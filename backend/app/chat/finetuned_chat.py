# app/chat/finetuned_chat.py
from app.chat.base import BaseChatEngine
from app.core.chatbot_engine.chat_generator import ChatGenerator


class FinetunedChatEngine(BaseChatEngine):
    def __init__(self):
        self.generator = ChatGenerator()
        self.generator.call_llm = self._call_finetuned

    def _call_finetuned(self, system_prompt, user_prompt, max_tokens=None):
        return "[FINETUNED PLACEHOLDER] " + user_prompt[:200]

    def respond(self, message: str, context: dict) -> dict:
        reply = self.generator.generate(
            user_id=context["user_id"],
            message=message,
            character=context["character"],
        )
        return {
            "reply": reply,
            "model_type": "finetuned",
        }
