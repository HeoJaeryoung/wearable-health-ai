# 실행: python -m evaluation.analysis.compare_results

import json
from pathlib import Path

RESULT_FILES = {
    "baseline": "evaluation/results/baseline/latest.json",
    "langchain": "evaluation/results/langchain/latest.json",
    # "finetuned": "evaluation/results/finetuned/latest.json",
}

METRICS = [
    "avg_accuracy",
    "avg_structure_score",
    "avg_citation_strict_score",
    "avg_concept_score",
    "avg_length_score",
]


def load_summary(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["summary"]["overall"]


def generate_comparison():
    summaries = {}

    for name, path in RESULT_FILES.items():
        if Path(path).exists():
            summaries[name] = load_summary(path)
        else:
            print(f"⚠️ {name} 결과 없음 → 비교에서 제외")

    return build_comparison_table(summaries)


def print_table(table, summaries):
    print("\n📊 모델 성능 비교표")
    print("=" * 60)

    stages = list(summaries.keys())  # ['baseline', 'langchain']

    # 헤더 동적 생성
    header = f"{'Metric':30} | " + " | ".join(f"{s.capitalize():>10}" for s in stages)
    print(header)
    print("-" * len(header))

    for metric, values in table.items():
        row = f"{metric:30} | "
        row += " | ".join(f"{values.get(s, 0):10.1f}" for s in stages)
        print(row)


def build_comparison_table(summaries: dict) -> dict:
    """
    summaries = {
        "baseline": {...overall summary...},
        "langchain": {...overall summary...}
    }
    """
    metrics = [
        ("avg_accuracy", "정확도 (%)"),
        ("avg_time", "응답 시간 (초)"),
        ("avg_structure_score", "구조 점수 (%)"),
        ("avg_citation_strict_score", "논문 인용율 (%)"),
        ("avg_concept_score", "개념 적용율 (%)"),
    ]

    table = {}

    for key, label in metrics:
        table[label] = {
            name: summary.get(key, 0) for name, summary in summaries.items()
        }

    return table


if __name__ == "__main__":
    summaries = {}
    for name, path in RESULT_FILES.items():
        if Path(path).exists():
            summaries[name] = load_summary(path)
        else:
            print(f"⚠️ {name} 결과 없음 → 비교에서 제외")

    table = build_comparison_table(summaries)
    print_table(table, summaries)

    # JSON 저장
    out_path = Path("evaluation/results/comparison_summary.json")
    out_path.parent.mkdir(exist_ok=True, parents=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=2)

    print(f"\n💾 비교 결과 저장: {out_path}")
