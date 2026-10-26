from fastapi import FastAPI, status, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import sys

from app.config import Config
from app.infrastructure.health import HealthChecker
from app.infrastructure.logger import setup_logging, get_logger
from app.api.routes_jobs import router as jobs_router
from app.api.routes_clips import router as clips_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia eventos de lifespan da aplicação."""
    # Startup
    setup_logging(
        log_level=Config.LOG_LEVEL,
        log_file=Config.LOG_FILE,
        max_bytes=Config.LOG_MAX_BYTES,
        backup_count=Config.LOG_BACKUP_COUNT
    )
    logger.info("Starting CortesVirais API")

    issues = Config.validate()
    if issues:
        for issue in issues:
            logger.warning(issue)
    
    yield
    
    # Shutdown
    logger.info("Shutting down CortesVirais API")


app = FastAPI(
    title="CortesVirais API",
    description="API para automação de extração de melhores momentos de vídeos",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(jobs_router)
app.include_router(clips_router)

# Logger principal
logger = get_logger("cortesvirais", log_file=Config.LOG_FILE)


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Verifica a disponibilidade da aplicação e suas dependências."""
    checker = HealthChecker()
    health = checker.get_health()

    if health["status"] == "healthy":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy", "details": health["details"]},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "details": health["details"]},
        )


@app.get("/")
async def root():
    """Retorna informações básicas da API."""
    return {
        "name": "CortesVirais API",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=Config.PYTHON_HOST,
        port=Config.PYTHON_PORT,
        reload=True,
    )
