from app.report.extractor import (
    extract_exact_section,
    summarize_text
)
from app.report.table_extractor import extract_pdf_tables
from app.report.figure_extractor import extract_pdf_figures

def execute_plan(plan: dict, doc):
    """
    Executes an LLM-generated report plan.
    """

    if not isinstance(plan.get("sections"), list):
        raise RuntimeError(f"execute_plan received invalid plan: {plan}")

    print("PLAN SENT TO EXECUTOR:", plan)

    report_sections = {}

    for step in plan["sections"]:
        action = step["action"]
        name = step.get("name", action)

        # ----------------------------
        # Extract text section
        # ----------------------------
        if action == "extract_section":
            content = extract_exact_section(
                doc,
                step["section_name"]
            )

            report_sections[name] = {
                "type": "text",
                "content": content
            }

        # ----------------------------
        # Extract tables
        # ----------------------------
        elif action == "extract_tables":
            tables = extract_pdf_tables(doc)

            report_sections[name] = {
                "type": "tables",
                "content": tables
            }

        # ----------------------------
        # Extract figures
        # ----------------------------
        elif action == "extract_figures":
            figures = extract_pdf_figures(doc)

            report_sections[name] = {
                "type": "figures",
                "content": figures
            }

        # ----------------------------
        # Summarize
        # ----------------------------
        elif action == "summarize_section":
            summary = summarize_text(
                source_section=step["source_section"]
            )

            report_sections[name] = {
                "type": "text",
                "content": summary
            }

        else:
            print(f"[WARN] Unknown action: {action}")

    return report_sections
