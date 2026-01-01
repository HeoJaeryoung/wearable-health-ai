"""
Baseline 평가 실행기
"""

import json
import requests
from pathlib import Path
from datetime import datetime

from evaluation.config import API_BASE_URL, TEST_USER_ID, EVALUATION_ROUNDS
from evaluation.metrics import (
    ResponseQualityMetrics,
    PerformanceMetrics,
    RAGQualityMetrics,
)


class BaselineRunner:

    def __init__(self):
        self.base_url = API_BASE_URL
        self.user_id = TEST_USER_ID
        self.results = []

    def run_health_queries(self, dataset_path: str) -> list:
        """
        건강 질문 테스트 실행
        """
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        results = []

        for query in dataset.get("queries", []):
            query_results = {
                "id": query["id"],
                "input": query["input"],
                "responses": [],
                "times": [],
                "scores": {},
            }

            # 여러 번 실행 (일관성 측정)
            for _ in range(EVALUATION_ROUNDS):
                result, elapsed = self._call_chat_api(query["input"])
                query_results["responses"].append(result)
                query_results["times"].append(elapsed)

            # 점수 계산
            query_results["scores"] = {
                "keyword_match": ResponseQualityMetrics.keyword_match_score(
                    query_results["responses"][0], query.get("expected_keywords", [])
                ),
                "consistency": ResponseQualityMetrics.consistency_score(
                    query_results["responses"]
                ),
                "avg_time": PerformanceMetrics.calculate_stats(query_results["times"])[
                    "avg"
                ],
            }

            results.append(query_results)

        return results

    def _call_chat_api(self, message: str) -> tuple[str, float]:
        """
        챗봇 API 호출
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "user_id": self.user_id,
            "message": message,
            "character": "default",
        }

        start = datetime.now()
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            elapsed = (datetime.now() - start).total_seconds()
            return result.get("response", ""), elapsed
        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            return f"Error: {str(e)}", elapsed

    def save_results(
        self, results: list, output_dir: str = "evaluation/results/baseline"
    ):
        """
        결과 저장
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_dir) / f"results_{timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"결과 저장: {output_path}")
        return output_path

    def generate_summary(self, results: list) -> dict:
        """
        요약 통계 생성
        """
        total_queries = len(results)
        avg_keyword_score = (
            sum(r["scores"]["keyword_match"] for r in results) / total_queries
        )
        avg_consistency = (
            sum(r["scores"]["consistency"] for r in results) / total_queries
        )
        avg_time = sum(r["scores"]["avg_time"] for r in results) / total_queries

        return {
            "total_queries": total_queries,
            "avg_keyword_match": round(avg_keyword_score, 4),
            "avg_consistency": round(avg_consistency, 4),
            "avg_response_time": round(avg_time, 4),
        }
