import subprocess
from pathlib import Path
from typing import Dict, Any, List

from app.config import Config


class HealthChecker:
    """Verifica a saúde e disponibilidade das dependências do sistema."""

    def __init__(self):
        self.config = Config
        self.logger = None

    def get_health(self) -> Dict[str, Any]:
        """Retorna o status de saúde de todas as dependências."""
        if self.logger is None:
            self.logger = __import__("logging").getLogger(__name__)

        details: Dict[str, Any] = {
            "application": self._check_application(),
            "ffmpeg": self._check_ffmpeg(),
            "storage": self._check_storage(),
            "logs": self._check_logs(),
            "llm": self._check_llm(),
        }

        all_healthy = all(
            status == "healthy" for status in details.values()
        )

        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "details": details,
        }

    def _check_application(self) -> str:
        """Verifica se a aplicação está configurada corretamente."""
        try:
            issues = self.config.validate()
            if issues:
                return "degraded"
            return "healthy"
        except Exception:
            return "unhealthy"

    def _check_ffmpeg(self) -> str:
        """Verifica se o FFmpeg está disponível."""
        try:
            ffmpeg_path = self.config.FFMPEG_PATH or "ffmpeg"
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                return "healthy"
            return "unhealthy"
        except FileNotFoundError:
            return "unavailable"
        except subprocess.TimeoutExpired:
            return "unhealthy"
        except Exception:
            return "unhealthy"

    def _check_storage(self) -> str:
        """Verifica se o diretório de armazenamento está acessível."""
        try:
            if not self.config.STORAGE_DIR.exists():
                self.config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

            test_file = self.config.STORAGE_DIR / ".health_check"
            test_file.touch(exist_ok=True)
            test_file.unlink()

            return "healthy"
        except Exception:
            return "unhealthy"

    def _check_logs(self) -> str:
        """Verifica se o diretório de logs está acessível."""
        try:
            if not self.config.LOGS_DIR.exists():
                self.config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

            test_file = self.config.LOGS_DIR / ".health_check"
            test_file.touch(exist_ok=True)
            test_file.unlink()

            return "healthy"
        except Exception:
            return "unhealthy"

    def _check_llm(self) -> str:
        """Verifica a conectividade com o LLM local."""
        import httpx

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.config.LLM_API_URL}/health",
                    timeout=5.0,
                )
                if response.status_code == 200:
                    return "healthy"
                return "degraded"
        except httpx.ConnectError:
            return "unavailable"
        except httpx.TimeoutException:
            return "unhealthy"
        except Exception:
            return "unhealthy"

    def get_dependencies_status(self) -> List[Dict[str, str]]:
        """Retorna uma lista detalhada do status de cada dependência."""
        health = self.get_health()
        results = []

        for component, status in health["details"].items():
            results.append({
                "component": component,
                "status": status,
            })

        return results
