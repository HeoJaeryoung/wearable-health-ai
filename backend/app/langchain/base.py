# app/langchain/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseLangChainEngine(ABC):
    """
    LangChain 기반 분석/챗봇 공통 베이스 엔진
    """

    def __init__(self, llm, retriever=None):
        self.llm = llm
        self.retriever = retriever
        self.chain = None  # 🔴 핵심: 모든 체인은 여기에 저장됨

    @abstractmethod
    def build_chain(self):
        """
        prompt | llm | parser (| retriever)
        체인 정의 책임은 자식에게 있음
        """
        raise NotImplementedError

    def run(self, **kwargs) -> Any:
        """
        공통 실행 진입점
        """
        if self.chain is None:
            raise RuntimeError("Chain is not built. Call build_chain() first.")

        return self.chain.invoke(kwargs)
