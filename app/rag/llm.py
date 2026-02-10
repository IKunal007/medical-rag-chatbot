import requests, json
from app.memory.utils import OLLAMA_BASE_URL


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
    return response

def call_llm_raw(prompt: str) -> str:
    # response should already be parsed JSON

    """
    Raw LLM call for controlled tasks like summarization.
    Uses the SAME Ollama /api/generate endpoint as call_llm,
    but returns plain text instead of JSON.
    """

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

    # IMPORTANT: for /api/generate, summary text is here
    return res.json().get("response", "").strip()



def call_llm_function(system_prompt, user_prompt, tools):
    payload = {
        "model": "llama3.1:8b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "tools": tools,
        "stream": False,
    }

    res = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=60,
    )

    if res.status_code != 200:
        raise RuntimeError(res.text)

    data = res.json()
    print("🧠 RAW CHAT RESPONSE:", data)

    message = data.get("message", {})

    # 1️⃣ Preferred: tool_calls
    tool_calls = message.get("tool_calls")
    if tool_calls:
        return tool_calls[0]["function"]["arguments"]

    # 2️⃣ Fallback: JSON in content
    content = message.get("content")
    if content:
        try:
            parsed = json.loads(content)
            if "parameters" in parsed:
                return parsed["parameters"]
            return parsed
        except json.JSONDecodeError:
            pass

    raise ValueError("LLM returned neither tool_calls nor valid JSON")
