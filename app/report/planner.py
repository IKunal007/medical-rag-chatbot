from typing import Dict, Any, List
from app.rag.llm import call_llm_function

ALLOWED_ACTIONS = {
    "extract_exact",
    "extract_tables",
    "extract_figures",
    "summarize",
}


def plan_report_sections(user_request: str) -> Dict[str, Any]:
    """
    Uses the LLM ONLY to decide which extraction tools to call.
    Does NOT generate report content.
    """

    system_prompt = """
You are a planner for a medical report generator.

You MUST follow these rules:
- You do NOT write report content
- You ONLY decide which tools to call
- Medical text must be extracted verbatim
- Summaries ONLY if explicitly requested
- Return valid JSON only
"""

    user_prompt = f"""
User request:
{user_request}

Decide which sections are needed and what action to take for each.
"""

    functions = [
        {
            "name": "create_report_plan",
            "parameters": {
                "type": "object",
                "properties": {
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "action": {
                                    "type": "string",
                                    "enum": list(ALLOWED_ACTIONS)
                                },
                                "source_section": {"type": "string"}
                            },
                            "required": ["name", "action"]
                        }
                    }
                },
                "required": ["sections"]
            }
        }
    ]

    # 🔌 Call your LLM wrapper here

    result = call_llm_function(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        functions=functions,
        function_name="create_report_plan",
    )

    sections = result.get("sections", [])

    # 🔒 Hard validation (important)
    for sec in sections:
        if sec["action"] not in ALLOWED_ACTIONS:
            raise ValueError(f"Invalid action: {sec['action']}")

        if sec["action"] == "summarize" and "source_section" not in sec:
            raise ValueError("Summarize action requires source_section")

    return {"sections": sections}
