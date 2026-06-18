import json
import httpx

BASE_URL = "http://127.0.0.1:8000"


def fetch_status():
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{BASE_URL}/status")
        return resp.status_code, resp.json()


def fetch_health():
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{BASE_URL}/health")
        return resp.status_code, resp.json()


def send_webhook_message(message_text: str, sender: str = "5511999999999"):
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": sender,
                                    "id": f"testmsg-{sender}-{message_text[:10]}",
                                    "text": {"body": message_text},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(f"{BASE_URL}/webhook", json=payload)
        return resp.status_code, resp.text


def main():
    print("Verificando /status")
    status_code, status_data = fetch_status()
    print("status", status_code)
    print(json.dumps(status_data, indent=2, ensure_ascii=False))

    print("\nVerificando /health")
    health_code, health_data = fetch_health()
    print("health", health_code)
    print(json.dumps(health_data, indent=2, ensure_ascii=False))

    print("\nEnviando mensagem de teste")
    code, body = send_webhook_message("Olá, isso é um teste de diálogo")
    print("webhook", code)
    print(body)


if __name__ == "__main__":
    main()
