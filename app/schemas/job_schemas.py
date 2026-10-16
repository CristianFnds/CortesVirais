from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class JobCreateRequest(BaseModel):
    """Requisição para criar um novo trabalho."""
    source_url: str = Field(..., min_length=1, description="URL do vídeo de origem")
    user_id: Optional[str] = Field(None, description="ID do usuário do Telegram")
    options: Optional[dict] = Field(None, description="Opções de processamento")


class JobCreateResponse(BaseModel):
    """Resposta da criação de um trabalho."""
    job_id: str = Field(..., description="Identificador único do trabalho")
    status: str = Field(..., description="Status inicial")
    message: str = Field(..., description="Mensagem de confirmação")


class JobResponse(BaseModel):
    """Resposta com informações de um trabalho."""
    job_id: str = Field(..., description="Identificador único")
    status: str = Field(..., description="Estado atual")
    stage: Optional[str] = Field(None, description="Etapa atual")
    source_url: str = Field(..., description="URL de origem")
    video_title: Optional[str] = Field(None, description="Título do vídeo")
    video_duration: Optional[float] = Field(None, description="Duração em segundos")
    created_at: datetime = Field(..., description="Data de criação")
    started_at: Optional[datetime] = Field(None, description="Data de início")
    completed_at: Optional[datetime] = Field(None, description="Data de conclusão")
    attempts: int = Field(..., description="Número de tentativas")
    error_message: Optional[str] = Field(None, description="Mensagem de erro")


class JobStatusUpdate(BaseModel):
    """Atualização de status de um trabalho."""
    status: str = Field(..., description="Novo status")
    stage: Optional[str] = Field(None, description="Nova etapa")
    error_message: Optional[str] = Field(None, description="Mensagem de erro")
