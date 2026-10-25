$env:N8N_HOST = "zachery-nonempirical-marguerite.ngrok-free.dev"
$env:N8N_PROTOCOL = "https"
$env:N8N_PORT = "5678"
$env:N8N_EDITOR_BASE_URL = "https://zachery-nonempirical-marguerite.ngrok-free.dev/"
$env:WEBHOOK_URL = "https://zachery-nonempirical-marguerite.ngrok-free.dev/"
$env:N8N_PROXY_HOPS = "1"

n8n


ngrok http 5678


venv\Scripts\activate 
python -m app.main


& "D:\IA\llama.cpp\build\bin\Release\llama-server.exe" -m "D:\IA\Modelos\lmstudio-community\Qwen3.5-35B-A3B-GGUF\Qwen3.5-35B-A3B-Q4_K_M.gguf" --host 127.0.0.1 --port 8083  -c 240000 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 --cont-batching --temp 0.2 --top-p 0.9