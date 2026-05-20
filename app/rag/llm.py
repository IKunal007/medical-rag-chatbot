import re
import requests, json
from app.memory.utils import OLLAMA_BASE_URL


def _parse_json_response(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Some local models wrap JSON in prose or code fences. Extract the first
    # JSON object so one formatting slip does not become a false refusal.
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise json.JSONDecodeError("No JSON object found", raw, 0)


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

    try:
        return _parse_json_response(raw)

    except json.JSONDecodeError:
        print("LLM JSON parse failed. Raw preview:", raw[:500])
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
