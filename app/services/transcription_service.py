
import json
import logging
from pathlib import Path
from typing import Optional
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
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        """
        Inicializa o serviço de transcrição.

        Args:
            model_name: Nome do modelo Whisper.
            device: Dispositivo de execução (cpu, cuda, auto).
            compute_type: Tipo de computação (int8, int8_float16, float16).
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.logger = logging.getLogger(__name__)
        self._model = None

    def _get_logger(self):
        """Retorna o logger configurado."""
        return self.logger

    def _load_model(self):
        """Carrega o modelo Whisper sob demanda."""
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )

            self.logger.info(
                "Modelo carregado: %s em %s, compute_type=%s",
                self.model_name,
                self.device,
                self.compute_type,
            )

        except ImportError as e:
            raise TranscriptionError(
                "faster-whisper não está instalado. "
                "Execute: python -m pip install faster-whisper"
            ) from e

        except Exception as e:
            self.logger.exception(
                "Falha ao carregar o modelo Whisper '%s'",
                self.model_name,
            )
            raise TranscriptionError(
                f"Erro ao carregar modelo: {type(e).__name__}: {e}"
            ) from e

    def transcribe(
        self,
        job_id: str,
        audio_path: str,
        language: Optional[str] = None,
        vad_filter: bool = True,
    ) -> Transcript:
        """
        Transcreve um arquivo de áudio.

        Args:
            job_id: ID do trabalho.
            audio_path: Caminho do arquivo de áudio.
            language: Idioma (None para detecção automática).
            vad_filter: Filtra silêncio usando VAD.

        Returns:
            Objeto Transcript com os segmentos reconhecidos.

        Raises:
            TranscriptionError: Se a transcrição falhar.
        """
        audio_path = Path(audio_path)

        if not audio_path.is_file():
            raise TranscriptionError(
                f"Arquivo de áudio não encontrado: {audio_path}"
            )

        self._load_model()

        try:
            self.logger.info(
                "Iniciando transcrição do job %s: %s",
                job_id,
                audio_path,
            )

            # O faster-whisper retorna um iterador de segmentos.
            # A inferência pode ocorrer durante a iteração.
            segments, info = self._model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=vad_filter,
            )

            segment_list = []

            for seg in segments:
                segment_list.append(
                    Segment(
                        start=float(seg.start),
                        end=float(seg.end),
                        text=seg.text.strip(),
                    )
                )

            transcript_language = (
                info.language
                if info.language_probability > 0
                else "unknown"
            )

            transcript = Transcript(
                job_id=job_id,
                language=transcript_language,
                segments=segment_list,
                source_audio_path=str(audio_path),
                duration=float(info.duration),
            )

            output_path = self.save_transcription(job_id, transcript)

            self.logger.info(
                "Transcrição concluída para o job %s: "
                "%s segmentos, idioma=%s, duração=%.2fs, arquivo=%s",
                job_id,
                len(segment_list),
                transcript.language,
                info.duration,
                output_path,
            )

            if not segment_list:
                self.logger.warning(
                    "A transcrição do job %s terminou sem segmentos.",
                    job_id,
                )

            return transcript

        except TranscriptionError:
            raise

        except Exception as e:
            self.logger.exception(
                "Falha durante a transcrição do job %s",
                job_id,
            )

            raise TranscriptionError(
                f"Erro durante transcrição: {type(e).__name__}: {e}"
            ) from e

    def save_transcription(
        self,
        job_id: str,
        transcript: Transcript,
    ) -> str:
        """
        Salva a transcrição em JSON.

        Args:
            job_id: ID do trabalho.
            transcript: Objeto Transcript a salvar.

        Returns:
            Caminho do arquivo salvo.
        """
        job_dir = Path(Config.get_storage_path(job_id))
        job_dir.mkdir(parents=True, exist_ok=True)

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

        try:
            with output_path.open("w", encoding="utf-8") as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )

            return str(output_path)

        except Exception as e:
            self.logger.exception(
                "Falha ao salvar a transcrição do job %s",
                job_id,
            )
            raise TranscriptionError(
                f"Erro ao salvar transcrição: {type(e).__name__}: {e}"
            ) from e

    def load_transcription(
        self,
        job_id: str,
    ) -> Optional[Transcript]:
        """
        Carrega uma transcrição salva.

        Args:
            job_id: ID do trabalho.

        Returns:
            Transcript ou None se o arquivo não existir ou for inválido.
        """
        job_dir = Path(Config.get_storage_path(job_id))
        output_path = job_dir / "transcription.json"

        if not output_path.is_file():
            return None

        try:
            with output_path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            segments = [
                Segment(
                    start=float(segment["start"]),
                    end=float(segment["end"]),
                    text=segment["text"],
                )
                for segment in data.get("segments", [])
            ]

            return Transcript(
                job_id=data["job_id"],
                language=data["language"],
                segments=segments,
                source_audio_path=data.get("source_audio_path"),
                duration=data.get("duration"),
                created_at=datetime.fromisoformat(data["created_at"]),
            )

        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ):
            self.logger.exception(
                "Erro ao carregar a transcrição do job %s",
                job_id,
            )
            return None

    def is_transcription_valid(
        self,
        job_id: str,
        min_segments: int = 1,
    ) -> bool:
        """
        Verifica se uma transcrição existe e é válida.

        Args:
            job_id: ID do trabalho.
            min_segments: Número mínimo de segmentos esperado.

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
