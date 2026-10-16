from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Estados possíveis de um trabalho."""
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    AUDIO_EXTRACTED = "audio_extracted"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    CUTTING = "cutting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(BaseModel):
    """Modelo de um trabalho de processamento."""
    job_id: str = Field(..., description="Identificador único do trabalho")
    source_url: str = Field(..., description="URL de origem do vídeo")
    user_id: Optional[str] = Field(None, description="ID do usuário do Telegram")
    status: JobStatus = Field(JobStatus.QUEUED, description="Estado atual do trabalho")
    stage: Optional[str] = Field(None, description="Etapa atual")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação")
    started_at: Optional[datetime] = Field(None, description="Data de início")
    completed_at: Optional[datetime] = Field(None, description="Data de conclusão")
    attempts: int = Field(0, description="Número de tentativas")
    error_message: Optional[str] = Field(None, description="Mensagem de erro")
    video_title: Optional[str] = Field(None, description="Título do vídeo")
    video_duration: Optional[float] = Field(None, description="Duração do vídeo em segundos")
    video_id: Optional[str] = Field(None, description="ID do vídeo da origem")
    storage_path: Optional[str] = Field(None, description="Caminho de armazenamento")
    config: dict = Field(default_factory=dict, description="Configurações utilizadas")
