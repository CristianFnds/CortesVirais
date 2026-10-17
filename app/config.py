import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuração centralizada para o projeto CortesVirais."""

    # API Python
    PYTHON_HOST: str = os.getenv("PYTHON_HOST", "127.0.0.1")
    PYTHON_PORT: int = int(os.getenv("PYTHON_PORT", "8000"))

    # LLM Local
    LLM_API_URL: str = os.getenv("LLM_API_URL", "http://127.0.0.1:8083/v1")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-7b")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "300"))

    # FFmpeg
    FFMPEG_PATH: Optional[str] = os.getenv("FFMPEG_PATH")

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")

    # Usuários Autorizados
    AUTHORIZED_USERS: list = [
        uid.strip() for uid in os.getenv("AUTHORIZED_USERS", "").split(",") if uid.strip()
    ]

    # Armazenamento
    STORAGE_BASE_PATH: str = os.getenv("STORAGE_BASE_PATH", "storage")

    # Logs
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    LOG_MAX_BYTES: int = int(os.getenv("LOG_MAX_BYTES", "10485760"))  # 10MB
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "7"))

    # Processamento
    MAX_CLIPS: int = int(os.getenv("MAX_CLIPS", "5"))
    TARGET_DURATION_SECONDS: int = int(os.getenv("TARGET_DURATION_SECONDS", "60"))
    MIN_DURATION_SECONDS: int = int(os.getenv("MIN_DURATION_SECONDS", "45"))
    MAX_DURATION_SECONDS: int = int(os.getenv("MAX_DURATION_SECONDS", "65"))

    # Caminhos
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STORAGE_DIR: Path = BASE_DIR / STORAGE_BASE_PATH
    LOGS_DIR: Path = BASE_DIR / "logs"

    @classmethod
    def validate(cls) -> list[str]:
        """Valida a configuração e retorna uma lista de problemas."""
        issues = []

        if not cls.STORAGE_DIR.exists():
            issues.append(f"Storage directory does not exist: {cls.STORAGE_DIR}")

        if not cls.LOGS_DIR.exists():
            issues.append(f"Logs directory does not exist: {cls.LOGS_DIR}")

        if cls.FFMPEG_PATH and not Path(cls.FFMPEG_PATH).exists():
            issues.append(f"FFmpeg path not found: {cls.FFMPEG_PATH}")

        return issues

    @classmethod
    def get_storage_path(cls, job_id: str) -> Path:
        """Retorna o caminho para o diretório de um trabalho específico."""
        path = cls.STORAGE_DIR / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path
