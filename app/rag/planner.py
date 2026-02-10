from app.rag.functions import REPORT_FUNCTIONS
from app.rag.prompt import build_report_planner_prompt
from app.rag.llm import call_llm

def plan_report(user_prompt: str):
    prompt = build_report_planner_prompt(user_prompt)

    response = call_llm(
        prompt=prompt,
        functions=REPORT_FUNCTIONS,
        function_call="auto"
    )

    return response
