# app/langchain/exercise_chain.py

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.langchain.base import BaseLangChainEngine
from app.config import (
    LLM_MODEL_MAIN,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
)
from app.langchain.prompts.exercise_prompt import get_exercise_analysis_prompt


class ExerciseAnalysisChain(BaseLangChainEngine):
    """
    운동 루틴 분석 체인
    - 규칙 기반으로 생성된 '운동 루틴'에 대해
    - 왜 현재 건강 상태에 적합한지를
    - 전문 트레이너 관점에서 설명하는 역할
    """

    def __init__(self):
        llm = ChatOpenAI(
            model=LLM_MODEL_MAIN,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        super().__init__(llm)

    # -------------------------------------------------
    # 1) 체인 구성
    # -------------------------------------------------
    def build_chain(self):
        prompt = get_exercise_analysis_prompt()
        self.chain = prompt | self.llm

    # -------------------------------------------------
    # 2) 운동 목록 포맷팅
    # -------------------------------------------------
    def _format_items(self, items: list) -> str:
        """운동 목록을 프롬프트용 텍스트로 변환"""
        if not items:
            return "운동 목록 없음"

        lines = []
        for i, item in enumerate(items, 1):
            name = item.get("exercise_name", "Unknown")
            sets = item.get("set_count", 3)
            duration = item.get("duration_sec", 30)
            rest = item.get("rest_sec", 15)
            met = item.get("met", 4.0)

            lines.append(
                f"{i}. {name}: {sets}세트 × {duration}초, 휴식 {rest}초, MET {met}"
            )

        return "\n".join(lines)

    # -------------------------------------------------
    # 3) RAG 강도 텍스트 변환
    # -------------------------------------------------
    def _format_rag_strength(self, rag_strength: str) -> str:
        """RAG 강도를 사용자 친화적 텍스트로 변환"""
        mapping = {
            "strong": "과거 유사한 건강 패턴이 확인되었습니다.",
            "medium": "과거 패턴 정보가 일부 있습니다.",
            "weak": "과거 패턴 정보가 제한적입니다.",
            "none": "과거 패턴 정보가 없습니다.",
        }
        return mapping.get(rag_strength, mapping["none"])

    # -------------------------------------------------
    # 4) 실행 (변수 평탄화 포함)
    # -------------------------------------------------
    def run(
        self,
        health_summary: dict,
        score: int,
        settings: dict,
        items: list,
        health_context: str,
        rag_strength: str,
        weight: float,
    ) -> str:
        """
        운동 분석 실행

        Args:
            health_summary: 건강 요약 dict (score, grade, recommended_intensity 등)
            score: 건강 점수
            settings: 운동 설정
            items: 운동 목록
            health_context: 건강 컨텍스트 텍스트
            rag_strength: RAG 강도 (strong/medium/weak/none)
            weight: 체중 (kg)

        Returns:
            str: 운동 분석 텍스트
        """
        # 프롬프트 변수 평탄화
        prompt_vars = {
            # health_summary dict → 평탄화된 변수
            "health_summary_score": health_summary.get("score", score),
            "health_summary_grade": health_summary.get(
                "grade", settings.get("grade", "C")
            ),
            "health_summary_recommended_intensity": health_summary.get(
                "recommended_intensity", settings.get("intensity", "중")
            ),
            # 운동 목록 포맷팅
            "items": self._format_items(items),
            # 건강 컨텍스트
            "health_context": health_context or "건강 컨텍스트 정보 없음",
            # RAG 강도 텍스트 변환
            "rag_strength": self._format_rag_strength(rag_strength),
        }

        # 체인 실행
        if self.chain is None:
            raise RuntimeError("Chain is not built. Call build_chain() first.")

        result = self.chain.invoke(prompt_vars)

        # ChatOpenAI 응답 객체 처리
        if hasattr(result, "content"):
            return result.content.strip()

        return str(result)
