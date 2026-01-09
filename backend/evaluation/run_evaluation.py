"""
3단계 평가 실행 스크립트 v2

사용법:
    # 1단계: Baseline 평가
    python run_evaluation.py baseline

    # 2단계: LangChain 평가
    python run_evaluation.py langchain

    # 3단계: Fine-tuned 평가
    python run_evaluation.py finetuned

    # 전체 실행 (1, 2, 3단계 순차)
    python run_evaluation.py all

    # 결과 비교
    python run_evaluation.py compare
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def run_baseline():
    """1단계: Baseline 평가"""
    print("\n" + "=" * 60)
    print("🚀 1단계: Baseline 평가 시작")
    print("=" * 60)

    from evaluation.runners.baseline_runner import BaselineRunner

    runner = BaselineRunner()
    runner.run_all()
    runner.print_summary()
    result_path = runner.save_results()

    return result_path


def run_langchain():
    """2단계: LangChain 평가"""
    print("\n" + "=" * 60)
    print("🚀 2단계: LangChain 평가 시작")
    print("=" * 60)

    from evaluation.runners.langchain_runner import LangchainRunner

    runner = LangchainRunner()
    runner.run_all()
    runner.print_summary()
    result_path = runner.save_results()

    return result_path


def run_finetuned():
    """3단계: Fine-tuned 평가"""
    print("\n" + "=" * 60)
    print("🚀 3단계: Fine-tuned 평가 시작")
    print("=" * 60)

    from evaluation.runners.finetuned_runner import FinetunedRunner

    runner = FinetunedRunner()
    runner.run_all()
    runner.print_summary()
    result_path = runner.save_results()

    return result_path


def compare_results():
    """결과 비교"""
    print("\n" + "=" * 60)
    print("📊 3단계 평가 결과 비교")
    print("=" * 60)

    results_dir = Path("evaluation/results")

    # 각 단계별 최신 결과 파일 찾기
    stages = ["baseline", "langchain", "finetuned"]
    latest_results = {}

    for stage in stages:
        stage_dir = results_dir / stage
        if stage_dir.exists():
            result_files = list(stage_dir.glob("results_*.json"))
            if result_files:
                latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
                with open(latest_file, "r", encoding="utf-8") as f:
                    latest_results[stage] = json.load(f)
                print(f"✅ {stage}: {latest_file.name}")
            else:
                print(f"⚠️ {stage}: 결과 파일 없음")
        else:
            print(f"⚠️ {stage}: 디렉토리 없음")

    if len(latest_results) < 2:
        print("\n비교할 결과가 부족합니다. 최소 2개 단계 평가가 필요합니다.")
        return

    # 비교 테이블 출력
    print("\n" + "-" * 80)
    print("📈 서비스별 정확도 비교")
    print("-" * 80)
    print(
        f"{'서비스':<12} {'Baseline':<12} {'LangChain':<12} {'Fine-tuned':<12} {'개선율':<12}"
    )
    print("-" * 80)

    services = ["health", "exercise", "chat"]
    service_names = {"health": "건강 분석", "exercise": "운동 분석", "chat": "챗봇"}

    for service in services:
        row = [service_names.get(service, service)]

        baseline_acc = (
            latest_results.get("baseline", {})
            .get("summary", {})
            .get("by_service", {})
            .get(service, {})
            .get("avg_accuracy", 0)
        )
        langchain_acc = (
            latest_results.get("langchain", {})
            .get("summary", {})
            .get("by_service", {})
            .get(service, {})
            .get("avg_accuracy", 0)
        )
        finetuned_acc = (
            latest_results.get("finetuned", {})
            .get("summary", {})
            .get("by_service", {})
            .get(service, {})
            .get("avg_accuracy", 0)
        )

        row.append(f"{baseline_acc:.1f}%" if baseline_acc else "-")
        row.append(f"{langchain_acc:.1f}%" if langchain_acc else "-")
        row.append(f"{finetuned_acc:.1f}%" if finetuned_acc else "-")

        # 개선율 계산 (Baseline → Fine-tuned)
        if baseline_acc and finetuned_acc:
            improvement = finetuned_acc - baseline_acc
            row.append(
                f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
            )
        else:
            row.append("-")

        print(f"{row[0]:<12} {row[1]:<12} {row[2]:<12} {row[3]:<12} {row[4]:<12}")

    # v2 핵심 지표 비교
    print("\n" + "-" * 80)
    print("🎯 v2 핵심 지표 비교 (Fine-tuning 효과)")
    print("-" * 80)
    print(f"{'지표':<20} {'Baseline':<12} {'LangChain':<12} {'Fine-tuned':<12}")
    print("-" * 80)

    v2_metrics = [
        ("응답 구조 점수", "avg_structure_score"),
        ("전문 인용 점수", "avg_citation_score"),
        ("길이 적절성", "avg_length_score"),
    ]

    for metric_name, metric_key in v2_metrics:
        row = [metric_name]

        for stage in stages:
            # 전체 평균 또는 건강 분석 기준
            value = (
                latest_results.get(stage, {})
                .get("summary", {})
                .get("overall", {})
                .get(metric_key, 0)
            )
            if not value:
                value = (
                    latest_results.get(stage, {})
                    .get("summary", {})
                    .get("by_service", {})
                    .get("health", {})
                    .get(metric_key, 0)
                )
            row.append(f"{value:.1f}%" if value else "-")

        print(f"{row[0]:<20} {row[1]:<12} {row[2]:<12} {row[3]:<12}")

    # 건강 분석 등급 정확도
    print("\n건강 분석 등급 정확도:")
    for stage in stages:
        grade_acc = (
            latest_results.get(stage, {})
            .get("summary", {})
            .get("by_service", {})
            .get("health", {})
            .get("grade_accuracy", 0)
        )
        print(f"   {stage}: {grade_acc:.1f}%" if grade_acc else f"   {stage}: -")

    # 운동 분석 카보넨 인용율
    print("\n운동 분석 카보넨 인용율:")
    for stage in stages:
        karv_rate = (
            latest_results.get(stage, {})
            .get("summary", {})
            .get("by_service", {})
            .get("exercise", {})
            .get("karvonen_citation_rate", 0)
        )
        print(f"   {stage}: {karv_rate:.1f}%" if karv_rate else f"   {stage}: -")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "baseline":
        run_baseline()
    elif command == "langchain":
        run_langchain()
    elif command == "finetuned":
        run_finetuned()
    elif command == "all":
        print("\n🚀 3단계 전체 평가 시작")
        print("=" * 60)
        run_baseline()
        run_langchain()
        run_finetuned()
        compare_results()
    elif command == "compare":
        compare_results()
    else:
        print(f"알 수 없는 명령어: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
