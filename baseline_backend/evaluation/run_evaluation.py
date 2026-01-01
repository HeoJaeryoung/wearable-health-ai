"""
평가 실행 스크립트
"""

import argparse
import json
from pathlib import Path

from runners.baseline_runner import BaselineRunner


def main():
    parser = argparse.ArgumentParser(description="AI 시스템 평가 실행")
    parser.add_argument(
        "--stage",
        choices=["baseline", "langchain", "finetuned"],
        default="baseline",
        help="평가 단계 선택",
    )
    parser.add_argument(
        "--dataset",
        choices=["health", "routine", "chat", "all"],
        default="all",
        help="테스트 데이터셋 선택",
    )
    args = parser.parse_args()

    print(f"=== {args.stage.upper()} 평가 시작 ===")

    if args.stage == "baseline":
        runner = BaselineRunner()

        results = []

        if args.dataset in ["health", "all"]:
            health_results = runner.run_health_queries(
                "evaluation/datasets/health_queries.json"
            )
            results.extend(health_results)

        # 결과 저장
        runner.save_results(results)

        # 요약 출력
        summary = runner.generate_summary(results)
        print("\n=== 평가 요약 ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    else:
        print(f"{args.stage} 평가는 아직 구현되지 않았습니다.")


if __name__ == "__main__":
    main()
