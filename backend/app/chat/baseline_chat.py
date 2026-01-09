from openai import OpenAI
from app.chat.base import BaseChatEngine
from app.config import LLM_MODEL_MAIN, LLM_TEMPERATURE, LLM_MAX_TOKENS

client = OpenAI()


class BaselineChatEngine(BaseChatEngine):
    def respond(self, message: str, context: dict) -> dict:
        response = client.chat.completions.create(
            model=LLM_MODEL_MAIN,
            messages=[
                {
                    "role": "system",
                    "content": "당신은 전문 피트니스 트레이너입니다.",
                },
                {
                    "role": "user",
                    "content": message,
                },
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )

        return {
            "reply": response.choices[0].message.content.strip(),
            "model_type": "baseline",
        }
