# CortesVirais

Ferramenta de automação para identificar e extrair os melhores momentos de vídeos do YouTube, utilizando inteligência artificial local.

## Requisitos

- Python 3.10+
- FFmpeg
- Acesso a um LLM local (opcional para FASE 1)

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

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure variáveis de ambiente

```bash
copy .env.example .env
```

Edite o arquivo `.env` com suas configurações.

### 5. Instale o FFmpeg

Baixe e instale o FFmpeg em: https://ffmpeg.org/download.html

Ou use o Chocolatey (Windows):

```bash
choco install ffmpeg
```

### 6. Inicie a API

```bash
python -m app.main
```

A API estará disponível em http://localhost:8000

## Estrutura do Projeto

```
CortesVirais/
├── app/
│   ├── api/              # Rotas da API
│   ├── models/           # Modelos de dados
│   ├── schemas/          # Esquemas de validação
│   ├── services/         # Serviços de negócio
│   ├── infrastructure/   # Infraestrutura (DB, LLM, etc)
│   ├── config.py         # Configuração centralizada
│   └── main.py           # Aplicação FastAPI
├── tests/
│   ├── unit/             # Testes unitários
│   ├── integration/      # Testes de integração
│   └── fixtures/         # Dados de teste
├── workflows/            # Workflows do n8n
├── storage/              # Armazenamento de arquivos (ignorado pelo Git)
├── logs/                 # Logs de aplicação (ignorado pelo Git)
├── .env.example          # Exemplo de variáveis de ambiente
├── .gitignore
├── requirements.txt
└── README.md
```

## Testes

```bash
pytest tests/ -v
```

## Fases de Desenvolvimento

- **FASE 1**: Fundação e configuração
- **FASE 2**: Download e preparação de mídia
- **FASE 3**: Transcrição
- **FASE 4**: Seleção de momentos com IA
- **FASE 5**: Geração dos clipes
- **FASE 6**: API de processamento
- **FASE 7**: Persistência e gerenciamento de estados
- **FASE 8**: Integração com n8n e Telegram
- **FASE 9**: Testes
- **FASE 10**: Otimização e confiabilidade

## Documentação

Veja [PLANO_DESENVOLVIMENTO.md](PLANO_DESENVOLVIMENTO.md) para detalhes completos do projeto.
