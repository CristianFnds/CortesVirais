import pytest
from unittest.mock import patch, MagicMock
from app.infrastructure.health import HealthChecker


class TestHealthChecker:
    """Testes para o HealthChecker."""

    @pytest.fixture
    def checker(self):
        """Cria uma instância do HealthChecker."""
        return HealthChecker()

    def test_get_health_returns_dict(self, checker):
        """Testa se get_health retorna um dicionário."""
        health = checker.get_health()
        assert isinstance(health, dict)
        assert "status" in health
        assert "details" in health

    def test_health_contains_all_components(self, checker):
        """Testa se todas as componentes estão presentes."""
        health = checker.get_health()
        details = health["details"]

        assert "application" in details
        assert "ffmpeg" in details
        assert "storage" in details
        assert "logs" in details
        assert "llm" in details

    @patch("app.infrastructure.health.HealthChecker._check_application")
    @patch("app.infrastructure.health.HealthChecker._check_ffmpeg")
    @patch("app.infrastructure.health.HealthChecker._check_storage")
    @patch("app.infrastructure.health.HealthChecker._check_logs")
    @patch("app.infrastructure.health.HealthChecker._check_llm")
    def test_healthy_status_when_all_components_healthy(
        self, mock_llm, mock_logs, mock_storage, mock_ffmpeg, mock_app, checker
    ):
        """Testa status healthy quando todos os componentes estão saudáveis."""
        mock_app.return_value = "healthy"
        mock_ffmpeg.return_value = "healthy"
        mock_storage.return_value = "healthy"
        mock_logs.return_value = "healthy"
        mock_llm.return_value = "healthy"

        health = checker.get_health()
        assert health["status"] == "healthy"

    @patch("app.infrastructure.health.HealthChecker._check_application")
    @patch("app.infrastructure.health.HealthChecker._check_ffmpeg")
    @patch("app.infrastructure.health.HealthChecker._check_storage")
    @patch("app.infrastructure.health.HealthChecker._check_logs")
    @patch("app.infrastructure.health.HealthChecker._check_llm")
    def test_unhealthy_status_when_one_component_unhealthy(
        self, mock_llm, mock_logs, mock_storage, mock_ffmpeg, mock_app, checker
    ):
        """Testa status unhealthy quando um componente está com problema."""
        mock_app.return_value = "healthy"
        mock_ffmpeg.return_value = "unhealthy"
        mock_storage.return_value = "healthy"
        mock_logs.return_value = "healthy"
        mock_llm.return_value = "healthy"

        health = checker.get_health()
        assert health["status"] == "unhealthy"

    def test_dependencies_status_format(self, checker):
        """Testa formato da lista de status das dependências."""
        results = checker.get_dependencies_status()

        assert isinstance(results, list)
        for result in results:
            assert "component" in result
            assert "status" in result
