from app.langchain.health_chain import HealthAnalysisChain
from app.core.health_interpreter import (
    get_user_health_prompt,
    interpret_bmi,
    interpret_oxygen,
)

_health_chain = HealthAnalysisChain()
_health_chain.build_chain()


def run_health_analysis_langchain(raw: dict) -> dict:
    user_prompt = get_user_health_prompt(raw)
    result = _health_chain.run(user_prompt=user_prompt)

    parsed = result.model_dump()
    parsed["bmi"] = interpret_bmi(raw)
    parsed["oxygen"] = interpret_oxygen(raw)
    return parsed
