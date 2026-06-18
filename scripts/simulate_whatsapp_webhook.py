import json
import sys

import httpx


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/webhook"
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "5511999999999",
                                    "id": "testmsg-123",
                                    "text": {"body": "Olá, como vai?"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload)
        print("URL:", url)
        print("Status:", response.status_code)
        try:
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except ValueError:
            print(response.text)


if __name__ == "__main__":
    main()
