# app/langchain/prompts/chat_prompt.py
from langchain_core.prompts import ChatPromptTemplate


def get_chat_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """당신은 {persona} 역할의 전문가입니다.
사용자의 건강 및 운동 관련 질문에 친절하고 전문적으로 답변하세요.
""",
            ),
            (
                "human",
                "{message}",
            ),
        ]
    )
