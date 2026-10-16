import pytest
from unittest.mock import patch, MagicMock
from app.services.url_validator import URLValidator, URLValidationError


class TestURLValidator:
    """Testes para o validador de URLs."""

    def test_validate_youtube_url(self):
        """Testa validação de URL do YouTube."""
        validator = URLValidator()
        result = validator.validate("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        assert result["valid"] is True
        assert result["host"] == "www.youtube.com"
        assert result["video_id"] == "dQw4w9WgXcQ"

    def test_validate_youtu_be_url(self):
        """Testa validação de URL youtu.be."""
        validator = URLValidator()
        result = validator.validate("https://youtu.be/dQw4w9WgXcQ")
        
        assert result["valid"] is True
        assert result["video_id"] == "dQw4w9WgXcQ"

    def test_validate_invalid_url(self):
        """Testa validação de URL inválida."""
        validator = URLValidator()
        
        with pytest.raises(URLValidationError):
            validator.validate("not-a-url")

    def test_validate_empty_url(self):
        """Testa validação de URL vazia."""
        validator = URLValidator()
        
        with pytest.raises(URLValidationError):
            validator.validate("")

    def test_validate_unsupported_host(self):
        """Testa validação de host não suportado."""
        validator = URLValidator()
        
        with pytest.raises(URLValidationError):
            validator.validate("https://vimeo.com/123456")

    def test_is_youtube_url_true(self):
        """Testa método is_youtube_url para URLs válidas."""
        validator = URLValidator()
        
        assert validator.is_youtube_url("https://www.youtube.com/watch?v=abc123") is True
        assert validator.is_youtube_url("https://youtu.be/abc123") is True

    def test_is_youtube_url_false(self):
        """Testa método is_youtube_url para URLs inválidas."""
        validator = URLValidator()
        
        assert validator.is_youtube_url("https://vimeo.com/123") is False
        assert validator.is_youtube_url("not-a-url") is False

    def test_add_host(self):
        """Testa adição de host personalizado."""
        validator = URLValidator()
        validator.add_host("vimeo.com")
        
        # O validador interno não é exposto, mas o método deve funcionar
        assert "vimeo.com" in validator.allowed_hosts

    def test_remove_host(self):
        """Testa remoção de host."""
        validator = URLValidator()
        validator.remove_host("m.youtube.com")
        
        assert "m.youtube.com" not in validator.allowed_hosts
