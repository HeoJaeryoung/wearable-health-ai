from app.chat.baseline_chat import BaselineChatEngine
from app.chat.langchain_chat import LangChainChatEngine
from app.chat.finetuned_chat import FineTunedChatEngine


def run_chat_comparison(message: str, context: dict) -> dict:
    engines = {
        "baseline": BaselineChatEngine(),
        "langchain": LangChainChatEngine(),
        "finetuned": FineTunedChatEngine(),
    }

    results = {}
    for name, engine in engines.items():
        results[name] = engine.respond(message, context)

    return results
