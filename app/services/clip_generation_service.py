import subprocess
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.clip import Clip, ClipCandidate
from app.models.job import JobStatus
from app.config import Config
from app.infrastructure.logger import get_logger


class ClipGenerationError(Exception):
    """Exceção para erros de geração de clipes."""
    pass


class ClipGenerationService:
    """Serviço de geração de clipes usando FFmpeg."""

    # Tolerâncias para duração (baseado na configuração do sistema)
    DURATION_TOLERANCE = 2.0  # segundos
    
    @property
    def MIN_ACCEPTABLE_DURATION(self) -> float:
        """Duração mínima aceitável baseada na configuração."""
        return Config.MIN_DURATION_SECONDS - self.DURATION_TOLERANCE
    
    @property
    def MAX_ACCEPTABLE_DURATION(self) -> float:
        """Duração máxima aceitável baseada na configuração."""
        return Config.MAX_DURATION_SECONDS + self.DURATION_TOLERANCE

    def __init__(self, ffmpeg_path: Optional[str] = None):
        """Inicializa o serviço de geração de clipes.
        
        Args:
            ffmpeg_path: Caminho do FFmpeg. Usa padrão se None.
        """
        self.ffmpeg_path = ffmpeg_path or Config.FFMPEG_PATH
        self.logger = get_logger(__name__)

    def generate_clips(
        self,
        job_id: str,
        audio_path: str,
        video_path: str,
        candidates: List[ClipCandidate],
        output_dir: str,
    ) -> List[Clip]:
        """Gera clipes a partir dos candidatos selecionados.
        
        Args:
            job_id: ID do trabalho.
            audio_path: Caminho do arquivo de áudio extraído.
            video_path: Caminho do arquivo de vídeo original.
            candidates: Lista de candidatos a gerar.
            output_dir: Diretório de saída para os clipes.
            
        Returns:
            Lista de clipes gerados com sucesso.
        """
        self.logger.log_step_start(job_id, "clip_generation", {
            "candidates_count": len(candidates),
            "output_dir": output_dir,
        })
        
        self.logger.info(f"[JOB:{job_id}] Iniciando geração de {len(candidates)} clipes")
        
        # Cria diretório de saída
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_clips = []
        failed_clips = []
        
        for idx, candidate in enumerate(candidates, 1):
            clip_id = f"clip_{uuid.uuid4().hex[:8]}"
            # Remove caracteres inválidos do nome do arquivo
            safe_title = candidate.title
            for char in r'\/:*?"<>|':
                safe_title = safe_title.replace(char, '_')
            safe_title = safe_title.replace(' ', '_')[:50]
            clip_filename = f"{safe_title}_{candidate.start:.0f}_{candidate.end:.0f}.mp4"
            clip_path = output_path / clip_filename
            
            try:
                self.logger.info(f"[JOB:{job_id}] [{idx}/{len(candidates)}] Gerando clipe: {candidate.title}")
                
                clip = self._generate_clip(
                    job_id=job_id,
                    clip_id=clip_id,
                    video_path=video_path,
                    audio_path=audio_path,
                    start_time=candidate.start,
                    end_time=candidate.end,
                    output_path=str(clip_path),
                    title=candidate.title,
                )
                
                # Valida o clipe gerado
                validation_result = self._validate_clip(clip_id, str(clip_path))
                
                if validation_result["valid"]:
                    clip.status = "completed"
                    clip.error_message = None
                    generated_clips.append(clip)
                    self.logger.info(f"[JOB:{job_id}] [{idx}/{len(candidates)}] Clipe gerado com sucesso: {clip_filename}")
                else:
                    clip.status = "failed"
                    clip.error_message = f"Validação falhou: {validation_result['error']}"
                    failed_clips.append(clip)
                    self.logger.warning(f"[JOB:{job_id}] [{idx}/{len(candidates)}] Clipe falhou validação: {clip_filename} - {validation_result['error']}")
                    
            except ClipGenerationError as e:
                clip = Clip(
                    clip_id=clip_id,
                    job_id=job_id,
                    candidate_title=candidate.title,
                    start=candidate.start,
                    end=candidate.end,
                    duration=0,
                    output_path=str(clip_path),
                    status="failed",
                    error_message=str(e),
                    created_at=datetime.utcnow(),
                )
                failed_clips.append(clip)
                self.logger.error(f"[JOB:{job_id}] [{idx}/{len(candidates)}] Falha ao gerar clipe: {candidate.title} - {e}")
            except Exception as e:
                clip = Clip(
                    clip_id=clip_id,
                    job_id=job_id,
                    candidate_title=candidate.title,
                    start=candidate.start,
                    end=candidate.end,
                    duration=0,
                    output_path=str(clip_path),
                    status="failed",
                    error_message=f"Erro inesperado: {e}",
                    created_at=datetime.utcnow(),
                )
                failed_clips.append(clip)
                self.logger.error(f"[JOB:{job_id}] [{idx}/{len(candidates)}] Erro inesperado: {candidate.title} - {e}")
        
        # Registra resultados
        self.logger.info(f"[JOB:{job_id}] Geração concluída: {len(generated_clips)} clipes gerados, {len(failed_clips)} falhas")
        
        self.logger.log_step_complete(job_id, "clip_generation", duration=0)
        
        return generated_clips

    def _generate_clip(
        self,
        job_id: str,
        clip_id: str,
        video_path: str,
        audio_path: str,
        start_time: float,
        end_time: float,
        output_path: str,
        title: str,
    ) -> Clip:
        """Gera um único clipe usando FFmpeg.
        
        Args:
            job_id: ID do trabalho.
            clip_id: ID do clipe.
            video_path: Caminho do vídeo original.
            audio_path: Caminho do áudio extraído.
            start_time: Tempo de início em segundos.
            end_time: Tempo de fim em segundos.
            output_path: Caminho de saída.
            title: Título do clipe.
            
        Returns:
            Objeto Clip gerado.
            
        Raises:
            ClipGenerationError: Se a geração falhar.
        """
        # Verifica se FFmpeg está disponível
        ffmpeg_cmd = self.ffmpeg_path or "ffmpeg"
        
        if not shutil.which(ffmpeg_cmd):
            raise ClipGenerationError(f"FFmpeg não encontrado: {ffmpeg_cmd}")
        
        # Calcula duração
        duration = end_time - start_time
        
        # Valida duração antes de gerar
        if duration < self.MIN_ACCEPTABLE_DURATION or duration > self.MAX_ACCEPTABLE_DURATION:
            raise ClipGenerationError(
                f"Duração inválida: {duration:.2f}s (esperado {self.MIN_ACCEPTABLE_DURATION:.1f}-{self.MAX_ACCEPTABLE_DURATION:.1f}s)"
            )
        
        # Monta comando FFmpeg
        # Usa o vídeo original para manter qualidade, corta pelo tempo
        # Usa -t em vez de -to para maior precisão na duração
        duration = end_time - start_time
        cmd = [
            ffmpeg_cmd,
            "-y",  # Sobrescrever saída
            "-ss", str(start_time),  # Início do corte
            "-t", str(duration),  # Duração do corte
            "-i", video_path,  # Entrada
            "-c:v", "libx264",  # Codec de vídeo
            "-preset", "fast",  # Velocidade de codificação
            "-crf", "23",  # Qualidade (0-51, menor é melhor)
            "-c:a", "aac",  # Codec de áudio
            "-b:a", "128k",  # Bitrate de áudio
            "-movflags", "+faststart",  # Otimizar para web
            "-metadata", f"title={title}",  # Metadado de título
            output_path,  # Saída
        ]
        
        self.logger.debug(f"[JOB:{job_id}] [CLIP:{clip_id}] Comando FFmpeg: {' '.join(cmd)}")
        
        try:
            # Executa FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300,  # 5 minutos timeout
            )
            
            if result.returncode != 0:
                error_msg = f"FFmpeg stderr: {result.stderr}"
                raise ClipGenerationError(error_msg)
            
            # Verifica se arquivo foi criado
            if not Path(output_path).exists():
                raise ClipGenerationError("Arquivo de saída não foi criado")
            
            # Obtém tamanho do arquivo
            file_size = Path(output_path).stat().st_size
            
            # Cria objeto Clip
            clip = Clip(
                clip_id=clip_id,
                job_id=job_id,
                candidate_title=title,
                start=start_time,
                end=end_time,
                duration=duration,
                output_path=output_path,
                status="pending_validation",
                error_message=None,
                created_at=datetime.utcnow(),
            )
            
            # Log de performance
            self.logger.log_performance(
                job_id=job_id,
                operation="clip_generation",
                duration=0,  # Será calculado
                size_bytes=file_size,
                extra_info=f"{title} | {duration:.2f}s | {file_size/(1024*1024):.2f}MB"
            )
            
            return clip
            
        except subprocess.TimeoutExpired:
            raise ClipGenerationError("Timeout ao gerar clipe (5 minutos)")
        except subprocess.SubprocessError as e:
            raise ClipGenerationError(f"Erro FFmpeg: {e}")

    def _validate_clip(
        self,
        clip_id: str,
        clip_path: str,
    ) -> Dict[str, Any]:
        """Valida um clipe gerado.
        
        Args:
            clip_id: ID do clipe.
            clip_path: Caminho do clipe.
            
        Returns:
            Dicionário com resultado da validação.
        """
        try:
            # Verifica se arquivo existe
            if not Path(clip_path).exists():
                return {"valid": False, "error": "Arquivo não existe"}
            
            # Obtém tamanho do arquivo
            file_size = Path(clip_path).stat().st_size
            if file_size == 0:
                return {"valid": False, "error": "Arquivo vazio"}
            
            # Obtém metadados do clipe usando ffprobe
            ffprobe_cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                clip_path,
            ]
            
            result = subprocess.run(
                ffprobe_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30,
            )
            
            if result.returncode != 0:
                return {"valid": False, "error": "Falha ao ler metadados"}
            
            import json
            probe_data = json.loads(result.stdout)
            
            # Obtém duração
            format_info = probe_data.get("format", {})
            duration = float(format_info.get("duration", 0))
            
            # Valida duração
            if duration < self.MIN_ACCEPTABLE_DURATION:
                return {"valid": False, "error": f"Duração muito curta: {duration:.2f}s"}
            
            if duration > self.MAX_ACCEPTABLE_DURATION:
                return {"valid": False, "error": f"Duração muito longa: {duration:.2f}s"}
            
            # Verifica se tem vídeo e áudio
            streams = probe_data.get("streams", [])
            has_video = any(s.get("codec_type") == "video" for s in streams)
            has_audio = any(s.get("codec_type") == "audio" for s in streams)
            
            if not has_video:
                return {"valid": False, "error": "Sem stream de vídeo"}
            
            if not has_audio:
                return {"valid": False, "error": "Sem stream de áudio"}
            
            # Validação bem-sucedida
            return {
                "valid": True,
                "duration": duration,
                "file_size": file_size,
                "has_video": has_video,
                "has_audio": has_audio,
            }
            
        except Exception as e:
            return {"valid": False, "error": f"Erro na validação: {e}"}

    def generate_clip_single(
        self,
        job_id: str,
        video_path: str,
        audio_path: str,
        start_time: float,
        end_time: float,
        output_path: str,
        title: str,
    ) -> Clip:
        """Gera um único clipe (método auxiliar para uso direto).
        
        Args:
            job_id: ID do trabalho.
            video_path: Caminho do vídeo original.
            audio_path: Caminho do áudio extraído.
            start_time: Tempo de início em segundos.
            end_time: Tempo de fim em segundos.
            output_path: Caminho de saída.
            title: Título do clipe.
            
        Returns:
            Objeto Clip gerado.
            
        Raises:
            ClipGenerationError: Se a geração falhar.
        """
        return self._generate_clip(
            job_id=job_id,
            clip_id=f"clip_{uuid.uuid4().hex[:8]}",
            video_path=video_path,
            audio_path=audio_path,
            start_time=start_time,
            end_time=end_time,
            output_path=output_path,
            title=title,
        )

    def get_clip_info(self, clip_path: str) -> Dict[str, Any]:
        """Obtém informações detalhadas de um clipe.
        
        Args:
            clip_path: Caminho do clipe.
            
        Returns:
            Dicionário com informações do clipe.
        """
        try:
            if not Path(clip_path).exists():
                return {"error": "Arquivo não existe"}
            
            ffprobe_cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                clip_path,
            ]
            
            result = subprocess.run(
                ffprobe_cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30,
            )
            
            if result.returncode != 0:
                return {"error": "Falha ao ler metadados"}
            
            import json
            probe_data = json.loads(result.stdout)
            
            format_info = probe_data.get("format", {})
            streams = probe_data.get("streams", [])
            
            return {
                "path": clip_path,
                "file_size": Path(clip_path).stat().st_size,
                "duration": float(format_info.get("duration", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "video_codec": next((s.get("codec_name") for s in streams if s.get("codec_type") == "video"), None),
                "audio_codec": next((s.get("codec_name") for s in streams if s.get("codec_type") == "audio"), None),
                "width": next((s.get("width") for s in streams if s.get("codec_type") == "video"), None),
                "height": next((s.get("height") for s in streams if s.get("codec_type") == "video"), None),
            }
            
        except Exception as e:
            return {"error": str(e)}
