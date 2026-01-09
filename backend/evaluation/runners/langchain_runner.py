"""
LangChain 평가 실행기 v2
- 실행: python -m evaluation.runners.langchain_runner
- 파일저장: evaluation/results/langchain/

- 1,2,3단계 결과 비교: python -m evaluation.runners.chat_compare_runner
- 파일저장: evaluation/results/compare/

BaselineRunner를 상속받아 스테이지명과 저장 경로만 변경
동일한 테스트셋, 동일한 메트릭으로 비교 평가
"""

from pathlib import Path
from datetime import datetime
import json
import os

from evaluation.runners.baseline_runner import BaselineRunner
from evaluation.config import RESULTS_DIR


class LangchainRunner(BaselineRunner):
    """LangChain 평가 러너 v2"""

    def __init__(self):
        super().__init__()  # 부모 초기화 먼저

        # 부모 초기화 후 EVAL_MODE 덮어쓰기
        os.environ["EVAL_MODE"] = "langchain"
        print("[INFO] EVAL_MODE = langchain (override)")

        self.stage = "langchain"

    def _generate_summary(self) -> dict:
        """요약 통계 생성 (스테이지명 변경)"""
        summary = super()._generate_summary()
        summary["stage"] = self.stage
        return summary

    def save_results(self, output_dir: str = None) -> Path:
        """결과 저장 (langchain 경로)"""
        if output_dir is None:
            output_dir = f"{RESULTS_DIR}/langchain"

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_dir) / f"results_{timestamp}.json"

        output_data = {
            "metadata": {
                "stage": self.stage,
                "version": "v2.1",
                "timestamp": datetime.now().isoformat(),
                "api_base_url": self.base_url,
                "description": "LangChain Chain + Structured Output 적용 버전",
                "improvements": [
                    "LangChain ChatPromptTemplate 사용",
                    "with_structured_output() 적용",
                    "Pipeline (prompt | llm) 구성",
                    "Few-shot Prompting 추가",
                ],
                "condition_grades": "6등급 (A/B/C+/C/D/F)",
            },
            "summary": self.summary,
            "results": self.results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 결과 저장: {output_path}")
        return output_path

    def print_summary(self):
        """요약 출력 (헤더 변경)"""
        print("\n" + "=" * 60)
        print("📊 LangChain 평가 요약 ")
        print("=" * 60)

        print(f"\n총 테스트: {self.summary.get('total_queries', 0)}건")

        for service, stats in self.summary.get("by_service", {}).items():
            service_name = {
                "health": "건강 분석",
                "exercise": "운동 분석",
                "chat": "챗봇",
            }.get(service, service)

            print(f"\n[{service_name}] ({stats['count']}건)")
            print(f"   정확도: {stats['avg_accuracy']:.1f}%")
            print(f"   키워드 매칭: {stats['avg_keyword_match']:.2f}")
            print(f"   일관성: {stats['avg_consistency']:.2f}")
            print(f"   응답 시간: {stats['avg_time']:.2f}초")

            # v2 지표
            print(f"   [v2 지표]")
            print(f"   응답 구조 점수: {stats['avg_structure_score']:.1f}%")
            print(f"   인용 점수: {stats['avg_citation_strict_score']:.1f}%")
            print(f"   개념 적용 점수: {stats['avg_concept_score']:.1f}%")
            print(f"   길이 적절성: {stats['avg_length_score']:.1f}%")

            if "grade_accuracy" in stats:
                print(f"   등급 정확도: {stats['grade_accuracy']:.1f}%")
            if "karvonen_citation_rate" in stats:
                print(f"   카보넨 인용율: {stats['karvonen_citation_rate']:.1f}%")

        if "overall" in self.summary:
            print(f"\n[전체 평균]")
            print(f"   정확도: {self.summary['overall']['avg_accuracy']:.1f}%")
            print(f"   응답 시간: {self.summary['overall']['avg_time']:.2f}초")
            print(
                f"   응답 구조 점수: {self.summary['overall']['avg_structure_score']:.1f}%"
            )


if __name__ == "__main__":
    runner = LangchainRunner()
    runner.run_all()
    runner.print_summary()
    runner.save_results()
