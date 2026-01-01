"""
평가 실행 스크립트

사용법:
    python run_evaluation.py --stage baseline --dataset all
    python run_evaluation.py --stage baseline --dataset health
    python run_evaluation.py --stage langchain --dataset all
    python run_evaluation.py --stage finetuned --dataset all
"""

import argparse
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluation.runners.baseline_runner import BaselineRunner


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
        choices=["health", "exercise", "chat", "all"],
        default="all",
        help="테스트 데이터셋 선택",
    )
    parser.add_argument("--verbose", action="store_true", help="상세 출력")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"🚀 {args.stage.upper()} 평가 시작")
    print(f"{'='*60}")
    print(f"데이터셋: {args.dataset}")

    if args.stage == "baseline":
        runner = BaselineRunner()

        if args.dataset == "all":
            runner.run_all()
        else:
            # 개별 데이터셋 실행
            datasets_dir = Path("evaluation/datasets")
            if args.dataset == "health":
                runner.results["health"] = runner._run_health_queries(
                    datasets_dir / "health_queries.json"
                )
            elif args.dataset == "exercise":
                runner.results["exercise"] = runner._run_exercise_queries(
                    datasets_dir / "exercise_queries.json"
                )
            elif args.dataset == "chat":
                runner.results["chat"] = runner._run_chat_queries(
                    datasets_dir / "chat_queries.json"
                )
            runner.summary = runner._generate_summary()

        # 결과 출력 및 저장
        runner.print_summary()
        runner.save_results()

    elif args.stage == "langchain":
        print(f"\n⚠️ LangChain 평가는 아직 구현되지 않았습니다.")
        print(f"   LangChain 리팩토링 완료 후 사용 가능합니다.")

    elif args.stage == "finetuned":
        print(f"\n⚠️ Fine-tuned 평가는 아직 구현되지 않았습니다.")
        print(f"   Fine-tuning 완료 후 사용 가능합니다.")

    print(f"\n{'='*60}")
    print(f"✅ 평가 완료")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
