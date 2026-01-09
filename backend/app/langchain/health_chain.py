# app/langchain/health_chain.py

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.langchain.base import BaseLangChainEngine

from app.langchain.prompts.health_prompts import get_enhanced_health_prompt
from app.schemas.health import HealthAnalysisResponse
from app.config import LLM_MODEL_MAIN, LLM_TEMPERATURE, LLM_MAX_TOKENS

import os


class HealthAnalysisChain(BaseLangChainEngine):
    def __init__(self):
        llm = ChatOpenAI(
            model=LLM_MODEL_MAIN,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        super().__init__(llm=llm)

    def build_chain(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", get_enhanced_health_prompt()),
                ("user", "{user_prompt}"),
            ]
        )

        structured_llm = self.llm.with_structured_output(HealthAnalysisResponse)

        self.chain = prompt | structured_llm
        return self
