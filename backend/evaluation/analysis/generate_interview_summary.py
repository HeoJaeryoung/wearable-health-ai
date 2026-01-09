# 실행: python -m evaluation.analysis.generate_interview_summary

import json
from pathlib import Path

COMPARISON_PATH = "evaluation/results/comparison_summary.json"


def generate_interview_summary(data: dict) -> str:
    """
    comparison_summary.json 기반 면접용 3줄 요약 생성
    """

    baseline = data.get("정확도 (%)", {}).get("baseline", 0)
    langchain = data.get("정확도 (%)", {}).get("langchain", 0)

    structure_base = data.get("구조 점수 (%)", {}).get("baseline", 0)
    structure_lc = data.get("구조 점수 (%)", {}).get("langchain", 0)

    citation = data.get("논문 인용율 (%)", {}).get("baseline", 0)
    concept = data.get("개념 적용율 (%)", {}).get("baseline", 0)

    line1 = (
        f"Baseline 대비 LangChain 적용 후 정확도가 "
        f"{baseline:.1f}% → {langchain:.1f}%로 소폭 개선되었습니다."
    )

    line2 = (
        "현재 LangChain은 챗봇 중심으로 구조화되어 있어 "
        f"응답 구조 점수는 {structure_base:.1f}% → {structure_lc:.1f}%로 제한적인 상태입니다."
    )

    line3 = (
        f"논문 인용율({citation:.1f}%)과 개념 적용율({concept:.1f}%)은 유지되어 "
        "Fine-tuning을 통해 구조 일관성과 전문성 강화를 목표로 하고 있습니다."
    )

    return "\n".join([line1, line2, line3])


if __name__ == "__main__":
    path = Path(COMPARISON_PATH)

    if not path.exists():
        raise FileNotFoundError(f"비교 결과 파일 없음: {path}")

    with open(path, "r", encoding="utf-8") as f:
        comparison_data = json.load(f)

    summary = generate_interview_summary(comparison_data)

    print("\n🎤 면접용 3줄 요약\n" + "=" * 40)
    print(summary)

    # 저장
    out_path = Path("evaluation/results/interview_summary.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(summary)

    print(f"\n💾 요약 저장: {out_path}")
