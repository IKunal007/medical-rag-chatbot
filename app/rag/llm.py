import requests, json

OLLAMA_URL = "http://localhost:11434/api/generate"

def call_llm(prompt: str) -> dict:
    res = requests.post(
        OLLAMA_URL,
        json={
            "model": "llama3.1:8b",
            "prompt": prompt,
            "stream": False,
            "temperature": 0  # important for consistency
        },
        timeout=60
    )

    if res.status_code != 200:
        raise RuntimeError(f"Ollama error: {res.text}")

    data = res.json()

    if "response" not in data:
        raise RuntimeError(f"Unexpected Ollama payload: {data}")

    raw = data["response"].strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"LLM did not return valid JSON.\nRaw output:\n{raw}"
        ) from e

