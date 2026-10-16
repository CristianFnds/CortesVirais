import re
from typing import List, Optional
from urllib.parse import urlparse

from app.config import Config


class URLValidationError(Exception):
    """Exceção para erros de validação de URL."""
    pass


class URLValidator:
    """Validador de URLs de vídeo."""

    # Hosts permitidos (YouTube inicialmente)
    ALLOWED_HOSTS: List[str] = [
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
    ]

    # Padrões de URL do YouTube
    YOUTUBE_PATTERNS = [
        r"^https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
        r"^https?://youtu\.be/([a-zA-Z0-9_-]+)",
        r"^https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)",
        r"^https?://(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]+)",
    ]

    def __init__(self, allowed_hosts: Optional[List[str]] = None):
        """Inicializa o validador.
        
        Args:
            allowed_hosts: Lista de hosts permitidos. Usa ALLOWED_HOSTS se None.
        """
        self.allowed_hosts = allowed_hosts or self.ALLOWED_HOSTS
        self.patterns = [re.compile(p) for p in self.YOUTUBE_PATTERNS]

    def validate(self, url: str) -> dict:
        """Valida uma URL e retorna metadados.
        
        Args:
            url: URL a ser validada.
            
        Returns:
            Dicionário com metadados da URL.
            
        Raises:
            URLValidationError: Se a URL for inválida.
        """
        if not url or not isinstance(url, str):
            raise URLValidationError("URL deve ser uma string não vazia")

        parsed = urlparse(url)

        if not parsed.scheme or not parsed.netloc:
            raise URLValidationError("URL inválida: esquema e host necessários")

        host = parsed.netloc.lower()

        if host not in self.allowed_hosts:
            raise URLValidationError(f"Host não permitido: {host}")

        video_id = self._extract_video_id(url)
        if not video_id:
            raise URLValidationError("Não foi possível extrair o ID do vídeo")

        return {
            "valid": True,
            "url": url,
            "host": host,
            "video_id": video_id,
            "scheme": parsed.scheme,
        }

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extrai o ID do vídeo da URL.
        
        Args:
            url: URL do vídeo.
            
        Returns:
            ID do vídeo ou None se não encontrado.
        """
        for pattern in self.patterns:
            match = pattern.match(url)
            if match:
                return match.group(1)
        return None

    def is_youtube_url(self, url: str) -> bool:
        """Verifica se a URL é do YouTube.
        
        Args:
            url: URL a verificar.
            
        Returns:
            True se for URL do YouTube.
        """
        try:
            self.validate(url)
            return True
        except URLValidationError:
            return False

    def add_host(self, host: str) -> None:
        """Adiciona um host à lista de permitidos.
        
        Args:
            host: Host a adicionar.
        """
        host = host.lower().strip()
        if host not in self.allowed_hosts:
            self.allowed_hosts.append(host)

    def remove_host(self, host: str) -> None:
        """Remove um host da lista de permitidos.
        
        Args:
            host: Host a remover.
        """
        host = host.lower().strip()
        if host in self.allowed_hosts:
            self.allowed_hosts.remove(host)
