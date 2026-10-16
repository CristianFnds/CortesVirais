import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import Config
from app.models.transcript import Transcript, Segment


class TranscriptionError(Exception):
    """Exceção para erros de transcrição."""
    pass


class TranscriptionService:
    """Serviço de transcrição de áudio usando faster-whisper."""

    def __init__(
        self,
        model_name: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
    ):
        """Inicializa o serviço de transcrição.
        
        Args:
            model_name: Nome do modelo Whisper.
            device: Dispositivo de execução (cpu, cuda, auto).
            compute_type: Tipo de computação (int8, int8_float16, float16).
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.logger = None
        self._model = None

    def _get_logger(self):
        """Retorna o logger configurado."""
        if self.logger is None:
            import logging
            self.logger = logging.getLogger(__name__)
        return self.logger

    def _load_model(self):
        """Carrega o modelo Whisper (lazy loading)."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
                
                self._model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type,
                )
                self._get_logger().info(f"Modelo carregado: {self.model_name} em {self.device}")
                
            except ImportError:
                raise TranscriptionError(
                    "faster-whisper não instalado. Execute: pip install faster-whisper"
                )
            except Exception as e:
                raise TranscriptionError(f"Erro ao carregar modelo: {e}")

    def transcribe(
        self,
        job_id: str,
        audio_path: str,
        language: Optional[str] = None,
        vad_filter: bool = True,
    ) -> Transcript:
        """Transcreve um arquivo de áudio.
        
        Args:
            job_id: ID do trabalho.
            audio_path: Caminho do arquivo de áudio.
            language: Idioma da transcrição (None para detectar automaticamente).
            vad_filter: Filtrar silêncio usando VAD.
            
        Returns:
            Objeto Transcript com segmentos.
            
        Raises:
            TranscriptionError: Se a transcrição falhar.
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise TranscriptionError(f"Áudio não encontrado: {audio_path}")

        self._load_model()

        try:
            segments, info = self._model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=vad_filter,
            )

            # Converte segmentos para lista de Segment objects
            segment_list = []
            for seg in segments:
                segment_list.append(Segment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                ))

            transcript = Transcript(
                job_id=job_id,
                language=info.language if info.language_probability > 0 else "unknown",
                segments=segment_list,
                source_audio_path=str(audio_path),
                duration=info.duration,
            )

            # Salva transcrição
            self.save_transcription(job_id, transcript)

            self._get_logger().info(
                f"Transcrição concluída: {len(segment_list)} segmentos, "
                f"idioma: {transcript.language}, duração: {info.duration:.2f}s"
            )

            return transcript

        except Exception as e:
            raise TranscriptionError(f"Erro durante transcrição: {e}")

    def save_transcription(self, job_id: str, transcript: Transcript) -> str:
        """Salva a transcrição em JSON.
        
        Args:
            job_id: ID do trabalho.
            transcript: Objeto Transcript a salvar.
            
        Returns:
            Caminho do arquivo salvo.
        """
        job_dir = Path(Config.get_storage_path(job_id))
        output_path = job_dir / "transcription.json"

        data = {
            "job_id": transcript.job_id,
            "language": transcript.language,
            "duration": transcript.duration,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                }
                for seg in transcript.segments
            ],
            "created_at": transcript.created_at.isoformat(),
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(output_path)

    def load_transcription(self, job_id: str) -> Optional[Transcript]:
        """Carrega uma transcrição salva.
        
        Args:
            job_id: ID do trabalho.
            
        Returns:
            Objeto Transcript ou None se não encontrado.
        """
        job_dir = Path(Config.get_storage_path(job_id))
        output_path = job_dir / "transcription.json"

        if not output_path.exists():
            return None

        try:
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            segments = [
                Segment(start=s["start"], end=s["end"], text=s["text"])
                for s in data.get("segments", [])
            ]

            return Transcript(
                job_id=data["job_id"],
                language=data["language"],
                segments=segments,
                duration=data.get("duration"),
                created_at=datetime.fromisoformat(data["created_at"]),
            )

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            self._get_logger().error(f"Erro ao carregar transcrição: {e}")
            return None

    def is_transcription_valid(self, job_id: str, min_segments: int = 1) -> bool:
        """Verifica se uma transcrição existe e é válida.
        
        Args:
            job_id: ID do trabalho.
            min_segments: Mínimo de segmentos esperado.
            
        Returns:
            True se a transcrição for válida.
        """
        transcript = self.load_transcription(job_id)
        if transcript is None:
            return False

        if len(transcript.segments) < min_segments:
            return False

        if not transcript.validate_order():
            return False

        return True
