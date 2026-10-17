# Melhorias no Sistema de Logging - CortesVirais

## Resumo das Alterações

### 1. Rotação de Arquivos de Log
- **Antes**: Arquivo de log crescia indefinidamente
- **Depois**: Rotação automática baseada em tamanho (10MB padrão)
- **Configuração**: `LOG_MAX_BYTES` e `LOG_BACKUP_COUNT` no .env
- **Arquivos mantidos**: 7 backups rotacionados

### 2. Formato JSON para Arquivo
- **Antes**: Formato de texto simples no arquivo
- **Depois**: Formato JSON estruturado para fácil parsing
- **Campos**: timestamp, level, logger, message, module, function, line, job_id, request_id, extra

### 3. Contexto Dinâmico
- **Novo**: Variáveis de contexto para `job_id` e `request_id`
- **Novo**: `log_context()` como context manager
- **Exemplo**:
  ```python
  with log_context(job_id="job_abc123"):
      logger.info("Processando job")
  ```

### 4. Novos Métodos de Log
- `log_performance()`: Logs de performance com duração e tamanho
- `log_audit()`: Logs de auditoria para ações críticas
- `set_context()`, `clear_context()`, `get_context_adapter()`: Gerenciamento de contexto

### 5. Correções de Bugs
- Removido método `validate()` duplicado em `config.py`
- Corrigido `log_error_job()` e `log_step_failed()` que criavam logs vazios
- Corrigido todos os serviços que usavam `_get_logger()` inexistente

### 6. Correção de Depreciação FastAPI
- **Antes**: `@app.on_event("startup")` (depreciado)
- **Depois**: `@asynccontextmanager` com `lifespan`

## Arquivos Modificados

1. `app/infrastructure/logger.py` - Sistema de logging completo
2. `app/config.py` - Adicionado LOG_MAX_BYTES e LOG_BACKUP_COUNT
3. `app/main.py` - Migrado para lifespan events
4. `app/services/job_manager.py` - Corrigido uso de logger
5. `app/services/clip_validator.py` - Corrigido uso de logger
6. `app/services/llm_client.py` - Corrigido uso de logger
7. `app/services/clip_selection_service.py` - Corrigido uso de logger
8. `app/services/transcription_service.py` - Removido método _get_logger()
9. `.env.example` - Adicionado LOG_MAX_BYTES e LOG_BACKUP_COUNT
10. `.env` - Criado com configurações de log

## Novas Variáveis de Ambiente

```bash
LOG_MAX_BYTES=10485760        # Tamanho máximo do arquivo (10MB)
LOG_BACKUP_COUNT=7            # Número de backups mantidos
```

## Exemplos de Uso

### Log de Performance
```python
logger.log_performance(
    job_id="job_abc123",
    operation="video_processing",
    duration=5.234,
    size_bytes=52428800,  # 50MB
    extra_info="quality=high"
)
```

### Log de Auditoria
```python
logger.log_audit(
    action="delete",
    resource="job_abc123",
    user_id="user_456",
    details={"reason": "user_request"}
)
```

### Contexto Dinâmico
```python
with log_context(job_id="job_abc123"):
    logger.info("Processando job")
    logger.warning("Alerta dentro do contexto")
```

## Formato de Saída

### Console (Colorido)
```
2026-10-16 22:31:10 - cortesvirais - INFO - Configurando sistema de logs
```

### Arquivo (JSON)
```json
{
  "timestamp": "2026-10-16T22:31:10.123456",
  "level": "INFO",
  "logger": "cortesvirais",
  "message": "Configurando sistema de logs",
  "module": "logger",
  "function": "setup_logging",
  "line": 325
}
```

## Benefícios

1. **Gerenciamento de disco**: Arquivos rotacionados evitam esgotamento de espaço
2. **Análise facilitada**: Formato JSON permite ingestão em ELK/Splunk
3. **Rastreamento**: Contexto dinâmico facilita debugging de jobs
4. **Performance**: Logs estruturados com métricas de performance
5. **Auditoria**: Logs separados para ações críticas
6. **Conformidade**: Uso de APIs modernas do FastAPI
