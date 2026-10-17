import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import httpx

from app.config import Config
from app.models.clip import ClipCandidate
from app.services.clip_validator import ClipValidator


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

FORMATO DE SAÍDA (JSON):
{
  "clips": [
    {
      "start": <início em segundos>,
      "end": <fim em segundos>,
      "title": "<título curto e atraente do clipe>",
      "reason": "<justificativa da seleção>",
      "hook": "<resumo do gancho inicial>",
      "score": <pontuação de 0 a 1>
    }
  ]
}

REGRAS IMPORTANTES:
- Os timestamps devem ser derivados diretamente dos segmentos da transcrição fornecida
- NÃO invente timestamps que não correspondem aos dados reais
- A duração de cada clipe deve estar entre {min_duration} e {max_duration} segundos
- Priorize clipes que funcionam de forma autônoma
- Retorne no máximo {max_clips} clipes
- Ordene por relevância (melhor primeiro)

TRANSCRIÇÃO DO VÍDEO:
{transcription}

RETORNE APENAS O JSON, SEM TEXTO ADICIONAL."""

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
        self.logger = None

    def _get_logger(self):
        """Retorna o logger configurado."""
        if self.logger is None:
            import logging
            self.logger = logging.getLogger(__name__)
        return self.logger

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

        self._get_logger().info(
            "Enviando transcrição para análise LLM: job %s, %d segmentos",
            job_id,
            len(transcription.get("segments", [])),
        )

        try:
            # Envia requisição para o LLM
            response = self._call_llm(prompt)
            
            # Parseia a resposta
            candidates = self._parse_response(response, job_id)
            
            self._get_logger().info(
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
                                "content": "Você é um assistente que retorna APENAS JSON válido. Não inclua markdown, nem texto adicional.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 4096,
                    },
                    timeout=self.timeout,
                )

            if response.status_code != 200:
                raise LLMClientError(
                    f"LLM retornou status {response.status_code}: {response.text}"
                )

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                raise LLMClientError("LLM retornou resposta vazia")
            
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
            # Tenta extrair JSON da resposta (pode ter markdown)
            json_text = self._extract_json(response_text)
            
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
            raise LLMClientError(f"Resposta do LLM não é JSON válido: {e}")
        except (ValueError, TypeError, KeyError) as e:
            raise LLMClientError(f"Erro ao parsear resposta do LLM: {e}")

    def _extract_json(self, text: str) -> str:
        """Extrai JSON de texto que pode conter markdown.
        
        Args:
            text: Texto que pode conter JSON em markdown.
            
        Returns:
            JSON extraído.
        """
        # Tenta usar o texto diretamente primeiro
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # Procura por bloco de código markdown
        import re
        match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Procura por chaves de JSON
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]

        # Se nada funcionar, retorna o texto original (vai falhar no parse)
        return text
