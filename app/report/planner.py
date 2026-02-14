from typing import Dict, Any
import json
ALLOWED_ACTIONS = {
    "extract_section",
    "extract_tables",
    "extract_figures",
    "summarize_section",
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

REPORT_PLAN_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "create_report_plan",
            "description": "Creates a structured execution plan for report generation",
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
                                    "enum": [
                                        "extract_section",
                                        "extract_tables",
                                        "extract_figures",
                                        "summarize_section"
                                    ]
                                },
                                "section_name": {"type": "string"},
                                "source_section": {"type": "string"}
                            },
                            "required": ["name", "action"]
                        }
                    }
                },
                "required": ["sections"]
            }
        }
    }
]


import json
from typing import Dict, Any

def validate_and_normalize_plan(result: Dict[str, Any]) -> Dict[str, Any]:
    sections = result.get("sections")

    # 🔁 Handle stringified JSON from LLM
    if isinstance(sections, str):
        try:
            sections = json.loads(sections)
        except json.JSONDecodeError:
            raise ValueError(f"Sections is not valid JSON: {sections}")

    if not isinstance(sections, list):
        raise ValueError(f"Invalid plan format (sections not list): {result}")

    for sec in sections:
        if not isinstance(sec, dict):
            raise ValueError(f"Invalid section entry (not dict): {sec}")

        if sec["action"] not in ALLOWED_ACTIONS:
            raise ValueError(f"Invalid action: {sec['action']}")

        if sec["action"] == "summarize_section" and "source_section" not in sec:
            raise ValueError("Summarize action requires source_section")

    # 🔒 IMPORTANT: return the normalized structure
    return {"sections": sections}
