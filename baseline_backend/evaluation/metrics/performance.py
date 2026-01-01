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
    def calculate_stats(values: list) -> dict:
        """
        통계 계산 (평균, 최소, 최대)
        """
        if not values:
            return {"avg": 0, "min": 0, "max": 0, "total": 0}
        
        return {
            "avg": round(sum(values) / len(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "total": round(sum(values), 4),
        }
    
    @staticmethod
    def calculate_token_stats(responses: list) -> dict:
        """
        응답들의 토큰 통계
        """
        token_counts = [PerformanceMetrics.estimate_tokens(r) for r in responses]
        return PerformanceMetrics.calculate_stats(token_counts)
