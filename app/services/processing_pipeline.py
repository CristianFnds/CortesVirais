from typing import Dict, Any, Optional
from pathlib import Path
import time

from app.services.job_manager import JobManager, JobNotFoundError
from app.services.download_service import DownloadService, DownloadError
from app.services.transcription_service import TranscriptionService, TranscriptionError
from app.services.clip_selection_service import ClipSelectionService, ClipSelectionError
from app.services.clip_generation_service import ClipGenerationService, ClipGenerationError
from app.models.job import Job, JobStatus
from app.models.transcript import Transcript
from app.config import Config
from app.infrastructure.logger import get_logger


class ProcessingPipelineError(Exception):
    """Exceção para erros do pipeline de processamento."""
    pass


class ProcessingPipeline:
    """Pipeline de processamento de vídeo."""

    def __init__(
        self,
        job_manager: Optional[JobManager] = None,
        download_service: Optional[DownloadService] = None,
        transcription_service: Optional[TranscriptionService] = None,
        clip_selection_service: Optional[ClipSelectionService] = None,
        clip_generation_service: Optional[ClipGenerationService] = None,
    ):
        """Inicializa o pipeline.
        
        Args:
            job_manager: Gerenciador de jobs.
            download_service: Serviço de download.
            transcription_service: Serviço de transcrição.
            clip_selection_service: Serviço de seleção de clipes.
            clip_generation_service: Serviço de geração de clipes.
        """
        self.job_manager = job_manager or JobManager()
        self.download_service = download_service or DownloadService()
        self.transcription_service = transcription_service or TranscriptionService()
        self.clip_selection_service = clip_selection_service or ClipSelectionService()
        self.clip_generation_service = clip_generation_service or ClipGenerationService()
        self.logger = get_logger(__name__)

    def process(
        self,
        job_id: str,
        url: str,
        detect_language: bool = True,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executa o pipeline completo de processamento.
        
        Args:
            job_id: ID do trabalho.
            url: URL do vídeo.
            detect_language: Detectar idioma automaticamente.
            language: Idioma forçado (None para detectar).
            
        Returns:
            Dicionário com resultados.
            
        Raises:
            ProcessingPipelineError: Se o processamento falhar.
        """
        start_time = time.time()
        
        try:
            # Etapa 1: Download
            self.logger.log_step_start(job_id, "download", {"url": url})
            self.job_manager.update_job_status(
                job_id,
                JobStatus.DOWNLOADING,
                stage="download",
            )

            download_result = self.download_service.download_video(
                job_id=job_id,
                url=url,
            )

            # Atualiza metadados do vídeo
            self.job_manager.set_video_metadata(
                job_id=job_id,
                title=download_result.get("video_id", "unknown"),
                duration=0,  # Será atualizado após extração
                video_id=download_result["video_id"],
            )

            self.logger.log_step_complete(job_id, "download", duration=time.time() - start_time)

            # Etapa 2: Extração de áudio
            self.logger.log_step_start(job_id, "audio_extraction")
            self.job_manager.update_job_status(
                job_id,
                JobStatus.AUDIO_EXTRACTED,
                stage="audio_extraction",
            )

            audio_result = self.download_service.extract_audio(
                job_id=job_id,
                video_path=download_result["video_path"],
            )

            # Atualiza duração do vídeo
            self.job_manager.set_video_metadata(
                job_id=job_id,
                title=download_result.get("video_id", "unknown"),
                duration=audio_result["duration"],
                video_id=download_result["video_id"],
            )

            self.logger.log_step_complete(job_id, "audio_extraction", duration=time.time() - start_time)

            # Etapa 3: Transcrição
            self.logger.log_step_start(job_id, "transcription", {"detect_language": detect_language})
            self.job_manager.update_job_status(
                job_id,
                JobStatus.TRANSCRIBING,
                stage="transcription",
            )

            transcript = self.transcription_service.transcribe(
                job_id=job_id,
                audio_path=audio_result["audio_path"],
                language=None if detect_language else language,
            )

            self.logger.log_step_complete(job_id, "transcription", duration=time.time() - start_time)

            # Etapa 4: Seleção de clipes com LLM
            self.logger.log_step_start(job_id, "clip_selection", {
                "target_duration": Config.TARGET_DURATION_SECONDS,
                "min_duration": Config.MIN_DURATION_SECONDS,
                "max_duration": Config.MAX_DURATION_SECONDS,
                "max_clips": Config.MAX_CLIPS,
            })
            self.job_manager.update_job_status(
                job_id,
                JobStatus.ANALYZING,
                stage="clip_selection",
            )

            from app.models.clip import ClipCandidate
            candidates = self.clip_selection_service.select_clips(
                job_id=job_id,
                transcript=transcript,
                target_duration=Config.TARGET_DURATION_SECONDS,
                min_duration=Config.MIN_DURATION_SECONDS,
                max_duration=Config.MAX_DURATION_SECONDS,
                max_clips=Config.MAX_CLIPS,
            )

            # Salva seleção
            self.clip_selection_service.save_selection(job_id, candidates)

            for candidate in candidates:
                self.logger.log_clip_candidate(job_id, {
                    "title": candidate.title,
                    "start": candidate.start,
                    "end": candidate.end,
                    "score": candidate.score,
                })

            self.logger.log_step_complete(job_id, "clip_selection", duration=time.time() - start_time)

            # Etapa 5: Geração de clipes
            self.logger.log_step_start(job_id, "clip_generation", {
                "candidates_count": len(candidates),
            })
            self.job_manager.update_job_status(
                job_id,
                JobStatus.CUTTING,
                stage="clip_generation",
            )

            storage_path = Path(self.job_manager.get_job(job_id).storage_path)
            audio_files = list(storage_path.glob("*_audio.*"))
            video_files = list(storage_path.glob("*.mp4"))
            
            if not audio_files or not video_files:
                raise ClipGenerationError("Arquivos de áudio ou vídeo não encontrados")

            generated_clips = self.clip_generation_service.generate_clips(
                job_id=job_id,
                audio_path=str(audio_files[0]),
                video_path=str(video_files[0]),
                candidates=candidates,
                output_dir=str(storage_path / "clips"),
            )

            # Salva informações dos clipes gerados
            import json
            clips_data = [
                {
                    "clip_id": c.clip_id,
                    "title": c.candidate_title,
                    "start": c.start,
                    "end": c.end,
                    "duration": c.duration,
                    "output_path": c.output_path,
                    "status": c.status,
                }
                for c in generated_clips
            ]
            with open(storage_path / "generated_clips.json", "w", encoding="utf-8") as f:
                json.dump(clips_data, f, indent=2)

            self.logger.log_step_complete(job_id, "clip_generation", duration=time.time() - start_time)

            # Atualiza status para concluído
            self.job_manager.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                stage="completed",
            )

            total_duration = time.time() - start_time
            self.logger.info(f"[JOB:{job_id}] PROCESSAMENTO CONCLUÍDO ({total_duration:.2f}s)")

            return {
                "job_id": job_id,
                "status": "completed",
                "video_id": download_result["video_id"],
                "video_duration": audio_result["duration"],
                "audio_path": audio_result["audio_path"],
                "transcript_segments": len(transcript.segments),
                "transcript_language": transcript.language,
                "selected_clips": len(candidates),
                "clips": [
                    {
                        "start": c.start,
                        "end": c.end,
                        "title": c.title,
                        "score": c.score,
                    }
                    for c in candidates
                ],
            }

        except JobNotFoundError as e:
            self.logger.log_error_job(job_id, "initialization", e, "Job não encontrado")
            raise ProcessingPipelineError(f"Job não encontrado: {e}")
        except DownloadError as e:
            self.logger.log_error_job(job_id, "download", e, "Erro no download")
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="download",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro no download: {e}")
        except TranscriptionError as e:
            self.logger.log_error_job(job_id, "transcription", e, "Erro na transcrição")
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="transcription",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro na transcrição: {e}")
        except ClipSelectionError as e:
            self.logger.log_error_job(job_id, "clip_selection", e, "Erro na seleção de clipes")
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="clip_selection",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro na seleção de clipes: {e}")
        except ClipGenerationError as e:
            self.logger.log_error_job(job_id, "clip_generation", e, "Erro na geração de clipes")
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="clip_generation",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro na geração de clipes: {e}")
        except Exception as e:
            self.logger.log_error_job(job_id, "unknown", e, "Erro no pipeline")
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="unknown",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro no pipeline: {e}")

    def process_step_download(self, job_id: str, url: str) -> Dict[str, Any]:
        """Executa apenas a etapa de download.
        
        Args:
            job_id: ID do trabalho.
            url: URL do vídeo.
            
        Returns:
            Dicionário com resultados do download.
        """
        try:
            self.job_manager.update_job_status(
                job_id,
                JobStatus.DOWNLOADING,
                stage="download",
            )

            result = self.download_service.download_video(
                job_id=job_id,
                url=url,
            )

            self.job_manager.set_video_metadata(
                job_id=job_id,
                title=result.get("video_id", "unknown"),
                duration=0,
                video_id=result["video_id"],
            )

            self.job_manager.update_job_status(
                job_id,
                JobStatus.AUDIO_EXTRACTED,
                stage="download_completed",
            )

            return result

        except DownloadError as e:
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="download",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro no download: {e}")

    def process_step_extract_audio(self, job_id: str) -> Dict[str, Any]:
        """Executa apenas a etapa de extração de áudio.
        
        Args:
            job_id: ID do trabalho.
            
        Returns:
            Dicionário com resultados da extração.
        """
        try:
            self.job_manager.update_job_status(
                job_id,
                JobStatus.AUDIO_EXTRACTED,
                stage="audio_extraction",
            )

            # Obtém informações do job
            job = self.job_manager.get_job(job_id)
            storage_path = Path(job.storage_path)
            video_files = list(storage_path.glob("*.mp4"))
            
            if not video_files:
                raise ProcessingPipelineError("Vídeo não encontrado")

            result = self.download_service.extract_audio(
                job_id=job_id,
                video_path=str(video_files[0]),
            )

            self.job_manager.set_video_metadata(
                job_id=job_id,
                title=job.video_title,
                duration=result["duration"],
                video_id=job.video_id,
            )

            return result

        except DownloadError as e:
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="audio_extraction",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro na extração: {e}")

    def process_step_transcribe(self, job_id: str, language: Optional[str] = None) -> Transcript:
        """Executa apenas a etapa de transcrição.
        
        Args:
            job_id: ID do trabalho.
            language: Idioma da transcrição.
            
        Returns:
            Objeto Transcript.
        """
        try:
            self.job_manager.update_job_status(
                job_id,
                JobStatus.TRANSCRIBING,
                stage="transcription",
            )

            job = self.job_manager.get_job(job_id)
            storage_path = Path(job.storage_path)
            audio_files = list(storage_path.glob("*_audio.*"))
            
            if not audio_files:
                raise ProcessingPipelineError("Áudio não encontrado")

            transcript = self.transcription_service.transcribe(
                job_id=job_id,
                audio_path=str(audio_files[0]),
                language=language,
            )

            self.job_manager.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                stage="transcription_completed",
            )

            return transcript

        except TranscriptionError as e:
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="transcription",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro na transcrição: {e}")
