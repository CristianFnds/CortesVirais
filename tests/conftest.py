import pytest
from app.config import Config


@pytest.fixture(scope="session")
def config():
    """Retorna a configuração para testes."""
    return Config


@pytest.fixture
def temp_storage(tmp_path):
    """Cria um diretório temporário para armazenamento."""
    original = Config.STORAGE_DIR
    Config.STORAGE_DIR = tmp_path
    yield tmp_path
    Config.STORAGE_DIR = original
