from app.chat.base import BaseChatEngine
from app.langchain.chat_chain import ChatChain


class LangChainChatEngine(BaseChatEngine):
    def __init__(self):
        self.chain = ChatChain()
        self.chain.build_chain()

    def respond(self, message: str, context: dict):
        result = self.chain.run(
            message=message,
            character=context["character"],
        )

        return {
            "reply": result,
            "model_type": "langchain",
        }
