import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import json

from app.models.job import Job, JobStatus
from app.models.transcript import Transcript
from app.models.clip import Clip
from app.config import Config


class JobNotFoundError(Exception):
    """Exceção quando um job não é encontrado."""
    pass


class JobManager:
    """Gerenciador de jobs para persistência e estado."""

    def __init__(self, storage_base: Optional[Path] = None):
        """Inicializa o gerenciador de jobs.
        
        Args:
            storage_base: Base do diretório de armazenamento.
        """
        self.storage_base = storage_base or Config.STORAGE_DIR
        self.logger = None

    def _get_logger(self):
        """Retorna o logger configurado."""
        if self.logger is None:
            import logging
            self.logger = logging.getLogger(__name__)
        return self.logger

    def _get_job_path(self, job_id: str) -> Path:
        """Retorna o caminho do arquivo de um job.
        
        Args:
            job_id: ID do job.
            
        Returns:
            Caminho do arquivo JSON do job.
        """
        return self.storage_base / job_id / "job.json"

    def create_job(
        self,
        source_url: str,
        user_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """Cria um novo job.
        
        Args:
            source_url: URL de origem.
            user_id: ID do usuário.
            config: Configurações do job.
            
        Returns:
            Objeto Job criado.
        """
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        # Cria diretório do job usando storage_base
        job_dir = self.storage_base / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        job = Job(
            job_id=job_id,
            source_url=source_url,
            user_id=user_id,
            status=JobStatus.QUEUED,
            stage="initialization",
            config=config or {},
            storage_path=str(job_dir),
        )

        self._save_job(job)
        
        self._get_logger().info(f"Job criado: {job_id}")
        
        return job

    def get_job(self, job_id: str) -> Job:
        """Obtém um job pelo ID.
        
        Args:
            job_id: ID do job.
            
        Returns:
            Objeto Job.
            
        Raises:
            JobNotFoundError: Se o job não existir.
        """
        job_path = self._get_job_path(job_id)
        
        if not job_path.exists():
            raise JobNotFoundError(f"Job não encontrado: {job_id}")

        with open(job_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._dict_to_job(data)

    def _save_job(self, job: Job) -> None:
        """Salva um job em JSON.
        
        Args:
            job: Objeto Job a salvar.
        """
        data = {
            "job_id": job.job_id,
            "source_url": job.source_url,
            "user_id": job.user_id,
            "status": job.status.value,
            "stage": job.stage,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "attempts": job.attempts,
            "error_message": job.error_message,
            "video_title": job.video_title,
            "video_duration": job.video_duration,
            "video_id": job.video_id,
            "storage_path": job.storage_path,
            "config": job.config,
        }

        job_path = self._get_job_path(job.job_id)
        with open(job_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _dict_to_job(self, data: Dict[str, Any]) -> Job:
        """Converte dicionário para objeto Job.
        
        Args:
            data: Dicionário com dados do job.
            
        Returns:
            Objeto Job.
        """
        return Job(
            job_id=data["job_id"],
            source_url=data["source_url"],
            user_id=data.get("user_id"),
            status=JobStatus(data["status"]),
            stage=data.get("stage"),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            attempts=data.get("attempts", 0),
            error_message=data.get("error_message"),
            video_title=data.get("video_title"),
            video_duration=data.get("video_duration"),
            video_id=data.get("video_id"),
            storage_path=data.get("storage_path"),
            config=data.get("config", {}),
        )

    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        stage: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Job:
        """Atualiza o status de um job.
        
        Args:
            job_id: ID do job.
            status: Novo status.
            stage: Nova etapa.
            error_message: Mensagem de erro (se aplicável).
            
        Returns:
            Objeto Job atualizado.
            
        Raises:
            JobNotFoundError: Se o job não existir.
        """
        job = self.get_job(job_id)
        
        # Valida transição de estado
        if job.status == JobStatus.COMPLETED:
            self._get_logger().warning(f"Tentativa de atualizar job concluído: {job_id}")
            return job
        
        job.status = status
        if stage is not None:
            job.stage = stage
        if error_message is not None:
            job.error_message = error_message
        
        if status in [JobStatus.DOWNLOADING, JobStatus.TRANSCRIBING, JobStatus.ANALYZING, JobStatus.CUTTING]:
            if job.started_at is None:
                job.started_at = datetime.utcnow()
        
        if status == JobStatus.COMPLETED:
            job.completed_at = datetime.utcnow()
        
        self._save_job(job)
        
        return job

    def increment_attempts(self, job_id: str) -> Job:
        """Incrementa o contador de tentativas de um job.
        
        Args:
            job_id: ID do job.
            
        Returns:
            Objeto Job atualizado.
        """
        job = self.get_job(job_id)
        job.attempts += 1
        self._save_job(job)
        return job

    def set_video_metadata(
        self,
        job_id: str,
        title: str,
        duration: float,
        video_id: str,
    ) -> Job:
        """Define metadados do vídeo.
        
        Args:
            job_id: ID do job.
            title: Título do vídeo.
            duration: Duração em segundos.
            video_id: ID do vídeo.
            
        Returns:
            Objeto Job atualizado.
        """
        job = self.get_job(job_id)
        job.video_title = title
        job.video_duration = duration
        job.video_id = video_id
        job.storage_path = str(Config.get_storage_path(job_id))
        self._save_job(job)
        return job

    def get_all_jobs(self) -> List[Job]:
        """Obtém todos os jobs.
        
        Returns:
            Lista de objetos Job.
        """
        jobs = []
        storage_path = self.storage_base
        
        if not storage_path.exists():
            return jobs

        for job_dir in storage_path.iterdir():
            if job_dir.is_dir():
                job_path = job_dir / "job.json"
                if job_path.exists():
                    try:
                        with open(job_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        jobs.append(self._dict_to_job(data))
                    except (json.JSONDecodeError, KeyError) as e:
                        self._get_logger().error(f"Erro ao ler job {job_dir.name}: {e}")

        # Ordena por data de criação (mais recente primeiro)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs

    def cancel_job(self, job_id: str) -> Job:
        """Cancela um job.
        
        Args:
            job_id: ID do job.
            
        Returns:
            Objeto Job atualizado.
        """
        return self.update_job_status(job_id, JobStatus.CANCELLED)

    def delete_job(self, job_id: str) -> bool:
        """Deleta um job e seus arquivos.
        
        Args:
            job_id: ID do job.
            
        Returns:
            True se deletado com sucesso.
        """
        job_dir = Path(Config.get_storage_path(job_id))
        
        if job_dir.exists():
            import shutil
            shutil.rmtree(job_dir)
            return True
        
        return False
