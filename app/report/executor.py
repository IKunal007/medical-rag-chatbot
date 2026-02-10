from app.report.extractor import (
    extract_exact_section,
    summarize_text
)
from app.report.table_extractor import extract_pdf_tables, extract_docx_tables
from app.report.figure_extractor import extract_pdf_figures
from app.report.extractor import load_docling_document
from app.storage.file_resolver import get_uploaded_pdf

def execute_plan(plan: dict, doc):
    """
    Executes an LLM-generated report plan.
    Plan format:
    {
        "sections": [
            {
                "action": "...",
                "section_name": "...",
                "source_section": "..."
            }
        ]
    }
    """

    # 🔒 Hard invariant check
    if not isinstance(plan.get("sections"), list):
        raise RuntimeError(f"execute_plan received invalid plan: {plan}")

    print("PLAN SENT TO EXECUTOR:", plan)

    report_sections = {}

    for step in plan["sections"]:
        action = step["action"]
        name = step.get("name", action)

        if action == "extract_section":
            report_sections[name] = extract_exact_section(
                doc,
                step["section_name"]
            )

        elif action == "extract_tables":
            report_sections[name] = extract_pdf_tables(doc)

        elif action == "extract_figures":
            report_sections[name] = extract_pdf_figures(doc)

        elif action == "summarize_section":
            report_sections[name] = summarize_text(
                source_section=step["source_section"],
            )

    return report_sections

