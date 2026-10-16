from fastapi import APIRouter, HTTPException, status
from typing import List

from app.schemas.job_schemas import (
    JobCreateRequest,
    JobCreateResponse,
    JobResponse,
    JobStatusUpdate,
)
from app.models.job import Job, JobStatus
from app.services.job_manager import JobManager, JobNotFoundError
from app.services.processing_pipeline import ProcessingPipeline, ProcessingPipelineError


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(request: JobCreateRequest):
    """Cria um novo trabalho de processamento.
    
    Args:
        request: Requisição com URL do vídeo.
        
    Returns:
        ID do trabalho criado.
        
    Raises:
        HTTPException: Se a URL for inválida.
    """
    from app.services.url_validator import URLValidator, URLValidationError
    
    validator = URLValidator()
    
    try:
        validator.validate(request.source_url)
    except URLValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"URL inválida: {e}",
        )

    job_manager = JobManager()
    job = job_manager.create_job(
        source_url=request.source_url,
        user_id=request.user_id,
        config=request.options or {},
    )

    return JobCreateResponse(
        job_id=job.job_id,
        status=job.status.value,
        message="Processamento registrado",
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Obtém informações de um trabalho.
    
    Args:
        job_id: ID do trabalho.
        
    Returns:
        Informações do trabalho.
        
    Raises:
        HTTPException: Se o trabalho não for encontrado.
    """
    job_manager = JobManager()
    
    try:
        job = job_manager.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabalho não encontrado: {job_id}",
        )

    return JobResponse(
        job_id=job.job_id,
        status=job.status.value,
        stage=job.stage,
        source_url=job.source_url,
        video_title=job.video_title,
        video_duration=job.video_duration,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        attempts=job.attempts,
        error_message=job.error_message,
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs():
    """Lista todos os trabalhos.
    
    Returns:
        Lista de trabalhos.
    """
    job_manager = JobManager()
    jobs = job_manager.get_all_jobs()

    return [
        JobResponse(
            job_id=job.job_id,
            status=job.status.value,
            stage=job.stage,
            source_url=job.source_url,
            video_title=job.video_title,
            video_duration=job.video_duration,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            attempts=job.attempts,
            error_message=job.error_message,
        )
        for job in jobs
    ]


@router.post("/{job_id}/retry")
async def retry_job(job_id: str):
    """Solicita repetição de uma etapa recuperável.
    
    Args:
        job_id: ID do trabalho.
        
    Returns:
        Confirmação da tentativa.
        
    Raises:
        HTTPException: Se o trabalho não for encontrado ou não puder ser retryado.
    """
    job_manager = JobManager()
    
    try:
        job = job_manager.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabalho não encontrado: {job_id}",
        )

    if job.status == JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trabalho já concluído, não pode ser retryado",
        )

    job_manager.increment_attempts(job_id)
    job_manager.update_job_status(
        job_id,
        JobStatus.QUEUED,
        stage="retry",
        error_message=None,
    )

    return {
        "job_id": job_id,
        "message": "Tentativa reiniciada",
        "attempts": job.attempts + 1,
    }


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Solicita cancelamento de um trabalho.
    
    Args:
        job_id: ID do trabalho.
        
    Returns:
        Confirmação do cancelamento.
        
    Raises:
        HTTPException: Se o trabalho não for encontrado.
    """
    job_manager = JobManager()
    
    try:
        job = job_manager.cancel_job(job_id)
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabalho não encontrado: {job_id}",
        )

    return {
        "job_id": job_id,
        "message": "Trabalho cancelado",
        "status": job.status.value,
    }


@router.post("/{job_id}/start")
async def start_job(job_id: str):
    """Inicia o processamento de um trabalho.
    
    Args:
        job_id: ID do trabalho.
        
    Returns:
        Confirmação do início.
        
    Raises:
        HTTPException: Se o trabalho não for encontrado.
    """
    from app.services.processing_pipeline import ProcessingPipeline
    
    job_manager = JobManager()
    
    try:
        job = job_manager.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabalho não encontrado: {job_id}",
        )

    if job.status != JobStatus.QUEUED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trabalho não está em estado queued (atual: {job.status.value})",
        )

    pipeline = ProcessingPipeline()
    
    try:
        result = pipeline.process(
            job_id=job_id,
            url=job.source_url,
            detect_language=True,
        )
        
        return {
            "job_id": job_id,
            "message": "Processamento concluído",
            "result": result,
        }
        
    except ProcessingPipelineError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
