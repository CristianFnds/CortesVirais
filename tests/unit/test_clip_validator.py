import pytest
from unittest.mock import patch, MagicMock
from app.models.clip import ClipCandidate
from app.services.clip_validator import ClipValidator


class TestClipValidator:
    """Testes para o validador de clipes."""

    def test_validate_duration_within_limits(self):
        """Testa validação de duração dentro dos limites."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
        )

        candidate = ClipCandidate(
            start=100.0,
            end=160.0,
            title="Test",
            reason="Test",
            score=0.9,
        )

        assert validator._is_valid(candidate) is True

    def test_validate_duration_too_short(self):
        """Testa validação de duração muito curta."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
        )

        candidate = ClipCandidate(
            start=100.0,
            end=140.0,  # 40 segundos
            title="Test",
            reason="Test",
            score=0.9,
        )

        assert validator._is_valid(candidate) is False

    def test_validate_duration_too_long(self):
        """Testa validação de duração muito longa."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
        )

        candidate = ClipCandidate(
            start=100.0,
            end=180.0,  # 80 segundos
            title="Test",
            reason="Test",
            score=0.9,
        )

        assert validator._is_valid(candidate) is False

    def test_validate_timestamps_outside_video(self):
        """Testa validação de timestamps fora do vídeo."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
        )

        # End maior que duração do vídeo
        candidate = ClipCandidate(
            start=950.0,
            end=1010.0,
            title="Test",
            reason="Test",
            score=0.9,
        )
        assert validator._is_valid(candidate) is False

    def test_validate_start_greater_than_end(self):
        """Testa validação de start > end."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
        )

        candidate = ClipCandidate(
            start=100.0,
            end=50.0,  # start > end
            title="Test",
            reason="Test",
            score=0.9,
        )

        assert validator._is_valid(candidate) is False

    def test_remove_duplicates(self):
        """Testa remoção de duplicatas."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
            min_overlap=0.5,
        )

        candidates = [
            ClipCandidate(start=100.0, end=160.0, title="A", reason="A", score=0.9),
            ClipCandidate(start=105.0, end=165.0, title="B", reason="B", score=0.8),  # Sobreposição
            ClipCandidate(start=200.0, end=260.0, title="C", reason="C", score=0.95),
        ]

        result = validator._remove_duplicates(candidates)

        # Deve remover B (sobreposição com A)
        assert len(result) == 2
        assert result[0].title in ["A", "C"]
        assert result[1].title in ["A", "C"]

    def test_remove_duplicates_keeps_higher_score(self):
        """Testa que remove duplicatas mantendo maior pontuação."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
            min_overlap=0.5,
        )

        candidates = [
            ClipCandidate(start=100.0, end=160.0, title="A", reason="A", score=0.8),
            ClipCandidate(start=105.0, end=165.0, title="B", reason="B", score=0.95),  # Sobreposição, maior score
        ]

        result = validator._remove_duplicates(candidates)

        # Deve manter B (maior pontuação)
        assert len(result) == 1
        assert result[0].title == "B"

    def test_calculate_overlap_no_overlap(self):
        """Testa cálculo de sobreposição sem sobreposição."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
        )

        clip1 = ClipCandidate(start=100.0, end=160.0, title="A", reason="A", score=0.9)
        clip2 = ClipCandidate(start=200.0, end=260.0, title="B", reason="B", score=0.8)

        overlap = validator._calculate_overlap(clip1, clip2)
        assert overlap == 0.0

    def test_calculate_overlap_partial(self):
        """Testa cálculo de sobreposição parcial."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
        )

        clip1 = ClipCandidate(start=100.0, end=160.0, title="A", reason="A", score=0.9)
        clip2 = ClipCandidate(start=140.0, end=200.0, title="B", reason="B", score=0.8)

        overlap = validator._calculate_overlap(clip1, clip2)
        # Sobreposição de 20 segundos em 60 segundos (menor duração)
        assert overlap == pytest.approx(20.0 / 60.0, rel=0.01)

    def test_validate_candidates_filters_invalid(self):
        """Testa validação de lista de candidatos."""
        validator = ClipValidator(
            video_duration=1000.0,
            min_duration=45.0,
            max_duration=65.0,
        )

        candidates = [
            ClipCandidate(start=100.0, end=160.0, title="A", reason="A", score=0.9),
            ClipCandidate(start=100.0, end=140.0, title="B", reason="B", score=0.8),  # Muito curto
            ClipCandidate(start=200.0, end=260.0, title="C", reason="C", score=0.95),
        ]

        result = validator.validate_candidates(candidates)

        assert len(result) == 2
        # Ordenado por pontuação
        assert result[0].score == 0.95
        assert result[1].score == 0.9
