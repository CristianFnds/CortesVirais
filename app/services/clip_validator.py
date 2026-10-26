from typing import List, Dict, Any
from app.models.clip import ClipCandidate
from app.infrastructure.logger import get_logger


class ClipValidator:
    """Validador de candidatos de clipes."""

    def __init__(
        self,
        video_duration: float,
        min_duration: float = 45.0,
        max_duration: float = 65.0,
        min_overlap: float = 0.5,
    ):
        """Inicializa o validador.
        
        Args:
            video_duration: Duração total do vídeo em segundos.
            min_duration: Duração mínima dos clipes.
            max_duration: Duração máxima dos clipes.
            min_overlap: Mínimo de sobreposição permitida (0.0 a 1.0).
        """
        self.video_duration = video_duration
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.min_overlap = min_overlap
        self.logger = get_logger(__name__)

    def validate_candidates(
        self,
        candidates: List[ClipCandidate],
    ) -> List[ClipCandidate]:
        """Valida e filtra candidatos.
        
        Args:
            candidates: Lista de candidatos.
            
        Returns:
            Lista de candidatos válidos.
        """
        valid_candidates = []
        
        for candidate in candidates:
            if self._is_valid(candidate):
                valid_candidates.append(candidate)
            else:
                self.logger.warning(
                    "Clipe inválido removido: %s (%.2f - %.2f)",
                    candidate.title,
                    candidate.start,
                    candidate.end,
                )
        
        # Remove duplicatas e sobreposições excessivas
        valid_candidates = self._remove_duplicates(valid_candidates)
        
        # Ordena por pontuação
        valid_candidates.sort(key=lambda c: c.score, reverse=True)
        
        return valid_candidates

    def _is_valid(self, candidate: ClipCandidate) -> bool:
        """Verifica se um candidato é válido.
        
        Args:
            candidate: Candidato a validar.
            
        Returns:
            True se válido.
        """
        # Verifica duração
        duration = candidate.duration()
        if duration < self.min_duration or duration > self.max_duration:
            return False
        
        # Verifica timestamps dentro do vídeo
        if candidate.start < 0 or candidate.end > self.video_duration:
            return False
        
        # Verifica start < end
        if candidate.start >= candidate.end:
            return False
        
        return True

    def _remove_duplicates(
        self,
        candidates: List[ClipCandidate],
    ) -> List[ClipCandidate]:
        """Remove duplicatas e sobreposições excessivas.
        
        Args:
            candidates: Lista de candidatos válidos.
            
        Returns:
            Lista sem duplicatas.
        """
        if not candidates:
            return []
        
        # Ordena por start
        sorted_candidates = sorted(candidates, key=lambda c: c.start)
        
        result = [sorted_candidates[0]]
        
        for candidate in sorted_candidates[1:]:
            last = result[-1]
            
            # Calcula sobreposição
            overlap = self._calculate_overlap(candidate, last)
            
            # Se sobreposição for muito alta, remove o candidato
            if overlap > self.min_overlap:
                # Mantém o de maior pontuação
                if candidate.score > last.score:
                    result[-1] = candidate
                continue
            
            result.append(candidate)
        
        return result

    def _calculate_overlap(
        self,
        clip1: ClipCandidate,
        clip2: ClipCandidate,
    ) -> float:
        """Calcula sobreposição entre dois clipes.
        
        Args:
            clip1: Primeiro clipe.
            clip2: Segundo clipe.
            
        Returns:
            Fração de sobreposição (0.0 a 1.0).
        """
        # Intervalo de sobreposição
        overlap_start = max(clip1.start, clip2.start)
        overlap_end = min(clip1.end, clip2.end)
        
        if overlap_start >= overlap_end:
            return 0.0
        
        overlap_duration = overlap_end - overlap_start
        
        # Duração menor dos dois clipes
        min_duration = min(clip1.duration(), clip2.duration())
        
        if min_duration == 0:
            return 0.0
        
        return overlap_duration / min_duration
