from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ClipCandidate(BaseModel):
    """Candidato a clipe selecionado pelo LLM."""
    start: float = Field(..., ge=0, description="Início do clipe em segundos")
    end: float = Field(..., gt=0, description="Fim do clipe em segundos")
    title: str = Field(..., min_length=1, description="Título do clipe")
    reason: str = Field(..., min_length=1, description="Justificativa da seleção")
    hook: Optional[str] = Field(None, description="Resumo do gancho inicial")
    score: float = Field(..., ge=0, le=1, description="Pontuação de relevância")

    def duration(self) -> float:
        """Retorna a duração do clipe."""
        return self.end - self.start


class Clip(BaseModel):
    """Clipe gerado com FFmpeg."""
    clip_id: str = Field(..., description="Identificador único do clipe")
    job_id: str = Field(..., description="ID do trabalho associado")
    candidate_title: str = Field(..., description="Título do candidato")
    start: float = Field(..., ge=0, description="Início do clipe em segundos")
    end: float = Field(..., gt=0, description="Fim do clipe em segundos")
    duration: float = Field(..., gt=0, description="Duração do clipe em segundos")
    output_path: str = Field(..., description="Caminho do arquivo gerado")
    status: str = Field("completed", description="Status do clipe")
    error_message: Optional[str] = Field(None, description="Mensagem de erro")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação")
