from typing import Dict, Any, Optional
from pathlib import Path

from app.services.job_manager import JobManager, JobNotFoundError
from app.services.download_service import DownloadService, DownloadError
from app.services.transcription_service import TranscriptionService, TranscriptionError
from app.models.job import Job, JobStatus
from app.models.transcript import Transcript
from app.config import Config


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
    ):
        """Inicializa o pipeline.
        
        Args:
            job_manager: Gerenciador de jobs.
            download_service: Serviço de download.
            transcription_service: Serviço de transcrição.
        """
        self.job_manager = job_manager or JobManager()
        self.download_service = download_service or DownloadService()
        self.transcription_service = transcription_service or TranscriptionService()
        self.logger = None

    def _get_logger(self):
        """Retorna o logger configurado."""
        if self.logger is None:
            import logging
            self.logger = logging.getLogger(__name__)
        return self.logger

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
        try:
            # Etapa 1: Download
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

            # Etapa 2: Extração de áudio
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

            # Etapa 3: Transcrição
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

            # Atualiza status para concluído
            self.job_manager.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                stage="completed",
            )

            return {
                "job_id": job_id,
                "status": "completed",
                "video_id": download_result["video_id"],
                "video_duration": audio_result["duration"],
                "audio_path": audio_result["audio_path"],
                "transcript_segments": len(transcript.segments),
                "transcript_language": transcript.language,
            }

        except JobNotFoundError as e:
            raise ProcessingPipelineError(f"Job não encontrado: {e}")
        except DownloadError as e:
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="download",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro no download: {e}")
        except TranscriptionError as e:
            self.job_manager.update_job_status(
                job_id,
                JobStatus.FAILED,
                stage="transcription",
                error_message=str(e),
            )
            raise ProcessingPipelineError(f"Erro na transcrição: {e}")
        except Exception as e:
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
