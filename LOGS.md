# Sistema de Logging - CortesVirais

## Visão Geral

O sistema de logging do CortesVirais foi projetado para fornecer logs estruturados, coloridos (no terminal) e com suporte a rotação automática de arquivos.

## Componentes

### StructuredLogger

Classe principal de logging com suporte a:

- **Múltiplos handlers**: Console (colorido) e arquivo (JSON)
- **Rotação automática**: Arquivos rotacionados baseados em tamanho
- **Logs estruturados**: Métodos especializados para diferentes cenários
- **Contexto dinâmico**: Variáveis de contexto para rastreamento

### Formatters

1. **CustomFormatter**: Formato colorido para console
   - DEBUG: Cinza
   - INFO: Azul
   - WARNING: Amarelo
   - ERROR: Vermelho
   - CRITICAL: Vermelho bold

2. **JSONFormatter**: Formato JSON para arquivo
   - Timestamp ISO 8601
   - Nível, logger, módulo, função, linha
   - job_id e request_id quando disponíveis
   - Dados extras serializados

## Configuração

### Variáveis de Ambiente

```bash
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=logs/app.log             # Caminho do arquivo de log
LOG_MAX_BYTES=10485760            # Tamanho máximo (10MB padrão)
LOG_BACKUP_COUNT=7                # Número de backups (7 padrão)
```

### Inicialização

```python
from app.infrastructure.logger import setup_logging, get_logger

# Configuração principal
logger = setup_logging(
    log_level=Config.LOG_LEVEL,
    log_file=Config.LOG_FILE,
    max_bytes=Config.LOG_MAX_BYTES,
    backup_count=Config.LOG_BACKUP_COUNT
)

# Logger específico para módulo
module_logger = get_logger(__name__, log_file=Config.LOG_FILE)
```

## Métodos Especializados

### Logs de Job

```python
# Início de etapa
logger.log_step_start(job_id, stage, details={})

# Conclusão de etapa
logger.log_step_complete(job_id, stage, duration=1.23)

# Falha de etapa
logger.log_step_failed(job_id, stage, error, details={})

# Log estruturado
logger.log_job(job_id, stage, message, level="INFO")

# Erro de job
logger.log_error_job(job_id, stage, error, message="Erro")
```

### Logs de LLM

```python
logger.log_llm_request(job_id, prompt_length=1000, tokens=150, duration=2.5)
```

### Logs de Clip

```python
logger.log_clip_candidate(job_id, {
    'title': 'Melhor Momento',
    'start': 120.5,
    'end': 180.3,
    'score': 0.85
})
```

### Logs de Performance

```python
logger.log_performance(
    job_id="job_abc123",
    operation="video_processing",
    duration=5.234,
    size_bytes=52428800,  # 50MB
    extra_info="quality=high"
)
```

### Logs de Auditoria

```python
logger.log_audit(
    action="delete",
    resource="job_abc123",
    user_id="user_456",
    details={"reason": "user_request"}
)
```

## Contexto Dinâmico

### Usando Context Manager

```python
from app.infrastructure.logger import log_context

with log_context(job_id="job_abc123"):
    logger.info("Processando job")
    logger.warning("Alerta dentro do contexto")
# Contexto automaticamente limpo

# Ou com request_id
with log_context(request_id="req_xyz789"):
    logger.info("Processando requisição")
```

### Contexto Manual

```python
# Definir contexto
logger.set_context(job_id="job_abc123", request_id="req_xyz789")

# Usar logger com contexto
adapter = logger.get_context_adapter()
adapter.info("Mensagem com contexto")

# Limpar contexto
logger.clear_context()
```

## Formato de Saída

### Console

```
2024-01-15 10:30:45 - app.services.job_manager - INFO - [JOB:abc123] [PROCESSING] INICIANDO
```

### Arquivo (JSON)

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "logger": "app.services.job_manager",
  "message": "[JOB:abc123] [PROCESSING] INICIANDO",
  "module": "job_manager",
  "function": "process_job",
  "line": 76,
  "job_id": "abc123"
}
```

## Rotação de Arquivos

Os arquivos de log são automaticamente rotacionados quando:
- Tamanho atinge `LOG_MAX_BYTES` (10MB padrão)
- Mantém até `LOG_BACKUP_COUNT` (7 padrão) arquivos antigos

Arquivos rotacionados:
- `app.log.1` - Último arquivo rotacionado
- `app.log.2` - Segundo mais recente
- ...
- `app.log.7` - Mais antigo mantido

## Melhores Práticas

1. **Use logs estruturados** para jobs em vez de logs genéricos
2. **Inclua duration** em logs de performance para monitoramento
3. **Use contexto** para logs relacionados a jobs específicos
4. **Log de auditoria** para ações críticas (delete, update, access)
5. **Nível apropriado**:
   - DEBUG: Detalhes técnicos para desenvolvimento
   - INFO: Fluxo principal do sistema
   - WARNING: Eventos esperados mas incomuns
   - ERROR: Erros recuperáveis
   - CRITICAL: Erros que impedem operação

## Exemplos de Uso

### Service Pattern

```python
class MyService:
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def process(self, job_id):
        self.logger.log_step_start(job_id, "PROCESSING")
        try:
            # Processamento
            self.logger.log_step_complete(job_id, "PROCESSING", duration=1.5)
        except Exception as e:
            self.logger.log_step_failed(job_id, "PROCESSING", e)
            raise
```

### Pipeline Pattern

```python
def process_video(job_id, video_path):
    with log_context(job_id=job_id):
        logger.info("Iniciando processamento")
        
        # Etapa 1
        logger.log_step_start(job_id, "DOWNLOAD")
        download_video(video_path)
        logger.log_step_complete(job_id, "DOWNLOAD")
        
        # Etapa 2
        logger.log_step_start(job_id, "TRANSCODING")
        transcode_video(video_path)
        logger.log_step_complete(job_id, "TRANSCODING")
```
