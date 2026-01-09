"""
Fine-tuned 모델 평가 실행기 v2
- 실행: python -m evaluation.runners.finetuned_runner
- 파일저장: evaluation/results/finetuned/

- 1,2,3단계 결과 비교: python -m evaluation.runners.chat_compare_runner
- 파일저장: evaluation/results/compare/

BaselineRunner를 상속받아 스테이지명과 저장 경로만 변경
Azure Fine-tuned Llama 3.1 8B 모델 성능 평가용
"""

from pathlib import Path
from datetime import datetime
import json
import os

from evaluation.runners.baseline_runner import BaselineRunner
from evaluation.config import RESULTS_DIR


class FinetunedRunner(BaselineRunner):
    """Fine-tuned 모델 평가 러너 v2"""

    def __init__(self):
        os.environ["EVAL_MODE"] = "finetuned"
        print(f"[INFO] EVAL_MODE = finetuned")

        super().__init__()
        self.stage = "finetuned"

    def _generate_summary(self) -> dict:
        """요약 통계 생성 (스테이지명 변경)"""
        summary = super()._generate_summary()
        summary["stage"] = self.stage
        return summary

    def save_results(self, output_dir: str = None) -> Path:
        """결과 저장 (finetuned 경로)"""
        if output_dir is None:
            output_dir = f"{RESULTS_DIR}/finetuned"

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_dir) / f"results_{timestamp}.json"

        output_data = {
            "metadata": {
                "stage": self.stage,
                "version": "v2.1",
                "timestamp": datetime.now().isoformat(),
                "api_base_url": self.base_url,
                "description": "Azure Fine-tuned Llama 3.1 8B 모델 적용 버전",
                "model": "llama-3.1-8b-finetuned",
                "training_data": "1,500건 (건강 400, 운동 300, 챗봇 500, 판단패턴 300)",
                "improvements": [
                    "일관된 응답 형식 학습",
                    "전문 기준 인용 패턴 학습",
                    "판단 근거 명시 학습",
                    "친근한 전문가 톤 학습",
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
        print("📊 Fine-tuned 모델 평가 요약 ")
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

        # Fine-tuned 모델 특화 지표 강조
        print("\n" + "-" * 40)
        print("🎯 Fine-tuning 효과 핵심 지표:")

        health_stats = self.summary.get("by_service", {}).get("health", {})
        exercise_stats = self.summary.get("by_service", {}).get("exercise", {})
        chat_stats = self.summary.get("by_service", {}).get("chat", {})

        if health_stats:
            print(
                f"   건강분석 인용 점수(저자명): {health_stats.get('avg_citation_strict_score', 0):.1f}%"
            )
            print(
                f"   건강분석 개념 적용률: {health_stats.get('avg_concept_score', 0):.1f}%"
            )

        if exercise_stats:
            print(
                f"   운동분석 카보넨 인용율: {exercise_stats.get('karvonen_citation_rate', 0):.1f}%"
            )

        if chat_stats:
            print(
                f"   챗봇 인용 점수(저자명): {chat_stats.get('avg_citation_strict_score', 0):.1f}%"
            )
            print(f"   챗봇 개념 적용률: {chat_stats.get('avg_concept_score', 0):.1f}%")


if __name__ == "__main__":
    runner = FinetunedRunner()
    runner.run_all()
    runner.print_summary()
