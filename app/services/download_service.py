import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from app.config import Config
from app.services.url_validator import URLValidator, URLValidationError


class DownloadError(Exception):
    """Exceção para erros de download."""
    pass


class DownloadService:
    """Serviço de download de vídeos usando yt-dlp."""

    def __init__(self, storage_base: Optional[Path] = None):
        """Inicializa o serviço de download.
        
        Args:
            storage_base: Base do diretório de armazenamento. Usa Config.STORAGE_DIR se None.
        """
        self.storage_base = storage_base or Config.STORAGE_DIR
        self.validator = URLValidator()
        self.logger = None

    def _get_logger(self):
        """Retorna o logger configurado."""
        if self.logger is None:
            import logging
            self.logger = logging.getLogger(__name__)
        return self.logger

    def validate_url(self, url: str) -> Dict[str, Any]:
        """Valida uma URL.
        
        Args:
            url: URL a validar.
            
        Returns:
            Dicionário com metadados da URL.
            
        Raises:
            URLValidationError: Se a URL for inválida.
        """
        return self.validator.validate(url)

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Obtém informações sobre um vídeo sem baixar.
        
        Args:
            url: URL do vídeo.
            
        Returns:
            Dicionário com metadados do vídeo.
            
        Raises:
            DownloadError: Se não for possível obter informações.
        """
        try:
            cmd = [
                "yt-dlp",
                "--no-download",
                "--dump-json",
                "--flat-playlist",
                url,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self._get_logger().error(f"yt-dlp error: {result.stderr}")
                raise DownloadError(f"yt-dlp falhou: {result.stderr}")

            import json
            info = json.loads(result.stdout)

            return {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "upload_date": info.get("upload_date"),
                "view_count": info.get("view_count"),
            }

        except subprocess.TimeoutExpired:
            raise DownloadError("Timeout ao obter informações do vídeo")
        except json.JSONDecodeError as e:
            raise DownloadError(f"Erro ao parsear JSON: {e}")
        except Exception as e:
            raise DownloadError(f"Erro ao obter informações: {e}")

    def download_video(
        self,
        job_id: str,
        url: str,
        format_spec: str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
    ) -> Dict[str, Any]:
        """Baixa um vídeo para um trabalho específico.
        
        Args:
            job_id: ID do trabalho.
            url: URL do vídeo.
            format_spec: Especificação de formato do yt-dlp.
            
        Returns:
            Dicionário com caminhos e metadados.
            
        Raises:
            DownloadError: Se o download falhar.
        """
        # Valida a URL
        url_info = self.validate_url(url)

        # Cria diretório do trabalho
        job_dir = Config.get_storage_path(job_id)
        self._get_logger().info(f"Download para job {job_id} em {job_dir}")

        try:
            # Executa yt-dlp
            output_template = str(job_dir / "%(id)s.%(ext)s")
            
            cmd = [
                "yt-dlp",
                "-f", format_spec,
                "--output", output_template,
                "--no-playlist",
                "--ffmpeg-location", Config.FFMPEG_PATH or None,
                url,
            ]

            self._get_logger().info(f"Executando: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutos
                cwd=str(job_dir),
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                self._get_logger().error(f"yt-dlp error: {error_msg}")
                
                if "format selection" in error_msg.lower():
                    raise DownloadError("Nenhum formato disponível para download")
                elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                    raise DownloadError("Erro de rede durante download")
                elif "permission" in error_msg.lower() or "disk" in error_msg.lower():
                    raise DownloadError("Erro de permissão ou disco cheio")
                else:
                    raise DownloadError(f"Download falhou: {error_msg}")

            # Encontra o arquivo baixado
            video_files = list(job_dir.glob(f"{url_info['video_id']}.*"))
            if not video_files:
                raise DownloadError("Arquivo baixado não encontrado")

            video_path = video_files[0]
            file_size = video_path.stat().st_size

            return {
                "job_id": job_id,
                "status": "completed",
                "video_path": str(video_path),
                "video_id": url_info["video_id"],
                "file_size": file_size,
                "storage_path": str(job_dir),
                "downloaded_at": datetime.utcnow().isoformat(),
            }

        except subprocess.TimeoutExpired:
            raise DownloadError("Timeout durante download")
        except URLValidationError as e:
            raise DownloadError(f"URL inválida: {e}")
        except Exception as e:
            raise DownloadError(f"Erro durante download: {e}")

    def extract_audio(
        self,
        job_id: str,
        video_path: str,
        output_format: str = "m4a",
    ) -> Dict[str, Any]:
        """Extrai áudio de um vídeo usando FFmpeg.
        
        Args:
            job_id: ID do trabalho.
            video_path: Caminho do vídeo.
            output_format: Formato de saída do áudio.
            
        Returns:
            Dicionário com caminho do áudio e duração.
            
        Raises:
            DownloadError: Se a extração falhar.
        """
        job_dir = Path(Config.get_storage_path(job_id))
        video_path = Path(video_path)

        if not video_path.exists():
            raise DownloadError(f"Vídeo não encontrado: {video_path}")

        output_path = job_dir / f"{video_path.stem}_audio.{output_format}"

        try:
            cmd = [
                Config.FFMPEG_PATH or "ffmpeg",
                "-y",  # Overwrite output file
                "-i", str(video_path),
                "-vn",  # No video
                "-acodec", "aac",  # Audio codec
                "-ab", "128k",  # Audio bitrate
                str(output_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode != 0:
                self._get_logger().error(f"FFmpeg error: {result.stderr}")
                raise DownloadError(f"FFmpeg falhou: {result.stderr}")

            if not output_path.exists():
                raise DownloadError("Arquivo de áudio não foi criado")

            # Obtém duração do áudio
            cmd_duration = [
                Config.FFMPEG_PATH or "ffmpeg",
                "-i", str(output_path),
            ]
            result_duration = subprocess.run(
                cmd_duration,
                capture_output=True,
                text=True,
                timeout=10,
            )

            duration = self._parse_duration(result_duration.stderr)

            return {
                "job_id": job_id,
                "status": "completed",
                "audio_path": str(output_path),
                "duration": duration,
                "file_size": output_path.stat().st_size,
            }

        except subprocess.TimeoutExpired:
            raise DownloadError("Timeout durante extração de áudio")
        except Exception as e:
            raise DownloadError(f"Erro durante extração: {e}")

    def _parse_duration(self, ffmpeg_output: str) -> Optional[float]:
        """Extrai duração do output do FFmpeg.
        
        Args:
            ffmpeg_output: Output do FFmpeg.
            
        Returns:
            Duração em segundos ou None.
        """
        import re
        match = re.search(r"Duration: (\d+):(\d+):(\d+)", ffmpeg_output)
        if match:
            hours, minutes, seconds = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds
        return None
