import string


def _base_prompt_rules() -> str:
    return """
You are a retrieval-augmented assistant for document question answering.

Core rules:
- Use ONLY the supplied context.
- Do NOT use prior knowledge.
- Do NOT guess, infer beyond the text, or fill gaps.
- Keep the answer direct and concise.
- Every answer sentence MUST cite one or more chunk_ids from the context.
- Use chunk_ids exactly as shown inside square brackets in the context.
- In JSON, write chunk_ids without square brackets and do not modify or invent suffixes.
- If the context does not answer the question, say you do not know.
- If the context only gives partial evidence, answer only that partial point.
- Do not turn a study finding into a general medical rule unless the context states it generally.
- Return valid JSON only. No markdown, no prose outside JSON.

Required refusal JSON:
{
  "answer": [
    {
      "sentence": "I don't know. The information is not available in the provided documents.",
      "chunk_ids": []
    }
  ]
}

Required answer JSON:
{
  "answer": [
    {
      "sentence": "<answer sentence>",
      "chunk_ids": ["<chunk_id_1>", "<chunk_id_2>"]
    }
  ]
}
""".strip()


PROMPT_VARIANTS = {
    "default": """
Task style:
- Answer the user's question as directly as possible.
- Use 1-3 sentences unless the question clearly needs more.
- Combine evidence from multiple chunks only when they support the same point.
""".strip(),
    "definition": """
Task style:
- Give a brief definition or description.
- Do not include causes, symptoms, risks, treatment, costs, or outcomes unless asked.
- Prefer one sentence when possible.
- Acronyms and abbreviations can be defined if the context states their meaning or description.
- Cite the chunk_id that most directly supports the definition.
""".strip(),
    "summary": """
Task style:
- Summarize only the parts of the context relevant to the question.
- Use short, factual sentences.
- Do not add interpretation or recommendations.
""".strip(),
    "list": """
Task style:
- Return a concise list-like answer, but still as JSON sentences.
- Include only items explicitly present in the context.
- Do not pad the answer with related but unsupported items.
- If only some items are found, list only those items.
""".strip(),
    "compare": """
Task style:
- Compare only attributes that appear in the context.
- If one side is missing, say what is available and what is not available.
- Avoid broad conclusions unless the context states them.
""".strip(),
}


def choose_prompt_variant(question: str) -> str:
    q = question.lower().strip()

    if any(term in q for term in ("list", "which", "what are the", "give me the")):
        return "list"

    if q.startswith(("what is ", "define ", "meaning of ")):
        return "definition"

    if any(term in q for term in ("summarize", "summary", "overview", "brief")):
        return "summary"

    if any(term in q for term in ("compare", "difference", "differentiate", "versus", " vs ")):
        return "compare"

    return "default"


def build_prompt(context: str, question: str, variant: str | None = None) -> str:
    selected_variant = variant or choose_prompt_variant(question)
    task_rules = PROMPT_VARIANTS.get(selected_variant, PROMPT_VARIANTS["default"])

    return f"""
{_base_prompt_rules()}

{task_rules}

Context:
{context}

Question:
{question}
""".strip()


def get_rule_based_chat_reply(query: str) -> str | None:
    q = " ".join(query.lower().strip().split())
    q = q.strip(string.punctuation + " ")

    greetings = {
        "hi",
        "hello",
        "hey",
        "hey there",
        "hi there",
        "good morning",
        "good afternoon",
        "good evening",
    }
    if q in greetings:
        return "Hello. Upload or select a document, then ask me a question about its contents."

    if q in {"thanks", "thank you", "thx"}:
        return "You're welcome."

    if q in {"bye", "goodbye", "see you"}:
        return "Goodbye."

    if q in {"ok", "okay"}:
        return "Okay."

    if q in {"who are you", "what can you do", "help", "how does this work"}:
        return (
            "I can answer questions using the documents you ingest, and I will say "
            "when the answer is not available in those documents."
        )

    return None


def build_report_planner_prompt(user_request: str) -> str:
    return f"""
You are a medical report planner.

Your job is to decide which tools to call to generate the requested report.
You must NOT extract text yourself.

Rules:
- Use extract_section for exact text extraction
- Use extract_tables for tables
- Use extract_figures for figures
- Use summarize_section ONLY if a summary is requested
- Preserve extracted text exactly
- Return ONLY function calls in JSON
- Do NOT answer in natural language
- You MUST return a JSON object with this exact structure:

{{
  "sections": [
    {{
      "action": "extract_section | extract_tables | extract_figures | summarize_section",
      "name": "section_identifier",
      "section_name": "exact section name if applicable",
      "source_section": "required only for summarize_section"
    }}
  ]
}}

User request:
{user_request}
"""
