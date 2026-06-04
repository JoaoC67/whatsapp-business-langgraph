# WhatsApp Business → FastAPI → LangGraph + Claude → Redis + pgvector

Projeto de exemplo para receber mensagens do WhatsApp Business API em um webhook FastAPI, processar o texto com um pipeline LangGraph + Claude, armazenar estado em Redis e buscar contexto semântico em PostgreSQL + pgvector.

## Estrutura

- `app/main.py` - webhook FastAPI + envio de resposta WhatsApp
- `app/settings.py` - configuração de ambiente
- `app/pipeline.py` - pipeline LangGraph + Claude
- `app/retrieval.py` - busca semântica usando pgvector
- `requirements.txt` - dependências Python
- `.env.example` - variáveis de ambiente de exemplo
- `Dockerfile` + `docker-compose.yml` - execução local

## Rodando localmente

1. Copie `.env.example` para `.env`
2. Ajuste as variáveis de ambiente

### Usando Python local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Usando Docker Compose (recomendado)

```bash
cp .env.example .env
# Ajuste .env se necessário
docker compose up -d --build db app
```

Depois de subir os serviços, verifique o health:

```bash
curl http://127.0.0.1:8000/health
```

### Notas de ambiente em `.env`

No Docker Compose, o app se conecta aos serviços internos:

- `REDIS_URL=redis://redis:6379/0`
- `POSTGRES_DSN=postgresql://postgres:password@db:5432/whatsapp`

5. Configure o webhook do WhatsApp Business para enviar eventos para `http://<host>:8000/webhook`

## Endpoints úteis

- `GET /health` — retorna o status de conexão com Redis e PostgreSQL
- `GET /status` — retorna informações do app e da configuração do pipeline
- `POST /webhook` — webhook do WhatsApp Business

## Testando o webhook

Para simular um evento do WhatsApp Business e verificar se o app processa o payload corretamente:

```bash
curl -X POST http://127.0.0.1:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [
            {
              "from": "5511999999999",
              "text": {"body": "Olá, como vai?"}
            }
          ]
        }
      }]
    }]
  }'
```

O servidor deve aceitar o payload e retornar um JSON de aceitação, por exemplo `{"status":"accepted"}`.

## Testes

```bash
python3 -m pytest -q
```

## Observações

- Ajuste `app/pipeline.py` de acordo com o SDK real do LangGraph/Claude.
- Use o Redis para sessão e caching de contexto.
- Use o pgvector para armazenar embeddings e fazer buscas semânticas.
