from fastapi import APIRouter, HTTPException, status, File, UploadFile, Query
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from typing import Optional

from app.config import Config
from app.services.job_manager import JobManager, JobNotFoundError
from app.infrastructure.logger import get_logger


router = APIRouter(prefix="/clips", tags=["clips"])
logger = get_logger(__name__)


@router.get("/{job_id}/{filename}")
async def download_clip(job_id: str, filename: str):
    """Baixa um arquivo de clipe gerado.
    
    Args:
        job_id: ID do trabalho.
        filename: Nome do arquivo do clipe.
        
    Returns:
        Arquivo MP4 para download.
        
    Raises:
        HTTPException: Se o trabalho ou arquivo não forem encontrados.
    """
    try:
        job_manager = JobManager()
        job = job_manager.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabalho não encontrado: {job_id}",
        )
    
    # Constrói o caminho completo do arquivo
    storage_path = Path(job.storage_path)
    clip_path = storage_path / "clips" / filename
    
    # Valida o caminho para evitar directory traversal
    try:
        clip_path.resolve().relative_to(storage_path.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Caminho de arquivo inválido",
        )
    
    if not clip_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo não encontrado: {filename}",
        )
    
    if not clip_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O caminho não é um arquivo",
        )
    
    # Verifica se o arquivo é um MP4
    if not filename.lower().endswith(".mp4"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas arquivos MP4 podem ser baixados",
        )
    
    logger.info(f"Download solicitado: {job_id}/{filename}")
    
    return FileResponse(
        path=str(clip_path),
        media_type="video/mp4",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/{job_id}/list")
async def list_clips(job_id: str):
    """Lista os clipes disponíveis para um trabalho.
    
    Args:
        job_id: ID do trabalho.
        
    Returns:
        Lista de clipes com metadados e URLs de download.
        
    Raises:
        HTTPException: Se o trabalho não for encontrado.
    """
    try:
        job_manager = JobManager()
        job = job_manager.get_job(job_id)
    except JobNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trabalho não encontrado: {job_id}",
        )
    
    storage_path = Path(job.storage_path)
    clips_dir = storage_path / "clips"
    
    if not clips_dir.exists():
        return {"job_id": job_id, "clips": []}
    
    clips = []
    for clip_file in clips_dir.glob("*.mp4"):
        clips.append({
            "filename": clip_file.name,
            "size": clip_file.stat().st_size,
            "download_url": f"/clips/{job_id}/{clip_file.name}",
        })
    
    return {
        "job_id": job_id,
        "clips": clips,
    }
