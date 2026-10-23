# Fase 5 — Geração e Validação de Clipes

## Visão Geral

Este serviço converte os intervalos selecionados pelo LLM em arquivos de vídeo MP4 utilizáveis, utilizando FFmpeg para cortes precisos.

## Arquitetura

### Classe Principal: `ClipGenerationService`

Local: `app/services/clip_generation_service.py`

#### Responsabilidades

1. **Geração de clipes** - Corta vídeos usando FFmpeg
2. **Validação** - Verifica integridade dos arquivos gerados
3. **Registro de falhas** - Mantém histórico de erros por clipe
4. **Prevenção de duplicação** - Garante que etapas repetidas não geram arquivos duplicados

### Métodos Principais

#### `generate_clips()`
Gera múltiplos clipes a partir de candidatos selecionados.

**Parâmetros:**
- `job_id`: ID do trabalho
- `audio_path`: Caminho do áudio extraído
- `video_path`: Caminho do vídeo original
- `candidates`: Lista de `ClipCandidate`
- `output_dir`: Diretório de saída

**Retorna:** Lista de `Clip` gerados com sucesso

**Fluxo:**
1. Cria diretório de saída
2. Para cada candidato:
   - Gera clipe com FFmpeg
   - Valida arquivo gerado
   - Registra sucesso ou falha
3. Retorna lista de clipes válidos

#### `_generate_clip()`
Gera um único clipe usando FFmpeg.

**Parâmetros:**
- `video_path`: Vídeo original
- `audio_path`: Áudio extraído
- `start_time`: Início do corte (segundos)
- `end_time`: Fim do corte (segundos)
- `output_path`: Caminho de saída

**Comando FFmpeg utilizado:**
```bash
ffmpeg -y -ss <start> -to <end> -i <video> \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  -shortest -movflags +faststart \
  -metadata title="<title>" <output>
```

**Parâmetros FFmpeg:**
- `-ss`, `-to`: Corte no tempo especificado
- `-c:v libx264`: Codec H.264 para compatibilidade
- `-preset fast`: Equilíbrio velocidade/qualidade
- `-crf 23`: Qualidade moderada (0-51)
- `-c:a aac`: Codec de áudio AAC
- `-b:a 128k`: Bitrate de áudio
- `-shortest`: Para quando o mais curto terminar
- `-movflags +faststart`: Otimizado para web

#### `_validate_clip()`
Valida um clipe gerado.

**Validações realizadas:**
1. Arquivo existe
2. Arquivo não está vazio
3. Duração dentro das tolerâncias (43-67s)
4. Possui stream de vídeo
5. Possui stream de áudio

**Retorna:** Dicionário com resultado da validação

### Tolerâncias de Duração

- **Duração alvo**: 45-65 segundos (configurável)
- **Tolerância**: ±2 segundos
- **Mínimo aceitável**: 43 segundos
- **Máximo aceitável**: 67 segundos

### Nomes de Arquivos

Padrão: `{titulo_sem_espacos}_{inicio}_{fim}.mp4`

Exemplo: `Melhor_Momento_120_180.mp4`

- Título truncado a 50 caracteres
- Espaços substituídos por underscores
- Timestamps em segundos (inteiro)

## Integração com Pipeline

### Fluxo Completo

```
1. Download → 2. Extração Áudio → 3. Transcrição → 4. Seleção LLM → 5. Geração Clipes
```

### Atualização de Status

O pipeline atualiza o status do job durante a geração:

```python
JobStatus.CUTTING  # Durante geração
JobStatus.COMPLETED  # Após conclusão
JobStatus.FAILED  # Em caso de erro
```

### Persistência

Informações dos clipes gerados são salvas em:
`{storage_path}/generated_clips.json`

Formato:
```json
[
  {
    "clip_id": "clip_abc123",
    "title": "Melhor Momento",
    "start": 120.5,
    "end": 180.3,
    "duration": 59.8,
    "output_path": "/storage/job_xyz/clips/Melhor_Momento_120_180.mp4",
    "status": "completed"
  }
]
```

## Tratamento de Erros

### Erros Comuns

1. **FFmpeg não encontrado**
   - Verifica disponibilidade antes de executar
   - Mensagem clara sobre caminho esperado

2. **Timeout de geração**
   - Timeout de 5 minutos por clipe
   - Erro específico para timeout

3. **Duração inválida**
   - Validação prévia antes de gerar
   - Erro antes de iniciar processamento

4. **Arquivo vazio**
   - Detectado na validação pós-geração
   - Clipe marcado como falha

### Registro de Falhas

Cada falha é registrada com:
- ID do clipe
- Título do candidato
- Tipo de erro
- Timestamp

Falhas não interrompem geração de outros clipes.

## Performance

### Otimizações

1. **Cortes precisos**: `-ss` antes de `-i` para seek rápido
2. **Qualidade balanceada**: CRF 23 com preset fast
3. **Web-ready**: `-movflags +faststart` para streaming
4. **Paralelização**: Potencial para gerar clipes em paralelo

### Métricas Registradas

Para cada clipe gerado:
- Duração exata
- Tamanho em bytes
- Tempo de processamento
- Status de validação

## Critérios de Aceite

### Funcionais

- [x] Cada arquivo final é reproduzível
- [x] Áudio sincronizado com vídeo
- [x] Duração dentro das tolerâncias configuradas
- [x] Nomes de arquivos previsíveis e consistentes
- [x] Falhas registradas por clipe individualmente

### Técnicos

- [x] Formato MP4 com H.264/AAC
- [x] Compatível com dispositivos móveis
- [x] Otimizado para web/mobile
- [x] Validação automática pós-geração
- [x] Prevenção de duplicação de arquivos

## Exemplos de Uso

### Geração em Lote

```python
service = ClipGenerationService()
clips = service.generate_clips(
    job_id="job_abc123",
    audio_path="/storage/job_abc123/audio.m4a",
    video_path="/storage/job_abc123/video.mp4",
    candidates=candidates,
    output_dir="/storage/job_abc123/clips"
)
```

### Geração Individual

```python
clip = service.generate_clip_single(
    job_id="job_abc123",
    video_path="/path/to/video.mp4",
    audio_path="/path/to/audio.m4a",
    start_time=120.5,
    end_time=180.3,
    output_path="/output/clip.mp4",
    title="Melhor Momento"
)
```

### Obter Informações

```python
info = service.get_clip_info("/path/to/clip.mp4")
print(f"Duração: {info['duration']}s")
print(f"Codec vídeo: {info['video_codec']}")
print(f"Codec áudio: {info['audio_codec']}")
```

## Dependências

- **FFmpeg**: Requerido para geração e validação
- **ffprobe**: Incluído no FFmpeg, usado para validação

## Limitações Conhecidas

1. **Seek impreciso**: Cortes podem não ser frame-perfect
2. **Qualidade**: CRF 23 pode não ser ideal para todos os vídeos
3. **Timeout**: 5 minutos pode ser insuficiente para vídeos muito longos
4. **Memória**: Vídeos muito grandes podem consumir muita RAM

## Melhorias Futuras

1. **Paralelização**: Gerar múltiplos clipes simultaneamente
2. **Adaptive CRF**: Ajustar qualidade baseado no conteúdo
3. **Re-encode mínimo**: Evitar re-encode quando possível
4. **Preview**: Gerar thumbnails para cada clipe
5. **Log detalhado**: Registrar cada comando FFmpeg executado
