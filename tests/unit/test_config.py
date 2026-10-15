import pytest
from app.config import Config


class TestConfig:
    """Testes para a configuração centralizada."""

    def test_python_host_default(self):
        """Testa o host padrão da API."""
        assert Config.PYTHON_HOST == "127.0.0.1"

    def test_python_port_default(self):
        """Testa a porta padrão da API."""
        assert Config.PYTHON_PORT == 8000

    def test_llm_api_url_default(self):
        """Testa a URL padrão do LLM."""
        assert Config.LLM_API_URL == "http://localhost:8080/v1"

    def test_llm_timeout_default(self):
        """Testa o timeout padrão do LLM."""
        assert Config.LLM_TIMEOUT == 300

    def test_storage_dir_exists(self):
        """Testa se o diretório de armazenamento existe ou é criado."""
        assert isinstance(Config.STORAGE_DIR, type(Config.BASE_DIR))

    def test_logs_dir_exists(self):
        """Testa se o diretório de logs existe ou é criado."""
        assert isinstance(Config.LOGS_DIR, type(Config.BASE_DIR))

    def test_authorized_users_empty(self):
        """Testa lista de usuários autorizados vazia."""
        assert isinstance(Config.AUTHORIZED_USERS, list)

    def test_processing_limits(self):
        """Testa limites de processamento."""
        assert Config.MAX_CLIPS == 5
        assert Config.TARGET_DURATION_SECONDS == 60
        assert Config.MIN_DURATION_SECONDS == 45
        assert Config.MAX_DURATION_SECONDS == 65

    def test_get_storage_path_creates_directory(self, tmp_path):
        """Testa criação de diretório para job específico."""
        original_storage = Config.STORAGE_DIR
        Config.STORAGE_DIR = tmp_path

        try:
            job_path = Config.get_storage_path("test_job_123")
            assert job_path.exists()
            assert "test_job_123" in str(job_path)
        finally:
            Config.STORAGE_DIR = original_storage

    def test_validate_returns_issues(self):
        """Testa método de validação."""
        issues = Config.validate()
        assert isinstance(issues, list)
