import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

def call_llm(prompt: str) -> str:
    res = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3.1:8b",
            "prompt": prompt,
            "stream": False
        },
        timeout=60
    )

    # If Ollama itself failed
    if res.status_code != 200:
        raise RuntimeError(f"Ollama error: {res.text}")

    data = res.json()

    # Case 1: normal response
    if "response" in data:
        return data["response"]

    # Case 2: Ollama error payload
    if "error" in data:
        raise RuntimeError(f"Ollama returned error: {data['error']}")

    # Case 3: unexpected shape
    raise RuntimeError(f"Unexpected Ollama response: {data}")
