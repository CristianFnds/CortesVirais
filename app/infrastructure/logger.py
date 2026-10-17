import logging
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from contextvars import ContextVar


class CustomFormatter(logging.Formatter):
    """Formatador personalizado com cores para terminal."""

    grey = "\x1b[38;21m"
    blue = "\x1b[34;1m"
    yellow = "\x1b[33;1m"
    red = "\x1b[31;1m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    green = "\x1b[32;1m"

    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: blue + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class JSONFormatter(logging.Formatter):
    """Formatador JSON para logs estruturados em arquivo."""

    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "exc_info") and record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "job_id") and record.job_id:
            log_record["job_id"] = record.job_id

        if hasattr(record, "request_id") and record.request_id:
            log_record["request_id"] = record.request_id

        if hasattr(record, "extra_data"):
            log_record["extra"] = record.extra_data

        return json.dumps(log_record, ensure_ascii=False)


class ContextAdapter(logging.LoggerAdapter):
    """LoggerAdapter com contexto dinâmico."""

    def process(self, msg, kwargs):
        extra = self.extra.copy() if self.extra else {}
        if hasattr(self.logger, "context_vars"):
            for key, value in self.logger.context_vars.items():
                extra[key] = value
        return super().process(msg, kwargs)


# Variáveis de contexto para rastreamento
job_id_var: ContextVar[str] = ContextVar("job_id", default=None)
request_id_var: ContextVar[str] = ContextVar("request_id", default=None)


class StructuredLogger:
    """Logger com suporte a logs estruturados para rastreamento de processos."""

    def __init__(self, name: str, level: int = logging.INFO, log_file: Optional[str] = None, 
                 max_bytes: int = 10*1024*1024, backup_count: int = 7):
        """Inicializa o logger estruturado.
        
        Args:
            name: Nome do logger.
            level: Nível de log.
            log_file: Caminho do arquivo de log.
            max_bytes: Tamanho máximo do arquivo antes da rotação.
            backup_count: Número de arquivos de backup.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.context_vars = {}
        
        # Evita duplicação de handlers
        if not self.logger.handlers:
            # Handler para console
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(CustomFormatter())
            self.logger.addHandler(console_handler)
            
            # Handler para arquivo com rotação
            if log_file:
                log_path = Path(log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = RotatingFileHandler(
                    log_path,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding="utf-8"
                )
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(JSONFormatter())
                self.logger.addHandler(file_handler)

    def set_context(self, **kwargs):
        """Define contexto para logs subsequentes.
        
        Args:
            **kwargs: Pares chave-valor para contexto.
        """
        for key, value in kwargs.items():
            self.logger.context_vars[key] = value

    def clear_context(self):
        """Limpa o contexto atual."""
        self.logger.context_vars.clear()

    def get_context_adapter(self):
        """Retorna um adaptador de logger com contexto atual.
        
        Returns:
            ContextAdapter com contexto atual.
        """
        return ContextAdapter(self.logger, self.logger.context_vars)

    def debug(self, msg: str, *args, **kwargs):
        """Log no nível DEBUG."""
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """Log no nível INFO."""
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """Log no nível WARNING."""
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """Log no nível ERROR."""
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """Log no nível CRITICAL."""
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """Log de exceção com traceback."""
        self.logger.exception(msg, *args, **kwargs)

    def log_job(self, job_id: str, stage: str, message: str, level: str = "INFO"):
        """Log estruturado para rastreamento de jobs.
        
        Args:
            job_id: ID do job.
            stage: Etapa do processamento.
            message: Mensagem do log.
            level: Nível do log.
        """
        log_method = getattr(self.logger, level.lower())
        log_method(f"[JOB:{job_id}] [{stage}] {message}")

    def log_error_job(self, job_id: str, stage: str, error: Exception, message: str = "Erro"):
        """Log de erro estruturado para jobs.
        
        Args:
            job_id: ID do job.
            stage: Etapa do processamento.
            error: Exceção lançada.
            message: Mensagem do log.
        """
        self.logger.error(f"[JOB:{job_id}] [{stage}] {message}: {error}", extra={"job_id": job_id})

    def log_step_start(self, job_id: str, stage: str, details: Optional[dict] = None):
        """Log de início de etapa.
        
        Args:
            job_id: ID do job.
            stage: Etapa do processamento.
            details: Detalhes adicionais.
        """
        self.logger.info(f"[JOB:{job_id}] [{stage}] INICIANDO")
        if details:
            for key, value in details.items():
                self.logger.debug(f"[JOB:{job_id}] [{stage}] {key}={value}")

    def log_step_complete(self, job_id: str, stage: str, duration: Optional[float] = None):
        """Log de conclusão de etapa.
        
        Args:
            job_id: ID do job.
            stage: Etapa do processamento.
            duration: Duração da etapa em segundos.
        """
        if duration:
            self.logger.info(f"[JOB:{job_id}] [{stage}] CONCLUÍDO ({duration:.2f}s)")
        else:
            self.logger.info(f"[JOB:{job_id}] [{stage}] CONCLUÍDO")

    def log_step_failed(self, job_id: str, stage: str, error: Exception, details: Optional[dict] = None):
        """Log de falha de etapa.
        
        Args:
            job_id: ID do job.
            stage: Etapa do processamento.
            error: Exceção lançada.
            details: Detalhes adicionais.
        """
        self.logger.error(f"[JOB:{job_id}] [{stage}] FALHOU: {error}", extra={"job_id": job_id})
        self.logger.exception("", extra={"job_id": job_id})
        if details:
            for key, value in details.items():
                self.logger.error(f"[JOB:{job_id}] [{stage}] {key}={value}", extra={"job_id": job_id})

    def log_llm_request(self, job_id: str, prompt_length: int, tokens: int, duration: float):
        """Log de requisição LLM.
        
        Args:
            job_id: ID do job.
            prompt_length: Tamanho do prompt em caracteres.
            tokens: Número de tokens.
            duration: Duração da requisição em segundos.
        """
        self.logger.info(f"[JOB:{job_id}] [LLM] Prompt: {prompt_length} chars, Tokens: {tokens}, Duration: {duration:.2f}s")

    def log_clip_candidate(self, job_id: str, candidate: dict):
        """Log de candidato de clipe.
        
        Args:
            job_id: ID do job.
            candidate: Dicionário com dados do candidato.
        """
        self.logger.info(
            f"[JOB:{job_id}] [CLIP] {candidate.get('title', 'Sem título')}: "
            f"{candidate.get('start', 0):.1f}-{candidate.get('end', 0):.1f}s "
            f"(score: {candidate.get('score', 0):.2f})"
        )

    def log_performance(self, job_id: str, operation: str, duration: float, 
                        size_bytes: Optional[int] = None, extra_info: Optional[str] = None):
        """Log de performance de operações.
        
        Args:
            job_id: ID do job.
            operation: Nome da operação.
            duration: Duração em segundos.
            size_bytes: Tamanho processado em bytes.
            extra_info: Informações adicionais.
        """
        log_msg = f"[JOB:{job_id}] [PERF] {operation}: {duration:.3f}s"
        if size_bytes:
            size_mb = size_bytes / (1024 * 1024)
            log_msg += f" | {size_mb:.2f}MB"
        if extra_info:
            log_msg += f" | {extra_info}"
        self.logger.info(log_msg)

    def log_audit(self, action: str, resource: str, user_id: Optional[str] = None, 
                  details: Optional[dict] = None):
        """Log de auditoria para ações críticas.
        
        Args:
            action: Ação realizada (create, update, delete, access).
            resource: Recurso afetado.
            user_id: ID do usuário que realizou a ação.
            details: Detalhes adicionais da ação.
        """
        log_msg = f"[AUDIT] {action} {resource}"
        if user_id:
            log_msg += f" | user: {user_id}"
        self.logger.warning(log_msg)
        if details:
            for key, value in details.items():
                self.logger.debug(f"[AUDIT] {key}: {value}")


# Logger padrão para o módulo
def get_logger(name: str, log_file: Optional[str] = None) -> StructuredLogger:
    """Retorna um logger estruturado.
    
    Args:
        name: Nome do logger.
        log_file: Caminho do arquivo de log.
        
    Returns:
        Instância de StructuredLogger.
    """
    return StructuredLogger(name, log_file=log_file)


# Logger padrão para a aplicação
def setup_logging(log_level: str = "INFO", log_file: str = "logs/app.log",
                  max_bytes: int = 10*1024*1024, backup_count: int = 7) -> StructuredLogger:
    """Configura o sistema de logs e retorna o logger principal.
    
    Args:
        log_level: Nível de log.
        log_file: Caminho do arquivo de log.
        max_bytes: Tamanho máximo do arquivo antes da rotação.
        backup_count: Número de arquivos de backup.
        
    Returns:
        Logger principal configurado.
    """
    logger = StructuredLogger("cortesvirais", level=getattr(logging, log_level), 
                             log_file=log_file, max_bytes=max_bytes, backup_count=backup_count)
    logger.info("Configurando sistema de logs")
    logger.info(f"Nível de log: {log_level}")
    logger.info(f"Arquivo de log: {log_file}")
    logger.info(f"Rotação: max_bytes={max_bytes}, backup_count={backup_count}")
    return logger


def log_context(job_id: Optional[str] = None, request_id: Optional[str] = None):
    """Cria um contexto de log para rastreamento.
    
    Args:
        job_id: ID do job para contexto.
        request_id: ID da requisição para contexto.
        
    Returns:
        ContextManager para uso com 'with'.
    """
    from contextvars import copy_context
    
    class LogContext:
        def __init__(self, logger: StructuredLogger, job_id: Optional[str], request_id: Optional[str]):
            self.logger = logger
            self.job_id = job_id
            self.request_id = request_id
            self.old_job_id = None
            self.old_request_id = None
            
        def __enter__(self):
            if self.job_id:
                self.old_job_id = job_id_var.get()
                job_id_var.set(self.job_id)
            if self.request_id:
                self.old_request_id = request_id_var.get()
                request_id_var.set(self.request_id)
            self.logger.set_context(job_id=self.job_id, request_id=self.request_id)
            return self.logger.get_context_adapter()
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.job_id and self.old_job_id is not None:
                job_id_var.set(self.old_job_id)
            elif self.job_id:
                job_id_var.set(None)
            if self.request_id and self.old_request_id is not None:
                request_id_var.set(self.old_request_id)
            elif self.request_id:
                request_id_var.set(None)
            self.logger.clear_context()
    
    return LogContext(StructuredLogger("cortesvirais"), job_id, request_id)
