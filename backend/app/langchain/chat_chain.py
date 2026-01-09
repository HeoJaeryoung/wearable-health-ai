# app/langchain/chat_chain.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.langchain.base import BaseLangChainEngine
from app.langchain.prompts.chat_prompt import get_chat_prompt


class ChatChain(BaseLangChainEngine):
    def __init__(self, llm=None, retriever=None):
        if llm is None:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
        super().__init__(llm=llm, retriever=retriever)

    def build_chain(self):
        prompt = get_chat_prompt()
        self.chain = prompt | self.llm | StrOutputParser()

    def run(self, message: str, character: str) -> str:
        if self.chain is None:
            raise RuntimeError("Chain is not built. Call build_chain() first.")
        return self.chain.invoke({"message": message, "persona": character})
