import requests, json, os

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"  # fallback for local non-Docker runs
)

def call_llm(prompt: str) -> dict:
    res = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": "llama3.1:8b",
            "prompt": prompt,
            "stream": False,
            "temperature": 0
        },
        timeout=60
    )

    if res.status_code != 200:
        raise RuntimeError(f"Ollama error: {res.text}")

    raw = res.json().get("response", "").strip()

    # Case 1: Valid JSON
    try:
        return json.loads(raw)

    # Case 2: LLM violated format → force safe refusal
    except json.JSONDecodeError:
        return {
            "answer": [
                {
                    "sentence": "I don't know. The information is not available in the provided documents.",
                    "chunk_ids": []
                }
            ]
        }
