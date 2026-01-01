"""
성능 측정 (시간, 토큰)
"""

import time
from typing import Callable, Any


class PerformanceMetrics:

    @staticmethod
    def measure_response_time(func: Callable, *args, **kwargs) -> tuple[Any, float]:
        """
        함수 실행 시간 측정 (초)

        Returns:
            (결과, 실행시간)
        """
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()

        return result, end - start

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        토큰 수 추정 (대략적)
        한글: 글자당 ~2토큰, 영어: 단어당 ~1.3토큰
        """
        # 간단한 추정: 문자 수 / 2
        return len(text) // 2

    @staticmethod
    def calculate_stats(times: list) -> dict:
        """
        시간 통계 계산
        """
        if not times:
            return {"avg": 0, "min": 0, "max": 0}

        return {
            "avg": sum(times) / len(times),
            "min": min(times),
            "max": max(times),
        }
