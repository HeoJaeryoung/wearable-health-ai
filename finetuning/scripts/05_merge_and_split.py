"""
LLM Fine-tuning 학습 데이터 통합 및 분할 스크립트 v2

4개 카테고리 통합:
- 건강 데이터 해석: 400건
- 운동 분석: 300건
- 코칭 챗봇: 500건
- 판단 패턴: 300건
= 총 1,500건

분할: Train 80% (1,200건) / Valid 10% (150건) / Test 10% (150건)
"""

import json
import random
import os
from datetime import datetime
from pathlib import Path


def load_jsonl(filepath: str) -> list:
    """JSONL 파일 로드"""
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line.strip()))
    return data


def save_jsonl(data: list, filepath: str):
    """JSONL 형식으로 저장"""
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def validate_data(data: list) -> dict:
    """데이터 유효성 검증"""
    stats = {"total": len(data), "valid": 0, "invalid": 0, "errors": []}

    for i, item in enumerate(data):
        try:
            # 필수 필드 확인
            assert "messages" in item, "messages 필드 없음"
            assert len(item["messages"]) >= 2, "messages 길이 부족"

            # 역할 확인
            roles = [m.get("role") for m in item["messages"]]
            assert "system" in roles, "system 역할 없음"
            assert "user" in roles, "user 역할 없음"
            assert "assistant" in roles, "assistant 역할 없음"

            # 내용 확인
            for msg in item["messages"]:
                assert msg.get("content"), "빈 content"

            stats["valid"] += 1

        except AssertionError as e:
            stats["invalid"] += 1
            stats["errors"].append(f"[{i}] {str(e)}")

    return stats


def merge_and_split(
    train_ratio: float = 0.8, valid_ratio: float = 0.1, test_ratio: float = 0.1
):
    """데이터 통합 및 분할 (Train/Valid/Test)"""

    print("=" * 60)
    print("🚀 LLM Fine-tuning 데이터 통합 v2")
    print("=" * 60)

    # 비율 검증
    assert (
        abs(train_ratio + valid_ratio + test_ratio - 1.0) < 0.001
    ), "비율 합이 1.0이어야 합니다"

    data_dir = Path(__file__).parent.parent / "data"

    # 파일 목록
    files = {
        "건강 분석": "health_interpretation_data_v2.jsonl",
        "운동 분석": "exercise_analysis_data_v2.jsonl",
        "코칭 챗봇": "coaching_chat_data_v2.jsonl",
        "판단 패턴": "decision_pattern_data_v2.jsonl",
    }

    all_data = []
    category_counts = {}

    print("\n📂 파일 로드 중...")
    for category, filename in files.items():
        filepath = data_dir / filename
        if filepath.exists():
            data = load_jsonl(filepath)
            category_counts[category] = len(data)
            all_data.extend(data)
            print(f"   ✅ {category}: {len(data)}건")
        else:
            print(f"   ❌ {category}: 파일 없음 ({filename})")
            category_counts[category] = 0

    print(f"\n📊 총 데이터: {len(all_data)}건")

    # 유효성 검증
    print("\n🔍 데이터 유효성 검증 중...")
    validation = validate_data(all_data)
    print(f"   - 유효: {validation['valid']}건")
    print(f"   - 무효: {validation['invalid']}건")

    if validation["invalid"] > 0:
        print(f"   ⚠️ 오류 샘플: {validation['errors'][:3]}")

    # 섞기
    random.seed(42)
    random.shuffle(all_data)

    # 분할 (Train / Valid / Test)
    total = len(all_data)
    train_end = int(total * train_ratio)
    valid_end = int(total * (train_ratio + valid_ratio))

    train_data = all_data[:train_end]
    valid_data = all_data[train_end:valid_end]
    test_data = all_data[valid_end:]

    print(
        f"\n📂 데이터 분할 (Train {int(train_ratio*100)}% / Valid {int(valid_ratio*100)}% / Test {int(test_ratio*100)}%)"
    )
    print(f"   - Train: {len(train_data)}건 (학습용)")
    print(f"   - Valid: {len(valid_data)}건 (학습 중 검증)")
    print(f"   - Test:  {len(test_data)}건 (학습 후 모델 평가)")

    # 저장
    timestamp = datetime.now().strftime("%Y%m%d")

    train_file = data_dir / f"train_{timestamp}.jsonl"
    valid_file = data_dir / f"valid_{timestamp}.jsonl"
    test_file = data_dir / f"test_model_{timestamp}.jsonl"

    save_jsonl(train_data, train_file)
    save_jsonl(valid_data, valid_file)
    save_jsonl(test_data, test_file)

    print(f"\n💾 저장 완료:")
    print(f"   - {train_file.name} ({len(train_data)}건)")
    print(f"   - {valid_file.name} ({len(valid_data)}건)")
    print(f"   - {test_file.name} ({len(test_data)}건)")

    # 통계 저장
    stats = {
        "generated_at": datetime.now().isoformat(),
        "total_count": len(all_data),
        "train_count": len(train_data),
        "valid_count": len(valid_data),
        "test_count": len(test_data),
        "ratios": {"train": train_ratio, "valid": valid_ratio, "test": test_ratio},
        "categories": category_counts,
        "validation": {"valid": validation["valid"], "invalid": validation["invalid"]},
    }

    stats_file = data_dir / f"stats_{timestamp}.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"   - {stats_file.name} (통계)")

    return train_file, valid_file, test_file, stats


def print_sample(filepath: str, count: int = 2):
    """샘플 출력"""
    data = load_jsonl(filepath)

    print(f"\n📝 샘플 ({filepath}):")
    print("-" * 40)

    for i, item in enumerate(data[:count]):
        print(f"\n[샘플 {i+1}]")
        print(f"User: {item['messages'][1]['content'][:100]}...")
        print(f"Assistant: {item['messages'][2]['content'][:150]}...")


# ============================================================
# 메인 실행
# ============================================================

if __name__ == "__main__":
    train_file, valid_file, test_file, stats = merge_and_split(
        train_ratio=0.8, valid_ratio=0.1, test_ratio=0.1
    )

    print("\n" + "=" * 60)
    print("✅ 완료!")
    print("=" * 60)

    print("\n📊 카테고리별 분포:")
    for category, count in stats["categories"].items():
        ratio = count / stats["total_count"] * 100 if stats["total_count"] > 0 else 0
        print(f"   - {category}: {count}건 ({ratio:.1f}%)")

    print("\n📁 파일 용도:")
    print(f"   - Train ({train_file.name}): Azure Fine-tuning 학습")
    print(f"   - Valid ({valid_file.name}): Azure Fine-tuning 검증 (Loss 모니터링)")
    print(f"   - Test ({test_file.name}): 학습 후 모델 평가 (정답 비교)")

    print("\n⚙️ 권장 Fine-tuning 설정:")
    print("   - Base Model: Llama 3.1 8B Instruct")
    print("   - Epochs: 3")
    print("   - Batch Size: 4")
    print("   - Learning Rate: 2e-4")
    print("   - LoRA Rank: 16")

    print("\n📋 평가 체계:")
    print("   ┌─────────────────────────────────────────────┐")
    print("   │  1. 모델 평가 (test_model_*.jsonl)          │")
    print("   │     - Fine-tuned 모델의 학습 품질 측정      │")
    print("   │     - 정답(assistant)과 출력 비교           │")
    print("   │                                             │")
    print("   │  2. 서비스 평가 (evaluation/datasets/)      │")
    print("   │     - Baseline → LangChain → Fine-tuned    │")
    print("   │     - 3단계 출력 품질 비교                  │")
    print("   └─────────────────────────────────────────────┘")
