import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import time

import httpx

from app.config import Config
from app.models.clip import ClipCandidate
from app.services.clip_validator import ClipValidator
from app.infrastructure.logger import get_logger


class LLMClientError(Exception):
    """Exceção para erros de comunicação com o LLM."""
    pass


class LLMClient:
    """Cliente para comunicação com LLM local compatível com OpenAI."""

    # Prompt especializado para seleção de momentos virais
    VIRAL_CLIP_PROMPT = """Você é um especialista em identificar os melhores momentos de vídeos para criar clipes virais curtos (TikTok, Reels, Shorts).

Sua tarefa é analisar a transcrição de um vídeo e identificar os momentos mais interessantes para criar clipes de aproximadamente {target_duration} segundos.

CRITÉRIOS DE AVALIAÇÃO:
1. GANCHO INICIAL: O momento começa com algo que prende a atenção imediatamente?
2. RELEVÂNCIA: O conteúdo é interessante e valioso para o público?
3. CLAREZA: A mensagem é clara e compreensível?
4. AUTONOMIA: O clipe faz sentido sem precisar do contexto completo do vídeo?
5. CONCLUSÃO: O momento tem começo, desenvolvimento e uma conclusão satisfatória?
6. POTENCIAL VIRAL: O conteúdo tem potencial para engajamento?
7. DURAÇÃO: O intervalo selecionado tem duração adequada para um clipe curto?

FORMATO DE SAÍDA (JSON OBRIGATÓRIO):
Retorne APENAS um objeto JSON válido, sem markdown, sem texto adicional, sem comentários.

Exemplo de formato:
{{
  "clips": [
    {{
      "start": 120.5,
      "end": 180.3,
      "title": "Momento Incrível",
      "reason": "Contúdo muito relevante",
      "hook": "Começa com uma pergunta",
      "score": 0.85
    }}
  ]
}}

REGRAS IMPORTANTES:
- Os timestamps devem ser derivados diretamente dos segmentos da transcrição fornecida
- NÃO invente timestamps que não correspondem aos dados reais
- A duração de cada clipe deve estar entre {min_duration} e {max_duration} segundos
- Priorize clipes que funcionam de forma autônoma
- RETORNE NO MÍNIMO 2 trechos candidatos, mesmo que a qualidade seja menor
- Retorne no máximo {max_clips} clipes
- Ordene por relevância (melhor primeiro)
- RETORNE APENAS O JSON, SEM markdown, SEM texto adicional

TRANSCRIÇÃO DO VÍDEO:
{transcription}

RETORNE APENAS O JSON, SEM TEXTO ADICIONAL, SEM markdown."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 300,
    ):
        """Inicializa o cliente LLM.
        
        Args:
            api_url: URL da API do LLM local.
            model: Nome do modelo a usar.
            timeout: Timeout em segundos.
        """
        self.api_url = api_url or Config.LLM_API_URL
        self.model = model or Config.LLM_MODEL
        self.timeout = timeout
        self.logger = get_logger(__name__)

    def analyze_transcription(
        self,
        job_id: str,
        transcription: Dict[str, Any],
        target_duration: int = 60,
        min_duration: int = 45,
        max_duration: int = 65,
        max_clips: int = 5,
    ) -> List[ClipCandidate]:
        """Analisa a transcrição e identifica momentos virais.
        
        Args:
            job_id: ID do trabalho.
            transcription: Transcrição completa.
            target_duration: Duração desejada dos clipes.
            min_duration: Duração mínima dos clipes.
            max_duration: Duração máxima dos clipes.
            max_clips: Número máximo de clipes a retornar.
            
        Returns:
            Lista de ClipCandidates.
            
        Raises:
            LLMClientError: Se a análise falhar.
        """
        # Formata a transcrição para o prompt
        transcription_text = self._format_transcription(transcription)
        
        # Monta o prompt
        prompt = self.VIRAL_CLIP_PROMPT.format(
            target_duration=target_duration,
            min_duration=min_duration,
            max_duration=max_duration,
            max_clips=max_clips,
            transcription=transcription_text,
        )

        self.logger.info(
            "Enviando transcrição para análise LLM: job %s, %d segmentos",
            job_id,
            len(transcription.get("segments", [])),
        )

        try:
            # Envia requisição para o LLM
            response = self._call_llm(prompt)
            
            # Parseia a resposta com fallback
            candidates = self._parse_response_with_fallback(response, job_id)
            
            self.logger.info(
                "LLM retornou %d candidatos para job %s",
                len(candidates),
                job_id,
            )
            
            return candidates

        except LLMClientError:
            raise
        except Exception as e:
            raise LLMClientError(f"Erro ao analisar transcrição: {e}")

    def _format_transcription(self, transcription: Dict[str, Any]) -> str:
        """Formata a transcrição para o prompt.
        
        Args:
            transcription: Transcrição completa.
            
        Returns:
            Texto formatado.
        """
        lines = []
        lines.append(f"Idioma: {transcription.get('language', 'unknown')}")
        lines.append(f"Duração total: {transcription.get('duration', 0):.2f} segundos")
        lines.append("")
        lines.append("Segmentos:")
        
        for i, segment in enumerate(transcription.get("segments", []), 1):
            lines.append(
                f"[{i}] {segment['start']:.2f}s - {segment['end']:.2f}s: {segment['text']}"
            )
        
        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> str:
        """Chama a API do LLM.
        
        Args:
            prompt: Prompt para enviar.
            
        Returns:
            Resposta do LLM.
            
        Raises:
            LLMClientError: Se a chamada falhar.
        """
        try:
            with httpx.Client() as client:
                response = client.post(
                    f"{self.api_url}/chat/completions",
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "Você é um assistente que retorna APENAS "
                                    "JSON válido. Não inclua markdown nem texto adicional."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 4096,
                        "stream": False,
                        "chat_template_kwargs": {
                            "enable_thinking": False,
                        },
                    },
                    timeout=self.timeout,
                )

            if response.status_code != 200:
                raise LLMClientError(
                    f"LLM retornou status {response.status_code}: {response.text}"
                )

            data = response.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            
            if not content:
                finish_reason = choice.get("finish_reason")
                usage = data.get("usage", {})
                raise LLMClientError(
                    "LLM retornou resposta vazia. "
                    f"finish_reason={finish_reason}, "
                    f"usage={usage}, "
                    f"reasoning_content_presente={bool(message.get('reasoning_content'))}"
                )
            
            return content

        except httpx.ConnectError:
            raise LLMClientError(
                f"Não foi possível conectar ao LLM em {self.api_url}. "
                "Verifique se o serviço está rodando."
            )
        except httpx.TimeoutException:
            raise LLMClientError("Timeout ao comunicar com o LLM")
        except Exception as e:
            raise LLMClientError(f"Erro ao chamar LLM: {e}")

    def _parse_response_with_fallback(
        self,
        response_text: str,
        job_id: str,
    ) -> List[ClipCandidate]:
        """Parseia a resposta do LLM com fallback para JSON inválido.
        
        Args:
            response_text: Texto da resposta.
            job_id: ID do trabalho.
            
        Returns:
            Lista de ClipCandidates ou lista vazia.
        """
        try:
            return self._parse_response(response_text, job_id)
        except LLMClientError as e:
            self.logger.warning(f"Parse falhou para {job_id}: {e}")
            # Tenta extrair timestamps manualmente como fallback
            return self._extract_fallback_candidates(response_text, job_id)

    def _parse_response(
        self,
        response_text: str,
        job_id: str,
    ) -> List[ClipCandidate]:
        """Parseia a resposta do LLM.
        
        Args:
            response_text: Texto da resposta.
            job_id: ID do trabalho.
            
        Returns:
            Lista de ClipCandidates.
            
        Raises:
            LLMClientError: Se o parse falhar.
        """
        try:
            # Log da resposta bruta para debug
            self.logger.debug(f"Resposta bruta do LLM para {job_id}: {response_text[:200]}...")
            
            # Tenta extrair JSON da resposta (pode ter markdown)
            json_text = self._extract_json(response_text)
            
            self.logger.debug(f"JSON extraído para {job_id}: {json_text[:200]}...")
            
            data = json.loads(json_text)
            
            clips_data = data.get("clips", [])
            
            candidates = []
            for clip_data in clips_data:
                candidate = ClipCandidate(
                    start=float(clip_data.get("start", 0)),
                    end=float(clip_data.get("end", 0)),
                    title=str(clip_data.get("title", "Sem título")),
                    reason=str(clip_data.get("reason", "Sem justificativa")),
                    hook=str(clip_data.get("hook", "")),
                    score=float(clip_data.get("score", 0)),
                )
                candidates.append(candidate)
            
            return candidates

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON inválido para {job_id}: {response_text[:500]}")
            raise LLMClientError(f"Resposta do LLM não é JSON válido: {e}")
        except (ValueError, TypeError, KeyError) as e:
            self.logger.error(f"Erro ao parsear resposta para {job_id}: {e}")
            raise LLMClientError(f"Erro ao parsear resposta do LLM: {e}")

    def _extract_json(self, text: str) -> str:
        """Extrai JSON de texto que pode conter markdown.
        
        Args:
            text: Texto que pode conter JSON em markdown.
            
        Returns:
            JSON extraído.
        """
        import re
        
        # Remove texto antes do primeiro {
        start_brace = text.find("{")
        if start_brace != -1:
            text = text[start_brace:]
        
        # Remove texto depois do último }
        end_brace = text.rfind("}")
        if end_brace != -1:
            text = text[:end_brace + 1]
        
        # Tenta usar o texto diretamente primeiro
        try:
            json.loads(text)
            return text.strip()
        except json.JSONDecodeError:
            pass

        # Procura por bloco de código markdown
        match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Se nada funcionar, retorna o texto original (vai falhar no parse)
        return text

    def _extract_fallback_candidates(
        self,
        response_text: str,
        job_id: str,
    ) -> List[ClipCandidate]:
        """Extrai candidatos como fallback quando JSON falha.
        
        Args:
            response_text: Texto da resposta.
            job_id: ID do trabalho.
            
        Returns:
            Lista de ClipCandidates ou lista vazia.
        """
        import re
        
        # Procura por padrões de timestamps no texto
        pattern = r"(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*[=:]\s*(.+?)(?=\n|\Z)"
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        
        candidates = []
        for start, end, title in matches:
            try:
                start_time = float(start)
                end_time = float(end)
                duration = end_time - start_time
                
                # Valida duração
                if 43 <= duration <= 72:
                    candidates.append(ClipCandidate(
                        start=start_time,
                        end=end_time,
                        title=title.strip()[:50],
                        reason="Extrato automático (fallback)",
                        hook="",
                        score=0.5,
                    ))
            except (ValueError, TypeError):
                continue
        
        return candidates
