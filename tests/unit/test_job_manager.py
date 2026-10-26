import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.models.job import Job, JobStatus
from app.services.job_manager import JobManager, JobNotFoundError


@pytest.fixture
def job_manager(tmp_path):
    """Cria um JobManager com storage temporário."""
    with patch.object(JobManager, '__init__', lambda self, storage_base=None: None):
        manager = JobManager()
        manager.storage_base = tmp_path
        manager.logger = MagicMock()
        return manager


class TestJobManager:
    """Testes para o JobManager."""

    def test_create_job(self, job_manager, tmp_path):
        """Testa criação de um job."""
        job = job_manager.create_job(
            source_url="https://www.youtube.com/watch?v=abc123",
            user_id="user_123",
        )

        assert job.job_id.startswith("job_")
        assert job.source_url == "https://www.youtube.com/watch?v=abc123"
        assert job.user_id == "user_123"
        assert job.status == JobStatus.QUEUED
        assert job.stage == "initialization"
        assert isinstance(job.created_at, datetime)

    def test_get_job(self, job_manager, tmp_path):
        """Testa obtenção de um job existente."""
        job = job_manager.create_job(
            source_url="https://www.youtube.com/watch?v=abc123",
        )

        retrieved_job = job_manager.get_job(job.job_id)

        assert retrieved_job.job_id == job.job_id
        assert retrieved_job.source_url == job.source_url

    def test_get_job_not_found(self, job_manager):
        """Testa obtenção de job inexistente."""
        with pytest.raises(JobNotFoundError):
            job_manager.get_job("job_nonexistent")

    def test_update_job_status(self, job_manager, tmp_path):
        """Testa atualização de status do job."""
        job = job_manager.create_job(source_url="https://www.youtube.com/watch?v=abc123")

        updated_job = job_manager.update_job_status(
            job.job_id,
            JobStatus.DOWNLOADING,
            stage="download",
        )

        assert updated_job.status == JobStatus.DOWNLOADING
        assert updated_job.stage == "download"
        assert updated_job.started_at is not None

    def test_update_job_status_completed(self, job_manager, tmp_path):
        """Testa atualização para status completed."""
        job = job_manager.create_job(source_url="https://www.youtube.com/watch?v=abc123")

        updated_job = job_manager.update_job_status(
            job.job_id,
            JobStatus.COMPLETED,
            stage="completed",
        )

        assert updated_job.status == JobStatus.COMPLETED
        assert updated_job.completed_at is not None

    def test_increment_attempts(self, job_manager, tmp_path):
        """Testa incremento de tentativas."""
        job = job_manager.create_job(source_url="https://www.youtube.com/watch?v=abc123")

        assert job.attempts == 0

        updated_job = job_manager.increment_attempts(job.job_id)
        assert updated_job.attempts == 1

        updated_job = job_manager.increment_attempts(job.job_id)
        assert updated_job.attempts == 2

    def test_set_video_metadata(self, job_manager, tmp_path):
        """Testa definição de metadados do vídeo."""
        job = job_manager.create_job(source_url="https://www.youtube.com/watch?v=abc123")

        updated_job = job_manager.set_video_metadata(
            job_id=job.job_id,
            title="Test Video",
            duration=120.5,
            video_id="abc123",
        )

        assert updated_job.video_title == "Test Video"
        assert updated_job.video_duration == 120.5
        assert updated_job.video_id == "abc123"

    def test_cancel_job(self, job_manager, tmp_path):
        """Testa cancelamento de job."""
        job = job_manager.create_job(source_url="https://www.youtube.com/watch?v=abc123")

        cancelled_job = job_manager.cancel_job(job.job_id)

        assert cancelled_job.status == JobStatus.CANCELLED

    def test_get_all_jobs(self, job_manager, tmp_path):
        """Testa obtenção de todos os jobs."""
        # Usa um storage_base temporário isolado
        from app.services.job_manager import JobManager
        isolated_manager = JobManager(storage_base=tmp_path)
        isolated_manager.logger = MagicMock()
        
        isolated_manager.create_job(source_url="https://www.youtube.com/watch?v=abc123")
        isolated_manager.create_job(source_url="https://www.youtube.com/watch?v=def456")

        jobs = isolated_manager.get_all_jobs()

        assert len(jobs) == 2

    def test_job_status_protection(self, job_manager, tmp_path):
        """Testa proteção de jobs concluídos."""
        job = job_manager.create_job(source_url="https://www.youtube.com/watch?v=abc123")
        
        # Conclui o job
        job_manager.update_job_status(job.job_id, JobStatus.COMPLETED)
        
        # Tenta atualizar novamente
        updated_job = job_manager.update_job_status(
            job.job_id,
            JobStatus.DOWNLOADING,
            stage="download",
        )
        
        # O status não deve mudar
        assert updated_job.status == JobStatus.COMPLETED
