import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from app.models.clip import ClipCandidate
from app.models.transcript import Transcript
from app.services.llm_client import LLMClient, LLMClientError
from app.services.clip_validator import ClipValidator
from app.config import Config


class ClipSelectionError(Exception):
    """Exceção para erros de seleção de clipes."""
    pass


class ClipSelectionService:
    """Serviço de seleção de momentos virais usando LLM."""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
    ):
        """Inicializa o serviço.
        
        Args:
            llm_client: Cliente LLM. Usa padrão se None.
        """
        self.llm_client = llm_client or LLMClient()
        self.logger = None

    def _get_logger(self):
        """Retorna o logger configurado."""
        if self.logger is None:
            import logging
            self.logger = logging.getLogger(__name__)
        return self.logger

    def select_clips(
        self,
        job_id: str,
        transcript: Transcript,
        target_duration: int = 60,
        min_duration: int = 45,
        max_duration: int = 65,
        max_clips: int = 5,
        retry_failed: bool = True,
    ) -> List[ClipCandidate]:
        """Seleiona os melhores momentos da transcrição.
        
        Args:
            job_id: ID do trabalho.
            transcript: Transcrição completa.
            target_duration: Duração desejada dos clipes.
            min_duration: Duração mínima dos clipes.
            max_duration: Duração máxima dos clipes.
            max_clips: Número máximo de clipes.
            retry_failed: Tentar novamente se falhar.
            
        Returns:
            Lista de ClipCandidates.
            
        Raises:
            ClipSelectionError: Se a seleção falhar.
        """
        self._get_logger().info(
            "Iniciando seleção de clipes para job %s",
            job_id,
        )

        # Valida parâmetros
        if target_duration < min_duration or target_duration > max_duration:
            raise ClipSelectionError(
                f"Duração desejada ({target_duration}) fora dos limites "
                f"({min_duration}-{max_duration})"
            )

        try:
            # Chama o LLM para análise
            candidates = self.llm_client.analyze_transcription(
                job_id=job_id,
                transcription={
                    "language": transcript.language,
                    "duration": transcript.duration,
                    "segments": [
                        {
                            "start": seg.start,
                            "end": seg.end,
                            "text": seg.text,
                        }
                        for seg in transcript.segments
                    ],
                },
                target_duration=target_duration,
                min_duration=min_duration,
                max_duration=max_duration,
                max_clips=max_clips,
            )

            # Valida candidatos
            validator = ClipValidator(
                video_duration=transcript.duration,
                min_duration=min_duration,
                max_duration=max_duration,
            )
            
            valid_candidates = validator.validate_candidates(candidates)

            self._get_logger().info(
                "Seleção concluída: %d candidatos válidos para job %s",
                len(valid_candidates),
                job_id,
            )

            return valid_candidates

        except LLMClientError as e:
            self._get_logger().error("Erro LLM: %s", e)
            
            if retry_failed:
                self._get_logger().info("Tentando com parâmetros relaxados...")
                return self._retry_with_fallback(
                    job_id,
                    transcript,
                    min_duration,
                    max_duration,
                    max_clips,
                )
            
            raise ClipSelectionError(f"Seleção falhou: {e}")
        except Exception as e:
            raise ClipSelectionError(f"Erro na seleção: {e}")

    def _retry_with_fallback(
        self,
        job_id: str,
        transcript: Transcript,
        min_duration: int,
        max_duration: int,
        max_clips: int,
    ) -> List[ClipCandidate]:
        """Tenta com parâmetros relaxados.
        
        Args:
            job_id: ID do trabalho.
            transcript: Transcrição.
            min_duration: Duração mínima.
            max_duration: Duração máxima.
            max_clips: Máximo de clipes.
            
        Returns:
            Lista de candidatos ou lista vazia.
        """
        try:
            # Aumenta timeout e relaxa restrições
            relaxed_client = LLMClient(
                api_url=self.llm_client.api_url,
                model=self.llm_client.model,
                timeout=self.llm_client.timeout + 60,
            )
            
            candidates = relaxed_client.analyze_transcription(
                job_id=job_id,
                transcription={
                    "language": transcript.language,
                    "duration": transcript.duration,
                    "segments": [
                        {
                            "start": seg.start,
                            "end": seg.end,
                            "text": seg.text,
                        }
                        for seg in transcript.segments
                    ],
                },
                target_duration=60,
                min_duration=min_duration,
                max_duration=max_duration,
                max_clips=max_clips,
            )
            
            return candidates

        except Exception as e:
            self._get_logger().error("Fallback falhou: %s", e)
            return []

    def save_selection(
        self,
        job_id: str,
        candidates: List[ClipCandidate],
    ) -> str:
        """Salva a seleção em JSON.
        
        Args:
            job_id: ID do trabalho.
            candidates: Lista de candidatos.
            
        Returns:
            Caminho do arquivo salvo.
        """
        from app.config import Config
        
        job_dir = Path(Config.get_storage_path(job_id))
        output_path = job_dir / "clip_selection.json"

        data = {
            "job_id": job_id,
            "selected_at": datetime.utcnow().isoformat(),
            "total_candidates": len(candidates),
            "clips": [
                {
                    "start": c.start,
                    "end": c.end,
                    "title": c.title,
                    "reason": c.reason,
                    "hook": c.hook,
                    "score": c.score,
                }
                for c in candidates
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(output_path)
