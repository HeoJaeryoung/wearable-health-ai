from abc import ABC, abstractmethod


class BaseChatEngine(ABC):
    """
    모든 Chat Engine의 공통 인터페이스
    """

    @abstractmethod
    def respond(self, message: str, context: dict) -> dict:
        """
        Args:
            message: 사용자 입력
            context: health_summary / routine / meta 정보

        Returns:
            {
                "reply": str,
                "model_type": str,
                "model_name": str,
                "temperature": float
            }
        """
        pass
