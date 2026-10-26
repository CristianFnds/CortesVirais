from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Segment(BaseModel):
    """Segmento de transcrição com timestamps."""
    start: float = Field(..., ge=0, description="Início do segmento em segundos")
    end: float = Field(..., gt=0, description="Fim do segmento em segundos")
    text: str = Field(..., min_length=1, description="Texto transcrito")

    def duration(self) -> float:
        """Retorna a duração do segmento."""
        return self.end - self.start


class Transcript(BaseModel):
    """Transcrição completa com metadados."""
    job_id: str = Field(..., description="ID do trabalho associado")
    language: str = Field(..., description="Idioma detectado")
    segments: List[Segment] = Field(..., description="Segmentos de transcrição")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação")
    source_audio_path: Optional[str] = Field(None, description="Caminho do áudio fonte")
    duration: Optional[float] = Field(None, description="Duração total do áudio")

    def total_duration(self) -> float:
        """Retorna a duração total da transcrição."""
        if not self.segments:
            return 0.0
        return sum(seg.duration() for seg in self.segments)

    def validate_order(self) -> bool:
        """Valida se os segmentos estão em ordem cronológica."""
        for i in range(1, len(self.segments)):
            if self.segments[i].start < self.segments[i - 1].end:
                return False
        return True
