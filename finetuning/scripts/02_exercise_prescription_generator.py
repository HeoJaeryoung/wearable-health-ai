"""
LLM Fine-tuning 학습 데이터 생성 스크립트 v2
카테고리 2: 운동 분석 (300건)

핵심 변경사항:
- 응답 길이 ~600자 → ~250자로 축소
- 카보넨 공식 판단 근거 명시
- 컨디션 기반 운동 강도 조절 패턴
"""

import json
import random
from pathlib import Path

# ============================================================
# 시스템 프롬프트
# ============================================================

SYSTEM_PROMPT = """당신은 ACSM 인증 운동처방 전문가입니다. 사용자의 건강 상태를 기반으로 운동 루틴을 분석하고 간결한 코멘트를 제공합니다.

적용 기준:
- ACSM Guidelines for Exercise Testing and Prescription
- 카보넨 공식: 목표심박수 = (최대심박수 - 안정시심박수) × 강도% + 안정시심박수
- 최대심박수 = 220 - 나이

응답 형식:
1. 루틴 적합도 평가 (컨디션 기반)
2. 목표 심박수 범위
3. 핵심 코멘트 (1-2문장)
4. 주의사항 (해당 시)"""


# ============================================================
# 운동 강도 기준
# ============================================================

INTENSITY_ZONES = {
    "low": {"range": (0.40, 0.55), "label": "저강도", "emoji": "🚶"},
    "low_moderate": {"range": (0.45, 0.60), "label": "저-중강도", "emoji": "🚶‍♂️"},
    "moderate": {"range": (0.55, 0.70), "label": "중강도", "emoji": "🏃"},
    "moderate_high": {"range": (0.65, 0.80), "label": "중-고강도", "emoji": "🏃‍♂️"},
    "high": {"range": (0.75, 0.90), "label": "고강도", "emoji": "🔥"},
}

# 컨디션 → 권장 강도 매핑 (6등급)
CONDITION_TO_INTENSITY = {
    "optimal": "high",
    "good": "moderate_high",
    "moderate_plus": "moderate",
    "moderate": "moderate",
    "caution": "low_moderate",
    "warning": "low",
}

# 시드 운동 목록 (16종) - 실제 서비스 데이터 기반
# category: 1=상체, 2=코어, 3=하체, 4=전신
# difficulty: 3=중간, 4=어려움, 5=매우 어려움
# met: 대사당량 (운동 강도)
SEED_EXERCISES_RAW = [
    {
        "name": "standing side crunch",
        "name_kr": "스탠딩 사이드 크런치",
        "category": [2, 3],
        "difficulty": 3,
        "met": 4.0,
    },
    {
        "name": "standing knee up",
        "name_kr": "스탠딩 니업",
        "category": [1, 3],
        "difficulty": 3,
        "met": 3.8,
    },
    {
        "name": "burpee test",
        "name_kr": "버피 테스트",
        "category": [4],
        "difficulty": 5,
        "met": 8.0,
    },
    {
        "name": "step forward dynamic lunge",
        "name_kr": "스텝 포워드 런지",
        "category": [3],
        "difficulty": 4,
        "met": 4.0,
    },
    {
        "name": "side lunge",
        "name_kr": "사이드 런지",
        "category": [3],
        "difficulty": 5,
        "met": 5.0,
    },
    {
        "name": "cross lunge",
        "name_kr": "크로스 런지",
        "category": [3, 2],
        "difficulty": 4,
        "met": 3.8,
    },
    {
        "name": "good morning exercise",
        "name_kr": "굿모닝 엑서사이즈",
        "category": [3],
        "difficulty": 5,
        "met": 5.0,
    },
    {
        "name": "lying leg raise",
        "name_kr": "라잉 레그 레이즈",
        "category": [3, 2],
        "difficulty": 4,
        "met": 4.0,
    },
    {
        "name": "crunch",
        "name_kr": "크런치",
        "category": [2],
        "difficulty": 4,
        "met": 4.5,
    },
    {
        "name": "bicycle crunch",
        "name_kr": "바이시클 크런치",
        "category": [3, 2],
        "difficulty": 5,
        "met": 5.0,
    },
    {
        "name": "scissor cross",
        "name_kr": "시저 크로스",
        "category": [2, 3],
        "difficulty": 4,
        "met": 4.5,
    },
    {
        "name": "hip thrust",
        "name_kr": "힙 쓰러스트",
        "category": [3, 2],
        "difficulty": 3,
        "met": 3.5,
    },
    {
        "name": "plank",
        "name_kr": "플랭크",
        "category": [4],
        "difficulty": 5,
        "met": 8.0,
    },
    {
        "name": "push up",
        "name_kr": "푸시업",
        "category": [1, 2],
        "difficulty": 4,
        "met": 6.0,
    },
    {
        "name": "knee push up",
        "name_kr": "니 푸시업",
        "category": [1, 2],
        "difficulty": 3,
        "met": 5.0,
    },
    {
        "name": "Y-exercise",
        "name_kr": "Y 엑서사이즈",
        "category": [1, 2],
        "difficulty": 3,
        "met": 4.5,
    },
]

# 난이도별 운동 분류
SEED_EXERCISES = {
    "low": [e for e in SEED_EXERCISES_RAW if e["difficulty"] == 3],  # 난이도 3: 저강도
    "moderate": [
        e for e in SEED_EXERCISES_RAW if e["difficulty"] == 4
    ],  # 난이도 4: 중강도
    "high": [e for e in SEED_EXERCISES_RAW if e["difficulty"] == 5],  # 난이도 5: 고강도
}


# ============================================================
# 카보넨 공식 계산
# ============================================================


def calculate_karvonen(age: int, resting_hr: int, intensity_key: str) -> dict:
    """카보넨 공식으로 목표 심박수 계산"""
    max_hr = 220 - age
    hr_reserve = max_hr - resting_hr

    intensity = INTENSITY_ZONES[intensity_key]
    low_pct, high_pct = intensity["range"]

    target_low = round(hr_reserve * low_pct + resting_hr)
    target_high = round(hr_reserve * high_pct + resting_hr)

    return {
        "max_hr": max_hr,
        "hr_reserve": hr_reserve,
        "target_low": target_low,
        "target_high": target_high,
        "intensity_label": intensity["label"],
        "intensity_emoji": intensity["emoji"],
    }


# ============================================================
# 컨디션 평가 (건강 분석과 동일 로직)
# ============================================================


def assess_condition(data: dict) -> dict:
    """컨디션 점수 및 등급 계산"""
    rhr_change = data["resting_heart_rate"] - data["usual_resting_heart_rate"]
    sleep = data["sleep_hr"]
    steps = data["steps"]

    # 간단한 점수 계산
    score = 100

    # RHR 변화 감점
    if rhr_change >= 15:
        score -= 35
    elif rhr_change >= 10:
        score -= 25
    elif rhr_change >= 5:
        score -= 10

    # 수면 부족 감점
    if sleep < 5:
        score -= 30
    elif sleep < 6:
        score -= 20
    elif sleep < 7:
        score -= 10

    # 활동량 부족 감점
    if steps < 3000:
        score -= 15
    elif steps < 5000:
        score -= 10

    score = max(0, min(100, score))

    # 등급 결정 (실제 서비스 health_interpreter.py 기준 - 6등급)
    if score >= 80:
        return {
            "score": score,
            "grade": "A",
            "label": "매우 우수",
            "scenario": "optimal",
        }
    elif score >= 70:
        return {"score": score, "grade": "B", "label": "우수", "scenario": "good"}
    elif score >= 55:
        return {
            "score": score,
            "grade": "C+",
            "label": "보통 이상",
            "scenario": "moderate_plus",
        }
    elif score >= 45:
        return {"score": score, "grade": "C", "label": "보통", "scenario": "moderate"}
    elif score >= 35:
        return {
            "score": score,
            "grade": "D",
            "label": "개선 필요",
            "scenario": "caution",
        }
    else:
        return {
            "score": score,
            "grade": "F",
            "label": "주의 필요",
            "scenario": "warning",
        }


# ============================================================
# 루틴 생성
# ============================================================


def generate_routine(condition_scenario: str, duration_min: int) -> list:
    """컨디션에 맞는 운동 루틴 생성 (실제 시드 운동 16종 사용)"""
    routine = []

    # 컨디션별 적합 난이도 매핑 (6등급)
    scenario_to_difficulty = {
        "optimal": ["low", "moderate", "high"],  # 모든 난이도 가능
        "good": ["low", "moderate", "high"],  # 모든 난이도 가능
        "moderate_plus": ["low", "moderate"],  # 중강도까지
        "moderate": ["low", "moderate"],  # 중강도까지
        "caution": ["low"],  # 저강도만
        "warning": ["low"],  # 저강도만
    }

    allowed_difficulties = scenario_to_difficulty.get(
        condition_scenario, ["low", "moderate"]
    )

    # 허용된 난이도의 운동만 선택
    available_exercises = []
    for diff in allowed_difficulties:
        available_exercises.extend(SEED_EXERCISES.get(diff, []))

    if not available_exercises:
        available_exercises = SEED_EXERCISES["low"]

    # 운동 개수 결정 (시간에 따라)
    if duration_min <= 15:
        num_exercises = 3
    elif duration_min <= 30:
        num_exercises = 4
    else:
        num_exercises = 5

    # 운동 선택 (중복 방지)
    selected = random.sample(
        available_exercises, min(num_exercises, len(available_exercises))
    )

    # 시간 분배
    time_per_exercise = duration_min // len(selected)

    for exercise in selected:
        routine.append(
            {
                "name": exercise["name"],
                "name_kr": exercise["name_kr"],
                "category": exercise["category"],
                "difficulty": exercise["difficulty"],
                "met": exercise["met"],
                "duration_min": time_per_exercise,
            }
        )

    return routine


# ============================================================
# 응답 생성 (간소화된 형식)
# ============================================================


def generate_response(
    data: dict, routine: list, condition: dict, karvonen: dict
) -> str:
    """간소화된 운동 분석 응답 생성"""

    # 루틴 난이도 평균 계산
    avg_difficulty = sum(e["difficulty"] for e in routine) / len(routine)
    avg_met = sum(e["met"] for e in routine) / len(routine)

    # 컨디션별 권장 난이도 (6등급)
    recommended_difficulty = {
        "optimal": 5,
        "good": 4.5,
        "moderate_plus": 4,
        "moderate": 4,
        "caution": 3.5,
        "warning": 3,
    }.get(condition["scenario"], 4)

    # 적합도 판단
    if avg_difficulty <= recommended_difficulty:
        fit_emoji = "✅"
        fit_label = "적합"
        fit_comment = "컨디션에 맞는 루틴입니다."
    elif avg_difficulty <= recommended_difficulty + 0.5:
        fit_emoji = "⚠️"
        fit_label = "주의"
        fit_comment = "난이도가 다소 높습니다. 컨디션을 살피며 진행하세요."
    else:
        fit_emoji = "🚨"
        fit_label = "부적합"
        fit_comment = "현재 컨디션에 비해 난이도가 높습니다. 강도를 낮추세요."

    # 루틴 요약
    total_time = sum(e["duration_min"] for e in routine)
    exercise_names = [e["name_kr"] for e in routine]

    # 주의사항 생성
    warnings = []
    rhr_change = data["resting_heart_rate"] - data["usual_resting_heart_rate"]

    if rhr_change >= 10:
        warnings.append(
            f"안정시 심박수가 평소 대비 +{rhr_change}bpm 상승했습니다. 무리하지 마세요. (Buchheit, 2014)"
        )
    if data["sleep_hr"] < 6:
        warnings.append(
            f"수면이 {data['sleep_hr']}시간으로 부족합니다. 고강도 운동은 피하세요. (Milewski, 2014)"
        )

    # 응답 조립
    response = f"""{karvonen['intensity_emoji']} **루틴 분석: {fit_label}** {fit_emoji}

**컨디션:** {condition['label']} ({condition['score']}/100) → {INTENSITY_ZONES[CONDITION_TO_INTENSITY[condition['scenario']]]['label']} 권장

**목표 심박수:** {karvonen['target_low']}-{karvonen['target_high']}bpm ({karvonen['intensity_label']})
└ 카보넨 공식: (220-{data['age']}-{data['resting_heart_rate']}) × {INTENSITY_ZONES[CONDITION_TO_INTENSITY[condition['scenario']]]['range'][0]:.0%}-{INTENSITY_ZONES[CONDITION_TO_INTENSITY[condition['scenario']]]['range'][1]:.0%} + {data['resting_heart_rate']}

**루틴:** {total_time}분, 평균 MET {avg_met:.1f}
- {', '.join(exercise_names)}

💡 **코멘트:** {fit_comment}"""

    if warnings:
        response += f"\n\n⚠️ **주의:** {' '.join(warnings)}"

    return response


# ============================================================
# 사용자 입력 생성
# ============================================================


def generate_user_input(data: dict, routine: list, duration_min: int) -> str:
    """사용자 입력 텍스트 생성"""
    rhr_change = data["resting_heart_rate"] - data["usual_resting_heart_rate"]

    routine_text = "\n".join(
        [
            f"- {e['name_kr']} (난이도 {e['difficulty']}, MET {e['met']}, {e['duration_min']}분)"
            for e in routine
        ]
    )

    return f"""[건강 데이터]
나이: {data['age']}세, 성별: {data['gender']}
resting_heart_rate: {data['resting_heart_rate']}bpm (평소 대비 {rhr_change:+d})
sleep_hr: {data['sleep_hr']}시간
steps: {data['steps']:,}보

[운동 루틴] (총 {duration_min}분)
{routine_text}

이 루틴이 현재 컨디션에 적합한지 분석해주세요."""


# ============================================================
# 시나리오별 데이터 생성
# ============================================================


def generate_raw_data(scenario: str, seed: int) -> dict:
    """시나리오별 생체 데이터 생성"""
    random.seed(seed)

    age = random.randint(25, 55)
    gender = random.choice(["남성", "여성"])
    usual_rhr = random.randint(58, 70)

    scenarios = {
        "optimal": {"rhr_change": (0, 4), "sleep": (7.5, 9.0), "steps": (8000, 12000)},
        "good": {"rhr_change": (3, 7), "sleep": (6.5, 7.5), "steps": (6000, 8500)},
        "moderate": {"rhr_change": (5, 10), "sleep": (5.5, 6.5), "steps": (4000, 6500)},
        "caution": {"rhr_change": (10, 15), "sleep": (4.5, 5.5), "steps": (2500, 4500)},
        "warning": {"rhr_change": (15, 22), "sleep": (3.0, 4.5), "steps": (1000, 3000)},
    }

    config = scenarios.get(scenario, scenarios["moderate"])
    rhr_change = random.randint(*config["rhr_change"])

    return {
        "age": age,
        "gender": gender,
        "resting_heart_rate": usual_rhr + rhr_change,
        "usual_resting_heart_rate": usual_rhr,
        "sleep_hr": round(random.uniform(*config["sleep"]), 1),
        "steps": random.randint(*config["steps"]),
    }


# ============================================================
# 학습 데이터 생성
# ============================================================


def generate_training_data(total_count: int = 300) -> list:
    """학습 데이터 생성"""

    scenario_distribution = {
        "optimal": int(total_count * 0.15),  # 45건
        "good": int(total_count * 0.25),  # 75건
        "moderate": int(total_count * 0.25),  # 75건
        "caution": int(total_count * 0.20),  # 60건
        "warning": int(total_count * 0.15),  # 45건
    }

    durations = [15, 20, 30, 45, 60]
    training_data = []

    for scenario, count in scenario_distribution.items():
        for i in range(count):
            seed = hash(f"exercise_v2_{scenario}_{i}") % (2**32)
            random.seed(seed)

            raw_data = generate_raw_data(scenario, seed)
            duration = random.choice(durations)

            condition = assess_condition(raw_data)
            routine = generate_routine(condition["scenario"], duration)
            karvonen = calculate_karvonen(
                raw_data["age"],
                raw_data["resting_heart_rate"],
                CONDITION_TO_INTENSITY[condition["scenario"]],
            )

            user_input = generate_user_input(raw_data, routine, duration)
            response = generate_response(raw_data, routine, condition, karvonen)

            training_sample = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": response},
                ]
            }

            training_data.append(training_sample)

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
    print("🏋️ 운동 분석 학습 데이터 생성 v2")
    print("=" * 60)
    print("📋 변경사항:")
    print("   - 응답 길이 ~600자 → ~250자")
    print("   - 카보넨 공식 판단 근거 명시")
    print("   - 컨디션 기반 적합도 판단 패턴")
    print()

    training_data = generate_training_data(300)

    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "exercise_analysis_data_v2.jsonl"
    save_jsonl(training_data, output_file)

    print(f"✅ 생성 완료: {len(training_data)}건")
    print(f"📁 저장 위치: {output_file}")

    # 샘플 출력
    print("\n" + "=" * 60)
    print("📝 샘플 응답:")
    print("=" * 60)
    sample = training_data[0]
    print(f"\n[User]\n{sample['messages'][1]['content']}")
    print(f"\n[Assistant]\n{sample['messages'][2]['content']}")
