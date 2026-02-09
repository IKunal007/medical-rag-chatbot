import requests, json, os
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

def call_llm_function(
    system_prompt: str,
    user_prompt: str,
    functions: list,
    function_name: str,
):
    """
    Wrapper for function-calling style LLM interaction.
    Returns parsed JSON arguments.
    """

    # Reuse your existing LLM call logic here
    # Example assumes Ollama JSON mode or structured output

    response = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        functions=functions,
        function_name=function_name,
    )

    # response should already be parsed JSON
    return response

def call_llm_raw(prompt: str) -> str:
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
