
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from app.config import Config
from app.services.url_validator import URLValidator, URLValidationError
from app.infrastructure.logger import get_logger


# Caminho para yt-dlp no ambiente virtual
YT_DLP_PATH = Path(sys.prefix) / "Scripts" / "yt-dlp.exe"


class DownloadError(Exception):
    """Exceção para erros de download."""
    pass


class DownloadService:
    """Serviço de download de vídeos usando yt-dlp e FFmpeg."""

    def __init__(self, storage_base: Optional[Path] = None):
        """Inicializa o serviço de download.

        Args:
            storage_base: Diretório base de armazenamento.
                Usa Config.STORAGE_DIR se None.
        """
        self.storage_base = storage_base or Config.STORAGE_DIR
        self.validator = URLValidator()
        self.logger = get_logger(__name__)

    def validate_url(self, url: str) -> Dict[str, Any]:
        """Valida uma URL e retorna seus metadados."""
        return self.validator.validate(url)

    def _run_command(
        self,
        cmd: list[str],
        timeout: int,
        cwd: Optional[str] = None,
    ) -> subprocess.CompletedProcess:
        """Executa um comando externo com saída UTF-8.

        Caracteres inválidos são substituídos para evitar
        UnicodeDecodeError durante a leitura da saída.
        """
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=cwd,
            check=False,
            shell=False,
        )

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Obtém informações sobre um vídeo sem baixá-lo."""
        try:
            self.validate_url(url)

            cmd = [
                str(YT_DLP_PATH),
                "--no-warnings",
                "--no-playlist",
                "--skip-download",
                "--dump-single-json",
                url,
            ]

            result = self._run_command(cmd, timeout=30)

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                self.logger.error("yt-dlp error: %s", error_msg)
                raise DownloadError(
                    f"yt-dlp falhou ao obter informações: {error_msg}"
                )

            info = json.loads(result.stdout)

            return {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "upload_date": info.get("upload_date"),
                "view_count": info.get("view_count"),
            }

        except DownloadError:
            raise
        except URLValidationError as e:
            raise DownloadError(f"URL inválida: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise DownloadError(
                "Timeout ao obter informações do vídeo"
            ) from e
        except json.JSONDecodeError as e:
            raise DownloadError(
                f"Erro ao interpretar JSON do yt-dlp: {e}"
            ) from e
        except Exception as e:
            raise DownloadError(
                f"Erro ao obter informações: {e}"
            ) from e

    def download_video(
        self,
        job_id: str,
        url: str,
        format_spec: str = (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "best[ext=mp4]/best"
        ),
    ) -> Dict[str, Any]:
        """Baixa um vídeo para o diretório de um job."""
        try:
            url_info = self.validate_url(url)

            job_dir = Path(Config.get_storage_path(job_id))
            job_dir.mkdir(parents=True, exist_ok=True)

            self.logger.info(
                "Download para job %s em %s",
                job_id,
                job_dir,
            )

            output_template = str(job_dir / "%(id)s.%(ext)s")

            cmd = [
                str(YT_DLP_PATH),
                "--no-playlist",
                "--no-warnings",
                "-f",
                format_spec,
                "--output",
                output_template,
            ]

            if Config.FFMPEG_PATH:
                cmd.extend([
                    "--ffmpeg-location",
                    str(Config.FFMPEG_PATH),
                ])

            cmd.append(url)

            self.logger.info(
                "Executando yt-dlp para job %s",
                job_id,
            )

            result = self._run_command(
                cmd,
                timeout=600,
                cwd=str(job_dir),
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self.logger.error(
                    "yt-dlp falhou para job %s: %s",
                    job_id,
                    error_msg,
                )

                lower_error = error_msg.lower()

                if (
                    "format selection" in lower_error
                    or "requested format" in lower_error
                ):
                    raise DownloadError(
                        "Nenhum formato disponível para download"
                    )

                if (
                    "network" in lower_error
                    or "connection" in lower_error
                ):
                    raise DownloadError(
                        f"Erro de rede durante o download: {error_msg}"
                    )

                if (
                    "permission" in lower_error
                    or "disk" in lower_error
                    or "no space left" in lower_error
                ):
                    raise DownloadError(
                        f"Erro de permissão ou espaço em disco: {error_msg}"
                    )

                raise DownloadError(
                    f"Download falhou: {error_msg}"
                )

            # Procura primeiro o arquivo correspondente ao ID validado.
            video_id = url_info.get("video_id")
            video_files = []

            if video_id:
                video_files = [
                    path
                    for path in job_dir.glob(f"{video_id}.*")
                    if path.is_file()
                    and not path.name.endswith((".part", ".ytdl"))
                ]

            # Fallback: identifica arquivos de vídeo criados no diretório.
            if not video_files:
                excluded_suffixes = {
                    ".part",
                    ".ytdl",
                    ".json",
                    ".description",
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                    ".vtt",
                    ".srt",
                }

                video_files = [
                    path
                    for path in job_dir.iterdir()
                    if path.is_file()
                    and path.suffix.lower() not in excluded_suffixes
                    and path.stat().st_size > 0
                ]

            if not video_files:
                raise DownloadError(
                    "O yt-dlp terminou sem erro, mas nenhum "
                    "arquivo baixado foi encontrado."
                )

            video_path = max(
                video_files,
                key=lambda path: path.stat().st_mtime,
            )
            file_size = video_path.stat().st_size

            self.logger.info(
                "Download concluído para job %s: %s (%s bytes)",
                job_id,
                video_path,
                file_size,
            )

            return {
                "job_id": job_id,
                "status": "completed",
                "video_path": str(video_path),
                "video_id": video_id or video_path.stem,
                "file_size": file_size,
                "storage_path": str(job_dir),
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
            }

        except DownloadError:
            raise
        except URLValidationError as e:
            raise DownloadError(f"URL inválida: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise DownloadError(
                "Timeout durante o download (limite de 10 minutos)"
            ) from e
        except Exception as e:
            self.logger.exception(
                "Erro inesperado durante download do job %s",
                job_id,
            )
            raise DownloadError(
                f"Erro durante download: {e}"
            ) from e

    def extract_audio(
        self,
        job_id: str,
        video_path: str,
        output_format: str = "m4a",
    ) -> Dict[str, Any]:
        """Extrai o áudio de um vídeo usando FFmpeg."""
        job_dir = Path(Config.get_storage_path(job_id))
        video_path = Path(video_path)

        if not video_path.exists():
            raise DownloadError(
                f"Vídeo não encontrado: {video_path}"
            )

        if output_format not in {"m4a", "mp3", "wav", "aac", "flac"}:
            raise DownloadError(
                f"Formato de áudio não suportado: {output_format}"
            )

        job_dir.mkdir(parents=True, exist_ok=True)
        output_path = job_dir / (
            f"{video_path.stem}_audio.{output_format}"
        )

        try:
            cmd = [
                Config.FFMPEG_PATH or "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vn",
            ]

            if output_format == "mp3":
                cmd.extend(["-acodec", "libmp3lame", "-b:a", "128k"])
            elif output_format == "wav":
                cmd.extend(["-acodec", "pcm_s16le"])
            elif output_format == "flac":
                cmd.extend(["-acodec", "flac"])
            else:
                cmd.extend(["-acodec", "aac", "-b:a", "128k"])

            cmd.append(str(output_path))

            result = self._run_command(
                cmd,
                timeout=300,
                cwd=str(job_dir),
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                self.logger.error(
                    "FFmpeg falhou para job %s: %s",
                    job_id,
                    error_msg,
                )
                raise DownloadError(
                    f"FFmpeg falhou: {error_msg}"
                )

            if not output_path.exists():
                raise DownloadError(
                    "Arquivo de áudio não foi criado"
                )

            # FFmpeg informa a duração no stderr.
            cmd_duration = [
                Config.FFMPEG_PATH or "ffmpeg",
                "-i",
                str(output_path),
            ]

            result_duration = self._run_command(
                cmd_duration,
                timeout=10,
                cwd=str(job_dir),
            )

            duration = self._parse_duration(
                result_duration.stderr
            )

            self.logger.info(
                "Áudio extraído para job %s: %s",
                job_id,
                output_path,
            )

            return {
                "job_id": job_id,
                "status": "completed",
                "audio_path": str(output_path),
                "duration": duration,
                "file_size": output_path.stat().st_size,
            }

        except DownloadError:
            raise
        except subprocess.TimeoutExpired as e:
            raise DownloadError(
                "Timeout durante a extração de áudio"
            ) from e
        except Exception as e:
            self.logger.exception(
                "Erro ao extrair áudio do job %s",
                job_id,
            )
            raise DownloadError(
                f"Erro durante extração de áudio: {e}"
            ) from e

    def _parse_duration(
        self,
        ffmpeg_output: str,
    ) -> Optional[float]:
        """Extrai a duração do formato HH:MM:SS.ss da saída do FFmpeg."""
        import re

        match = re.search(
            r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
            ffmpeg_output,
        )

        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = float(match.group(3))

            return hours * 3600 + minutes * 60 + seconds

        return None
