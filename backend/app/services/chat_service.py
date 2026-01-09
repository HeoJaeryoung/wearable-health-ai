import os

from typing import Dict
from app.chat.base import BaseChatEngine
from app.chat.baseline_chat import BaselineChatEngine
from app.chat.langchain_chat import LangChainChatEngine
from app.chat.finetuned_chat import FinetunedChatEngine

VALID_PERSONAS = {
    "devil_coach",
    "angel_coach",
    "booster_coach",
}


class ChatService:
    """
    eval_mode 기반 챗봇 진입점
    """

    def __init__(self):
        self.engines: Dict[str, BaseChatEngine] = {
            "baseline": BaselineChatEngine(),
            "langchain": LangChainChatEngine(),
            "finetuned": FinetunedChatEngine(),
        }

    # -------------------------------------------
    # 1) 자유형 챗봇
    # -------------------------------------------
    def handle_chat(
        self,
        user_id: str,
        message: str,
        character: str,
        eval_mode: str = "baseline",
    ):
        persona = character if character in VALID_PERSONAS else "devil_coach"
        engine = self._get_engine(eval_mode)

        result = engine.respond(
            message=message,
            context={
                "user_id": user_id,
                "character": persona,
            },
        )

        return {
            "character": persona,
            "reply": result["reply"],
            "eval_mode": eval_mode,
            "model_type": result.get("model_type"),
        }

    # -------------------------------------------
    # 2) 고정형 챗봇 (LLM 평가 포함)
    # -------------------------------------------
    def handle_fixed_chat(
        self,
        user_id: str,
        question_type: str,
        character: str,
        eval_mode: str = "baseline",
    ):

        persona = character if character in VALID_PERSONAS else "devil_coach"
        engine = self._get_engine(eval_mode)

        fixed_questions = {
            "sleep": "어제 수면 상태를 기준으로 오늘 운동해도 될까요?",
            "fatigue": "피로도가 높은 상태에서 운동을 해도 괜찮을까요?",
            "motivation": "운동 의욕이 떨어졌을 때 어떻게 하면 좋을까요?",
        }

        message = fixed_questions.get(
            question_type,
            "오늘 운동을 어떻게 진행하면 좋을까요?",
        )

        result = engine.respond(
            message=message,
            context={
                "user_id": user_id,
                "character": persona,
                "question_type": question_type,
            },
        )

        return {
            "character": persona,
            "question_type": question_type,
            "reply": result["reply"],
            "eval_mode": eval_mode,
            "model_type": result.get("model_type"),
        }

    def _get_engine(self, eval_mode: str) -> BaseChatEngine:
        if eval_mode not in self.engines:
            raise ValueError(f"Unsupported eval_mode: {eval_mode}")
        return self.engines[eval_mode]
