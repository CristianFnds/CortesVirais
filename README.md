# CortesVirais

Ferramenta de automação para identificar e extrair os melhores momentos de vídeos do YouTube, utilizando inteligência artificial local.

## Visão Geral

O CortesVirais implementa um pipeline completo de processamento de vídeo:

1. **Download**: Recebimento de URL do YouTube e download do vídeo
2. **Extração de Áudio**: Conversão do vídeo para formato de áudio
3. **Transcrição**: Transcrição do áudio usando faster-whisper
4. **Seleção Inteligente**: Identificação dos melhores momentos usando LLM local
5. **Geração de Clipes**: Criação dos cortes de vídeo usando FFmpeg
6. **API**: Disponibilização dos resultados via API FastAPI

## Arquitetura

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   YouTube   │────▶ |   Download   │────▶│   FFmpeg     │
└─────────────┘      │   Service    │      │   Service    │
                     └──────────────┘      └──────────────┘
                                                    │
                                                   ▼
┌────────────────┐      ┌──────────────┐      ┌──────────────┐
│   LLM Local    │◀──── │   Selection  │────▶│   Clip       │
│   (llama.cpp)  │      │   Service    │      │  Generator   │
└────────────────┘      └──────────────┘      └──────────────┘
                                                          │
                                                          ▼
                                                    ┌──────────────┐
                                                    │   FastAPI    │
                                                    │     API      │
                                                    └──────────────┘
```

## Componentes

- **Python**: Linguagem principal
- **FastAPI**: Framework da API HTTP
- **Uvicorn**: Servidor ASGI
- **yt-dlp**: Download de vídeos do YouTube
- **FFmpeg**: Processamento de áudio e vídeo
- **faster-whisper**: Transcrição de áudio
- **llama.cpp**: Execução de modelos de linguagem local
- **n8n**: Orquestração de automação (opcional)
- **ngrok**: Exposição HTTPS (opcional)
- **Telegram Bot API**: Integração com Telegram (opcional)

## Status Atual

- **FASE 1**: ✅ Concluída - Fundação do projeto
- **FASE 2**: ✅ Concluída - Download e preparação de mídia
- **FASE 3**: ✅ Concluída - Transcrição com timestamps
- **FASE 4**: ✅ Concluída - Seleção inteligente dos melhores momentos
- **FASE 5**: ✅ Concluída - Geração e validação dos clipes
- **FASE 6**: ✅ Concluída - Integração com n8n e Telegram
- **FASE 7**: ✅ Concluída - Testes, confiabilidade e otimização

## Pré-Requisitos

### Obrigatórios

- **Python 3.10+**
- **FFmpeg** (instalado e disponível no PATH)
- **Git**

### Opcionais (para pipeline completo)

- **llama.cpp** compilado (para execução de LLM local)
- **n8n** instalado (para orquestração)
- **ngrok** instalado (para exposição HTTPS)

## Instalação

### 1. Clone o repositório

```bash
git clone <repository-url>
cd CortesVirais
```

### 2. Configure o ambiente virtual

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

### 3. Instale as dependências Python

```bash
pip install -r requirements.txt
```

**Importante**: As seguintes dependências devem ser instaladas manualmente:

```bash
pip install faster-whisper yt-dlp
```

### 4. Instale o FFmpeg

**Windows (Chocolatey):**
```bash
choco install ffmpeg
```

**Windows (manual):**
1. Baixe em: https://ffmpeg.org/download.html
2. Extraia o arquivo
3. Adicione o diretório `bin` ao PATH do sistema

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

### 5. Configure variáveis de ambiente

```bash
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac
```

Edite o arquivo `.env` com suas configurações:

```dotenv
# API Python
PYTHON_HOST=127.0.0.1
PYTHON_PORT=8000

# LLM Local (API compatível com OpenAI)
LLM_API_URL=http://127.0.0.1:8083/v1
LLM_MODEL=Qwen3.5-35B-A3B-Q4_K_M
LLM_TIMEOUT=300

# FFmpeg (deixe vazio para usar ffmpeg do PATH)
FFMPEG_PATH=

# Telegram Bot (para integração futura)
TELEGRAM_BOT_TOKEN=

# Usuários Autorizados (IDs do Telegram, separados por vírgula)
AUTHORIZED_USERS=

# Armazenamento
STORAGE_BASE_PATH=storage

# Logs
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=7

# Processamento
MAX_CLIPS=5
TARGET_DURATION_SECONDS=60
MIN_DURATION_SECONDS=45
MAX_DURATION_SECONDS=70
```

## Execução

### Iniciar a API FastAPI

```bash
python -m app.main
```

A API estará disponível em **http://localhost:8000**

Documentação Swagger disponível em: **http://localhost:8000/docs**

### Iniciar servidor LLM local (llama.cpp)

```bash
# Windows
& "C:\caminho\para\llama.cpp\build\bin\Release\llama-server.exe" `
    -m "C:\caminho\para\modelo.gguf" `
    --host 127.0.0.1 `
    --port 8083 `
    -c 240000 `
    --flash-attn on `
    --cont-batching
```

**Parâmetros comuns:**
- `-m`: Caminho do modelo GGUF
- `--host`: Endereço da API (padrão: 127.0.0.1)
- `--port`: Porta da API (padrão: 8083)
- `-c`: Tamanho do contexto (padrão: 4096)
- `--flash-attn`: Ativar flash attention (se disponível)
- `--cont-batching`: Suporte a batch contínuo

### Configurar n8n (opcional)

```bash
n8n start
```

Acesso: **http://localhost:5678**

### Expor n8n via ngrok (opcional)

```bash
ngrok http 5678
```

Configure o webhook no n8n com a URL fornecida pelo ngrok.

### Configurar Telegram Bot (opcional)

1. Crie um bot no Telegram via [@BotFather](https://t.me/BotFather)
2. Anote o token fornecido
3. Adicione ao arquivo `.env`:
   ```
   TELEGRAM_BOT_TOKEN=SEU_TOKEN_AQUI
   ```

## Endpoints da API

### Health Check

```
GET /health
```

Verifica a disponibilidade da aplicação e suas dependências.

### Root

```
GET /
```

Retorna informações básicas da API.

### Jobs

```
POST /jobs
```

Cria um novo job de processamento.

```
GET /jobs/{job_id}
```

Retorna informações de um job específico.

```
GET /jobs
```

Lista todos os jobs.

### Clips

```
GET /clips/{job_id}
```

Retorna os clipes gerados para um job específico.

## Pipeline de Processamento

### Fluxo Completo

```
1. POST /jobs
   └─ Status: DOWNLOADING
   └─ Download do vídeo via yt-dlp

2. Status: AUDIO_EXTRACTED
   └─ Extração de áudio via FFmpeg

3. Status: TRANSCRIBING
   └─ Transcrição via faster-whisper

4. Status: ANALYZING
   └─ Análise do LLM local
   └─ Seleção dos melhores momentos

5. Status: CUTTING
   └─ Geração dos clipes via FFmpeg

6. Status: COMPLETED
   └─ Clipes prontos para download
```

### Status do Job

- `PENDING`: Job criado, aguardando processamento
- `DOWNLOADING`: Download do vídeo em andamento
- `AUDIO_EXTRACTED`: Áudio extraído com sucesso
- `TRANSCRIBING`: Transcrição em andamento
- `ANALYZING`: Análise do LLM em andamento
- `CUTTING`: Geração de clipes em andamento
- `COMPLETED`: Processamento concluído
- `FAILED`: Processamento falhou

## Armazenamento

Os arquivos processados são armazenados em `storage/{job_id}/`:

```
storage/
└── {job_id}/
    ├── {video_id}.mp4          # Vídeo original baixado
    ├── {video_id}_audio.m4a    # Áudio extraído
    ├── transcription.json      # Transcrição completa
    ├── clip_selection.json     # Momentos selecionados
    ├── generated_clips.json    # Clipes gerados
    └── clips/
        ├── {title}_{start}_{end}.mp4  # Clipe 1
        ├── {title}_{start}_{end}.mp4  # Clipe 2
        └── ...
```

## Testes

### Executar todos os testes

```bash
pytest tests/ -v
```

### Executar com cobertura

```bash
pytest tests/ -v --cov=app --cov-report=html
```

Abra `htmlcov/index.html` para ver o relatório.

### Executar testes específicos

```bash
pytest tests/unit/test_config.py -v
pytest tests/unit/test_job_manager.py -v
pytest tests/unit/test_clip_validator.py -v
```

## Solução de Problemas Comuns

### FFmpeg não encontrado

**Sintoma**: Erro "FFmpeg não encontrado" durante processamento

**Solução**:
1. Verifique se FFmpeg está instalado: `ffmpeg -version`
2. Adicione o diretório do FFmpeg ao PATH do sistema
3. Ou configure `FFMPEG_PATH` no arquivo `.env`

### LLM não responde

**Sintoma**: Erro "Não foi possível conectar ao LLM"

**Solução**:
1. Verifique se o servidor llama.cpp está rodando
2. Verifique se a porta 8083 está disponível
3. Teste conexão: `curl http://127.0.0.1:8083/v1/chat/completions`

### Download falha

**Sintoma**: Erro durante download do vídeo

**Solução**:
1. Verifique se yt-dlp está atualizado: `pip install --upgrade yt-dlp`
2. Verifique se a URL é válida
3. Verifique conexão com internet

### Modelo GGUF não encontrado

**Sintoma**: Erro ao carregar modelo

**Solução**:
1. Verifique se o caminho do modelo está correto
2. Verifique se o arquivo existe
3. Verifique permissões de leitura

## Estrutura do Projeto

```
CortesVirais/
├── app/
│   ├── api/              # Rotas da API
│   │   ├── routes_clips.py
│   │   └── routes_jobs.py
│   ├── infrastructure/   # Infraestrutura
│   │   ├── health.py     # Health check
│   │   └── logger.py     # Sistema de logging
│   ├── models/           # Modelos de dados
│   │   ├── clip.py
│   │   ├── job.py
│   │   └── transcript.py
│   ├── schemas/          # Esquemas de validação
│   │   └── job_schemas.py
│   ├── services/         # Serviços de negócio
│   │   ├── clip_generation_service.py
│   │   ├── clip_selection_service.py
│   │   ├── clip_validator.py
│   │   ├── download_service.py
│   │   ├── job_manager.py
│   │   ├── llm_client.py
│   │   ├── processing_pipeline.py
│   │   ├── transcription_service.py
│   │   └── url_validator.py
│   ├── config.py         # Configuração centralizada
│   └── main.py           # Aplicação FastAPI
├── logs/                 # Logs de aplicação (ignorado pelo Git)
├── storage/              # Armazenamento (ignorado pelo Git)
├── tests/
│   ├── unit/             # Testes unitários
│   ├── integration/      # Testes de integração
│   └── conftest.py       # Configuração do pytest
├── workflows/            # Workflows do n8n
├── .env.example          # Exemplo de variáveis de ambiente
├── .gitignore
├── requirements.txt
└── README.md
```
## Licença

Este projeto é desenvolvido para fins educacionais e de pesquisa.
