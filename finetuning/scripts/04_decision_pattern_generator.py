"""
LLM Fine-tuning 학습 데이터 생성 스크립트 v2
카테고리 4: 판단 패턴 (300건) - 신규

목적:
- 명시적인 "입력 → 판단 근거 → 결론" 패턴 학습
- 전문 기준 인용을 자연스럽게 학습
- 복합 조건 판단 패턴 학습
"""

import json
import random
from pathlib import Path

# ============================================================
# 시스템 프롬프트
# ============================================================

SYSTEM_PROMPT = """당신은 스포츠의학 전문가입니다. 생체 데이터를 보고 판단 근거와 함께 명확한 권장사항을 제시합니다.

적용 기준:
- ACSM Guidelines
- Buchheit (2014): RHR +10bpm 이상 → 급성 피로
- Milewski (2014): 8시간 미만 수면 → 부상 위험 1.7배

응답 형식:
1. 상태 판정 (이모지 + 등급)
2. 판단 근거 (번호 리스트)
3. 권장사항 (1문장)"""


# ============================================================
# 판단 패턴 정의
# ============================================================

# 단일 조건 판단 패턴
SINGLE_PATTERNS = {
    # 수면 패턴 (Milewski)
    "sleep_danger": {
        "condition": lambda d: d["sleep_hr"] < 5,
        "input_template": "sleep_hr: {sleep_hr}시간",
        "response_template": """🚨 **경고 상태**

**판단 근거:**
1. 수면 {sleep_hr}시간 → 권장량(7-9시간) 대비 심각하게 부족
2. 8시간 미만 수면 시 부상 위험 1.7배 증가

💡 **권장:** 오늘은 운동을 쉬고 일찍 주무세요.

📚 Milewski et al. (2014)""",
    },
    "sleep_poor": {
        "condition": lambda d: 5 <= d["sleep_hr"] < 6,
        "input_template": "sleep_hr: {sleep_hr}시간",
        "response_template": """⚠️ **주의 상태**

**판단 근거:**
1. 수면 {sleep_hr}시간 → 권장량(7-9시간) 미달
2. 수면 부족 시 회복력 저하 및 부상 위험 증가

💡 **권장:** 저강도 운동만 하세요. 고강도는 피하세요.

📚 Milewski et al. (2014)""",
    },
    "sleep_fair": {
        "condition": lambda d: 6 <= d["sleep_hr"] < 7,
        "input_template": "sleep_hr: {sleep_hr}시간",
        "response_template": """⚠️ **보통 상태**

**판단 근거:**
1. 수면 {sleep_hr}시간 → 권장량에 약간 미달
2. 가벼운 피로 가능성

💡 **권장:** 중강도까지 운동 가능. 컨디션 살피며 진행하세요.""",
    },
    "sleep_good": {
        "condition": lambda d: d["sleep_hr"] >= 7,
        "input_template": "sleep_hr: {sleep_hr}시간",
        "response_template": """✅ **양호 상태**

**판단 근거:**
1. 수면 {sleep_hr}시간 → 권장량(7-9시간) 충족
2. 충분한 회복 상태

💡 **권장:** 계획대로 운동하세요!""",
    },
    # RHR 패턴 (Buchheit)
    "rhr_danger": {
        "condition": lambda d: d["rhr_change"] >= 15,
        "input_template": "resting_heart_rate: {rhr}bpm (평소 {usual_rhr}bpm, +{rhr_change}bpm)",
        "response_template": """🚨 **경고 상태**

**판단 근거:**
1. 안정시 심박수 +{rhr_change}bpm → 정상 범위(±5bpm) 크게 초과
2. +15bpm 이상은 과훈련 또는 질병 신호

💡 **권장:** 반드시 휴식하세요. 며칠 후에도 지속되면 의료 상담을 권합니다.

📚 Buchheit (2014)""",
    },
    "rhr_fatigue": {
        "condition": lambda d: 10 <= d["rhr_change"] < 15,
        "input_template": "resting_heart_rate: {rhr}bpm (평소 {usual_rhr}bpm, +{rhr_change}bpm)",
        "response_template": """🚨 **피로 신호**

**판단 근거:**
1. 안정시 심박수 +{rhr_change}bpm → 급성 피로 지표
2. +10bpm 이상 상승은 회복 부족 신호

💡 **권장:** 오늘은 휴식하거나 저강도 운동만 하세요.

📚 Buchheit (2014)""",
    },
    "rhr_mild": {
        "condition": lambda d: 5 <= d["rhr_change"] < 10,
        "input_template": "resting_heart_rate: {rhr}bpm (평소 {usual_rhr}bpm, +{rhr_change}bpm)",
        "response_template": """⚠️ **경미한 피로**

**판단 근거:**
1. 안정시 심박수 +{rhr_change}bpm → 정상 범위 약간 초과
2. 가벼운 피로 또는 스트레스 가능성

💡 **권장:** 중강도까지 운동 가능. 몸 상태 살피며 진행하세요.""",
    },
    "rhr_normal": {
        "condition": lambda d: d["rhr_change"] < 5,
        "input_template": "resting_heart_rate: {rhr}bpm (평소 {usual_rhr}bpm, +{rhr_change}bpm)",
        "response_template": """✅ **정상 상태**

**판단 근거:**
1. 안정시 심박수 +{rhr_change}bpm → 정상 변동 범위(±5bpm)
2. 충분히 회복된 상태

💡 **권장:** 계획대로 운동하세요!""",
    },
}

# 복합 조건 판단 패턴
COMPOUND_PATTERNS = {
    "both_danger": {
        "condition": lambda d: d["sleep_hr"] < 5 and d["rhr_change"] >= 10,
        "input_template": "sleep_hr: {sleep_hr}시간, resting_heart_rate: {rhr}bpm (평소 대비 +{rhr_change}bpm)",
        "response_template": """🚨 **위험 상태**

**판단 근거:**
1. 수면 {sleep_hr}시간 → 심각한 부족, 부상 위험 1.7배 (Milewski, 2014)
2. RHR +{rhr_change}bpm → 급성 피로/과훈련 신호 (Buchheit, 2014)
3. 두 지표 모두 경고 수준

💡 **권장:** 오늘은 반드시 휴식하세요. 운동은 금물입니다.""",
    },
    "sleep_bad_rhr_mild": {
        "condition": lambda d: d["sleep_hr"] < 6 and 5 <= d["rhr_change"] < 10,
        "input_template": "sleep_hr: {sleep_hr}시간, resting_heart_rate: {rhr}bpm (평소 대비 +{rhr_change}bpm)",
        "response_template": """⚠️ **주의 상태**

**판단 근거:**
1. 수면 {sleep_hr}시간 → 부족 (권장 7-9시간)
2. RHR +{rhr_change}bpm → 경미한 피로
3. 복합적 피로 누적 가능성

💡 **권장:** 저강도 운동만 하세요. 오늘 밤 충분히 주무세요.""",
    },
    "sleep_ok_rhr_high": {
        "condition": lambda d: d["sleep_hr"] >= 7 and d["rhr_change"] >= 10,
        "input_template": "sleep_hr: {sleep_hr}시간, resting_heart_rate: {rhr}bpm (평소 대비 +{rhr_change}bpm)",
        "response_template": """⚠️ **주의 상태**

**판단 근거:**
1. 수면 {sleep_hr}시간 → 충분 ✅
2. RHR +{rhr_change}bpm → 피로 신호 🚨 (Buchheit, 2014)
3. 수면 외 다른 요인(스트레스, 질병 초기)으로 피로 가능성

💡 **권장:** 수면은 충분하지만 심박수가 높아요. 저강도 운동만 권합니다.""",
    },
    "both_good": {
        "condition": lambda d: d["sleep_hr"] >= 7 and d["rhr_change"] < 5,
        "input_template": "sleep_hr: {sleep_hr}시간, resting_heart_rate: {rhr}bpm (평소 대비 +{rhr_change}bpm)",
        "response_template": """✅ **최적 상태**

**판단 근거:**
1. 수면 {sleep_hr}시간 → 권장량 충족 ✅
2. RHR +{rhr_change}bpm → 정상 범위 ✅
3. 충분히 회복된 상태

💡 **권장:** 고강도 포함 모든 운동 가능합니다!""",
    },
}

# 운동 강도 판단 패턴
INTENSITY_PATTERNS = {
    "recommend_rest": {
        "condition": lambda d: d["condition_score"] < 40,
        "input_template": "컨디션 점수: {condition_score}/100",
        "response_template": """🚨 **휴식 권장**

**판단 근거:**
1. 컨디션 점수 {condition_score}/100 → F등급 (40점 미만)
2. 피로 누적 또는 회복 부족 상태

💡 **권장:** 오늘은 운동을 쉬세요. 가벼운 스트레칭 정도만 괜찮아요.""",
    },
    "recommend_low": {
        "condition": lambda d: 40 <= d["condition_score"] < 55,
        "input_template": "컨디션 점수: {condition_score}/100",
        "response_template": """⚠️ **저강도 권장**

**판단 근거:**
1. 컨디션 점수 {condition_score}/100 → D등급
2. 피로 상태이나 가벼운 활동은 가능

💡 **권장:** 걷기, 스트레칭 등 저강도 운동만 하세요.""",
    },
    "recommend_moderate": {
        "condition": lambda d: 55 <= d["condition_score"] < 70,
        "input_template": "컨디션 점수: {condition_score}/100",
        "response_template": """⚠️ **중강도 권장**

**판단 근거:**
1. 컨디션 점수 {condition_score}/100 → C등급
2. 보통 상태, 과도한 운동은 피해야 함

💡 **권장:** 중강도까지 운동 가능. 고강도는 피하세요.""",
    },
    "recommend_high": {
        "condition": lambda d: d["condition_score"] >= 70,
        "input_template": "컨디션 점수: {condition_score}/100",
        "response_template": """✅ **고강도 가능**

**판단 근거:**
1. 컨디션 점수 {condition_score}/100 → {grade}등급
2. 충분히 회복된 상태

💡 **권장:** 계획대로 운동하세요! 고강도도 가능합니다.""",
    },
}


# ============================================================
# 데이터 생성 함수
# ============================================================


def generate_single_pattern_data(count: int) -> list:
    """단일 조건 판단 패턴 데이터 생성"""
    data = []

    for _ in range(count):
        # 랜덤 데이터 생성
        usual_rhr = random.randint(58, 70)
        rhr_change = random.randint(0, 20)

        raw = {
            "sleep_hr": round(random.uniform(3.5, 9.0), 1),
            "rhr": usual_rhr + rhr_change,
            "usual_rhr": usual_rhr,
            "rhr_change": rhr_change,
        }

        # 조건에 맞는 패턴 선택
        for pattern_name, pattern in SINGLE_PATTERNS.items():
            if pattern["condition"](raw):
                user_input = pattern["input_template"].format(**raw)
                response = pattern["response_template"].format(**raw)

                data.append(
                    {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_input},
                            {"role": "assistant", "content": response},
                        ]
                    }
                )
                break

    return data


def generate_compound_pattern_data(count: int) -> list:
    """복합 조건 판단 패턴 데이터 생성"""
    data = []
    patterns_list = list(COMPOUND_PATTERNS.items())

    for i in range(count):
        pattern_name, pattern = patterns_list[i % len(patterns_list)]

        # 패턴에 맞는 데이터 생성
        usual_rhr = random.randint(58, 70)

        if pattern_name == "both_danger":
            sleep = round(random.uniform(3.5, 4.9), 1)
            rhr_change = random.randint(10, 18)
        elif pattern_name == "sleep_bad_rhr_mild":
            sleep = round(random.uniform(4.5, 5.9), 1)
            rhr_change = random.randint(5, 9)
        elif pattern_name == "sleep_ok_rhr_high":
            sleep = round(random.uniform(7.0, 8.5), 1)
            rhr_change = random.randint(10, 15)
        else:  # both_good
            sleep = round(random.uniform(7.0, 8.5), 1)
            rhr_change = random.randint(0, 4)

        raw = {
            "sleep_hr": sleep,
            "rhr": usual_rhr + rhr_change,
            "usual_rhr": usual_rhr,
            "rhr_change": rhr_change,
        }

        user_input = pattern["input_template"].format(**raw)
        response = pattern["response_template"].format(**raw)

        data.append(
            {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": response},
                ]
            }
        )

    return data


def generate_intensity_pattern_data(count: int) -> list:
    """운동 강도 판단 패턴 데이터 생성"""
    data = []

    for _ in range(count):
        score = random.randint(20, 95)

        # 6등급 기준 (실제 서비스 health_interpreter.py 기준)
        if score >= 80:
            grade = "A"
        elif score >= 70:
            grade = "B"
        elif score >= 55:
            grade = "C+"
        elif score >= 45:
            grade = "C"
        elif score >= 35:
            grade = "D"
        else:
            grade = "F"

        raw = {"condition_score": score, "grade": grade}

        for pattern_name, pattern in INTENSITY_PATTERNS.items():
            if pattern["condition"](raw):
                user_input = pattern["input_template"].format(**raw)
                response = pattern["response_template"].format(**raw)

                data.append(
                    {
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_input},
                            {"role": "assistant", "content": response},
                        ]
                    }
                )
                break

    return data


def generate_training_data(total_count: int = 300) -> list:
    """학습 데이터 생성"""

    # 패턴별 분배
    single_count = int(total_count * 0.40)  # 120건
    compound_count = int(total_count * 0.35)  # 105건
    intensity_count = int(total_count * 0.25)  # 75건

    training_data = []

    training_data.extend(generate_single_pattern_data(single_count))
    training_data.extend(generate_compound_pattern_data(compound_count))
    training_data.extend(generate_intensity_pattern_data(intensity_count))

    # 섞기
    random.seed(42)
    random.shuffle(training_data)

    return training_data


def save_jsonl(data: list, filepath: str):
    """JSONL 형식으로 저장"""
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ============================================================
# 메인 실행
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧠 판단 패턴 학습 데이터 생성 (신규)")
    print("=" * 60)
    print("📋 목적:")
    print("   - 명시적 '입력 → 판단 근거 → 결론' 패턴")
    print("   - 전문 기준 인용 자연스럽게 학습")
    print("   - 복합 조건 판단 패턴")
    print()

    training_data = generate_training_data(300)

    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "decision_pattern_data_v2.jsonl"
    save_jsonl(training_data, output_file)

    print(f"✅ 생성 완료: {len(training_data)}건")
    print(f"📁 저장 위치: {output_file}")

    print("\n📊 패턴별 분포:")
    print("   - 단일 조건 패턴: 120건 (40%)")
    print("   - 복합 조건 패턴: 105건 (35%)")
    print("   - 강도 판단 패턴: 75건 (25%)")

    # 샘플 출력
    print("\n" + "=" * 60)
    print("📝 샘플 응답:")
    print("=" * 60)
    sample = training_data[0]
    print(f"\n[User]\n{sample['messages'][1]['content']}")
    print(f"\n[Assistant]\n{sample['messages'][2]['content']}")
