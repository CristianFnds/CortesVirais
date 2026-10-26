import pytest
from unittest.mock import patch, MagicMock
from app.services.llm_client import LLMClient, LLMClientError


class TestLLMClient:
    """Testes para o cliente LLM."""

    def test_parse_valid_json_response(self):
        """Testa parse de resposta JSON válida."""
        client = LLMClient()

        response_text = """
        {
            "clips": [
                {
                    "start": 100.5,
                    "end": 160.5,
                    "title": "Melhor Momento",
                    "reason": "Conteúdo muito interessante",
                    "hook": "Gancho inicial forte",
                    "score": 0.95
                }
            ]
        }
        """

        candidates = client._parse_response(response_text, "job_test")

        assert len(candidates) == 1
        assert candidates[0].start == 100.5
        assert candidates[0].end == 160.5
        assert candidates[0].title == "Melhor Momento"
        assert candidates[0].score == 0.95

    def test_parse_json_with_markdown(self):
        """Testa parse de JSON com markdown."""
        client = LLMClient()

        response_text = """
        Aqui está a resposta:

        ```json
        {
            "clips": [
                {
                    "start": 50.0,
                    "end": 110.0,
                    "title": "Teste",
                    "reason": "Justificativa",
                    "hook": "Gancho",
                    "score": 0.8
                }
            ]
        }
        ```

        Fim da resposta.
        """

        candidates = client._parse_response(response_text, "job_test")

        assert len(candidates) == 1
        assert candidates[0].start == 50.0
        assert candidates[0].title == "Teste"

    def test_extract_json_from_plain_text(self):
        """Testa extração de JSON de texto plano."""
        client = LLMClient()

        response_text = '{"clips": [{"start": 1.0, "end": 2.0, "title": "T", "reason": "R", "score": 0.5}]}'

        candidates = client._parse_response(response_text, "job_test")

        assert len(candidates) == 1
        assert candidates[0].start == 1.0

    def test_extract_json_with_code_block(self):
        """Testa extração de JSON com bloco de código."""
        client = LLMClient()

        response_text = """```json
{
    "clips": [
        {"start": 10.0, "end": 20.0, "title": "T", "reason": "R", "score": 0.7}
    ]
}
```"""

        candidates = client._parse_response(response_text, "job_test")

        assert len(candidates) == 1
        assert candidates[0].start == 10.0

    def test_format_transcription(self):
        """Testa formatação de transcrição para prompt."""
        client = LLMClient()

        transcription = {
            "language": "pt",
            "duration": 1000.0,
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "Texto 1"},
                {"start": 5.0, "end": 10.0, "text": "Texto 2"},
            ],
        }

        formatted = client._format_transcription(transcription)

        assert "Idioma: pt" in formatted
        assert "1000.00 segundos" in formatted
        assert "Texto 1" in formatted
        assert "Texto 2" in formatted

    @patch("app.services.llm_client.httpx.Client")
    def test_call_llm_success(self, mock_client_class):
        """Testa chamada bem-sucedida ao LLM."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": '{"clips": []}'}}
            ]
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post = MagicMock(return_value=mock_response)

        mock_client_class.return_value = mock_client

        client = LLMClient(api_url="http://test:8080", model="test-model")
        result = client._call_llm("Test prompt")

        assert result == '{"clips": []}'
        mock_client.post.assert_called_once()

    @patch("app.services.llm_client.httpx.Client")
    def test_call_llm_connect_error(self, mock_client_class):
        """Testa erro de conexão com LLM."""
        import httpx

        mock_client_class.side_effect = httpx.ConnectError("Connection refused")

        client = LLMClient(api_url="http://invalid:9999")

        with pytest.raises(LLMClientError) as exc_info:
            client._call_llm("Test prompt")

        assert "Não foi possível conectar" in str(exc_info.value)

    @patch("app.services.llm_client.httpx.Client")
    def test_call_llm_timeout(self, mock_client_class):
        """Testa timeout do LLM."""
        import httpx

        mock_client_class.side_effect = httpx.TimeoutException("Timeout")

        client = LLMClient(api_url="http://slow:8080", timeout=1)

        with pytest.raises(LLMClientError) as exc_info:
            client._call_llm("Test prompt")

        assert "Timeout" in str(exc_info.value)

    def test_parse_response_empty(self):
        """Testa parse de resposta vazia."""
        client = LLMClient()

        with pytest.raises(LLMClientError):
            client._parse_response("", "job_test")

    def test_parse_response_invalid_json(self):
        """Testa parse de JSON inválido."""
        client = LLMClient()

        with pytest.raises(LLMClientError):
            client._parse_response("not json at all", "job_test")

    def test_parse_response_missing_clips(self):
        """Testa parse sem campo clips."""
        client = LLMClient()

        response_text = '{"other_field": "value"}'

        candidates = client._parse_response(response_text, "job_test")

        assert len(candidates) == 0
