"""
평가용 테스트 데이터셋 생성 스크립트

총 100건 생성:
- 건강 분석: 30건 (생체 데이터 입력)
- 운동 추천: 30건 (생체 데이터 + 옵션 입력)
- 챗봇 대화: 40건 (질문 텍스트 입력)

난이도 분배: 쉬움 30% / 보통 40% / 어려움 30%

파인튜닝 데이터와 중복 없음 (seed=9999 사용)
"""

import json
import random
from pathlib import Path

# 파인튜닝 데이터와 다른 시드 사용
random.seed(9999)


# ============================================
# 생체지표 범위 정의 (전문 기준 기반)
# ============================================

# 심박수 (AHA, Buchheit 기준)
HEART_RATE = {"normal": (60, 100), "borderline": (100, 110), "danger": (110, 130)}

RESTING_HEART_RATE = {
    "excellent": (50, 60),
    "normal": (60, 70),
    "borderline": (70, 85),
    "danger": (85, 100),
}

# 수면 (Milewski 기준)
SLEEP_HR = {
    "excellent": (8.0, 9.0),  # 최적
    "good": (7.0, 8.0),  # 양호
    "fair": (6.0, 7.0),  # 부족
    "poor": (5.0, 6.0),  # 매우 부족
    "danger": (3.5, 5.0),  # 위험 (부상 1.7배)
}

# 걸음수 (WHO/CDC 기준)
STEPS = {
    "excellent": (10000, 15000),
    "good": (7000, 10000),
    "fair": (5000, 7000),
    "poor": (3000, 5000),
    "danger": (1000, 3000),
}

# 이동거리 (WHO 기준)
DISTANCE_KM = {
    "excellent": (8.0, 12.0),
    "good": (5.0, 8.0),
    "fair": (3.0, 5.0),
    "poor": (2.0, 3.0),
    "danger": (0.5, 2.0),
}

# 활동 칼로리 (ACSM 기준)
ACTIVE_CALORIES = {
    "excellent": (500, 800),
    "good": (300, 500),
    "fair": (200, 300),
    "poor": (100, 200),
    "danger": (30, 100),
}

# 산소포화도 (WHO 기준)
OXYGEN_SATURATION = {"normal": (95, 100), "borderline": (93, 95), "low": (90, 93)}

# BMI (WHO 기준)
BMI = {
    "underweight": (16.0, 18.5),
    "normal": (18.5, 25.0),
    "overweight": (25.0, 30.0),
    "obese": (30.0, 35.0),
}

# 체중
WEIGHT = {"range": (50.0, 95.0)}


# ============================================
# 유틸리티 함수
# ============================================


def random_value(range_tuple, decimals=0):
    """범위 내 랜덤 값 생성"""
    val = random.uniform(range_tuple[0], range_tuple[1])
    if decimals == 0:
        return int(val)
    return round(val, decimals)


def get_expected_condition(data):
    """생체 데이터 기반 기대 컨디션 판정"""
    issues = []

    # 수면 체크 (Milewski 기준)
    if data["sleep_hr"] < 6:
        issues.append("sleep_danger")
    elif data["sleep_hr"] < 7:
        issues.append("sleep_poor")

    # 안정시심박 체크 (Buchheit 기준)
    if data["resting_heart_rate"] > 85:
        issues.append("rhr_danger")
    elif data["resting_heart_rate"] > 75:
        issues.append("rhr_high")

    # 활동량 체크 (WHO 기준)
    if data["steps"] < 5000:
        issues.append("steps_low")

    # 산소포화도 체크
    if data["oxygen_saturation"] < 93:
        issues.append("spo2_danger")
    elif data["oxygen_saturation"] < 95:
        issues.append("spo2_low")

    # BMI 체크
    if data["bmi"] > 30 or data["bmi"] < 18.5:
        issues.append("bmi_abnormal")
    elif data["bmi"] > 25:
        issues.append("bmi_overweight")

    # 컨디션 레벨 결정
    if len(issues) == 0:
        return "optimal", ["양호", "충분", "정상", "좋은"], "고강도 가능"
    elif len(issues) <= 2:
        return "good", ["주의", "부족", "권장"], "중강도 권장"
    else:
        return "warning", ["위험", "경고", "휴식", "피로"], "저강도 또는 휴식"


def get_expected_exercise(data, options):
    """생체 데이터 + 옵션 기반 기대 운동 추천"""
    condition, _, intensity_rec = get_expected_condition(data)

    if condition == "optimal":
        return {
            "intensity_level": "중-고강도",
            "keywords": ["운동", "루틴", "세트", "분"],
            "has_warmup": True,
            "has_cooldown": True,
        }
    elif condition == "good":
        return {
            "intensity_level": "중강도",
            "keywords": ["운동", "루틴", "주의", "세트"],
            "has_warmup": True,
            "has_cooldown": True,
        }
    else:
        return {
            "intensity_level": "저강도",
            "keywords": ["가벼운", "스트레칭", "휴식", "주의"],
            "has_warmup": True,
            "has_cooldown": True,
        }


# ============================================
# 난이도별 생체 데이터 생성
# ============================================


def generate_easy_data():
    """
    쉬움 (Easy) - 판단이 명확한 케이스
    - 모든 지표 정상 OR 모든 지표 위험
    """
    # 50% 확률로 전부 정상 / 전부 위험
    if random.random() < 0.5:
        # 전부 정상
        return {
            "heart_rate": random_value(HEART_RATE["normal"]),
            "resting_heart_rate": random_value(RESTING_HEART_RATE["normal"]),
            "sleep_hr": random_value(SLEEP_HR["good"], 1),
            "steps": random_value(STEPS["good"]),
            "distance_km": random_value(DISTANCE_KM["good"], 1),
            "active_calories": random_value(ACTIVE_CALORIES["good"]),
            "oxygen_saturation": random_value(OXYGEN_SATURATION["normal"]),
            "weight": random_value(WEIGHT["range"], 1),
            "bmi": random_value(BMI["normal"], 1),
        }
    else:
        # 전부 위험
        return {
            "heart_rate": random_value(HEART_RATE["danger"]),
            "resting_heart_rate": random_value(RESTING_HEART_RATE["danger"]),
            "sleep_hr": random_value(SLEEP_HR["danger"], 1),
            "steps": random_value(STEPS["danger"]),
            "distance_km": random_value(DISTANCE_KM["danger"], 1),
            "active_calories": random_value(ACTIVE_CALORIES["danger"]),
            "oxygen_saturation": random_value(OXYGEN_SATURATION["low"]),
            "weight": random_value(WEIGHT["range"], 1),
            "bmi": random_value(BMI["obese"], 1),
        }


def generate_medium_data():
    """
    보통 (Medium) - 1-2개 지표만 문제
    - 대부분 정상, 1-2개만 경계/위험
    """
    data = {
        "heart_rate": random_value(HEART_RATE["normal"]),
        "resting_heart_rate": random_value(RESTING_HEART_RATE["normal"]),
        "sleep_hr": random_value(SLEEP_HR["good"], 1),
        "steps": random_value(STEPS["good"]),
        "distance_km": random_value(DISTANCE_KM["good"], 1),
        "active_calories": random_value(ACTIVE_CALORIES["good"]),
        "oxygen_saturation": random_value(OXYGEN_SATURATION["normal"]),
        "weight": random_value(WEIGHT["range"], 1),
        "bmi": random_value(BMI["normal"], 1),
    }

    # 1-2개 지표를 문제 상태로 변경
    problem_count = random.choice([1, 2])
    problem_fields = random.sample(
        ["sleep_hr", "resting_heart_rate", "steps", "oxygen_saturation", "bmi"],
        problem_count,
    )

    for field in problem_fields:
        if field == "sleep_hr":
            data["sleep_hr"] = random_value(SLEEP_HR["fair"], 1)
        elif field == "resting_heart_rate":
            data["resting_heart_rate"] = random_value(RESTING_HEART_RATE["borderline"])
        elif field == "steps":
            data["steps"] = random_value(STEPS["fair"])
        elif field == "oxygen_saturation":
            data["oxygen_saturation"] = random_value(OXYGEN_SATURATION["borderline"])
        elif field == "bmi":
            data["bmi"] = random_value(BMI["overweight"], 1)

    return data


def generate_hard_data():
    """
    어려움 (Hard) - 복합적 판단 필요
    - 여러 지표가 혼재 (일부 좋음 + 일부 나쁨)
    - 상충되는 신호 (예: 활동량 높음 + 피로 신호)
    """
    # 상충 패턴 선택
    pattern = random.choice(
        ["high_activity_fatigue", "mixed_signals", "borderline_all"]
    )

    if pattern == "high_activity_fatigue":
        # 활동량 높지만 피로 신호
        return {
            "heart_rate": random_value((80, 95)),
            "resting_heart_rate": random_value(RESTING_HEART_RATE["borderline"]),
            "sleep_hr": random_value(SLEEP_HR["fair"], 1),
            "steps": random_value(STEPS["excellent"]),  # 높음
            "distance_km": random_value(DISTANCE_KM["excellent"], 1),  # 높음
            "active_calories": random_value(ACTIVE_CALORIES["excellent"]),  # 높음
            "oxygen_saturation": random_value(OXYGEN_SATURATION["borderline"]),
            "weight": random_value(WEIGHT["range"], 1),
            "bmi": random_value(BMI["overweight"], 1),
        }

    elif pattern == "mixed_signals":
        # 혼합 신호
        return {
            "heart_rate": random_value(HEART_RATE["normal"]),
            "resting_heart_rate": random_value(RESTING_HEART_RATE["danger"]),  # 나쁨
            "sleep_hr": random_value(SLEEP_HR["excellent"], 1),  # 좋음
            "steps": random_value(STEPS["poor"]),  # 나쁨
            "distance_km": random_value(DISTANCE_KM["poor"], 1),
            "active_calories": random_value(ACTIVE_CALORIES["excellent"]),  # 좋음
            "oxygen_saturation": random_value(OXYGEN_SATURATION["borderline"]),
            "weight": random_value(WEIGHT["range"], 1),
            "bmi": random_value(BMI["normal"], 1),
        }

    else:  # borderline_all
        # 모든 지표가 경계값
        return {
            "heart_rate": random_value(HEART_RATE["borderline"]),
            "resting_heart_rate": random_value(RESTING_HEART_RATE["borderline"]),
            "sleep_hr": random_value(SLEEP_HR["fair"], 1),
            "steps": random_value(STEPS["fair"]),
            "distance_km": random_value(DISTANCE_KM["fair"], 1),
            "active_calories": random_value(ACTIVE_CALORIES["fair"]),
            "oxygen_saturation": random_value(OXYGEN_SATURATION["borderline"]),
            "weight": random_value(WEIGHT["range"], 1),
            "bmi": random_value(BMI["overweight"], 1),
        }


# ============================================
# 건강 분석 테스트 데이터 생성 (30건)
# ============================================


def generate_health_data():
    """
    건강 분석 테스트 데이터 30건 생성
    - 쉬움: 9건 (30%)
    - 보통: 12건 (40%)
    - 어려움: 9건 (30%)
    """
    test_cases = []

    # 쉬움 9건
    for i in range(9):
        data = generate_easy_data()
        condition, keywords, exercise_rec = get_expected_condition(data)

        test_cases.append(
            {
                "id": f"HD{str(i+1).zfill(3)}",
                "type": "health_analysis",
                "difficulty": "easy",
                "input_data": data,
                "expected": {
                    "condition_level": condition,
                    "keywords": keywords,
                    "exercise_recommendation": exercise_rec,
                },
            }
        )

    # 보통 12건
    for i in range(12):
        data = generate_medium_data()
        condition, keywords, exercise_rec = get_expected_condition(data)

        test_cases.append(
            {
                "id": f"HD{str(i+10).zfill(3)}",
                "type": "health_analysis",
                "difficulty": "medium",
                "input_data": data,
                "expected": {
                    "condition_level": condition,
                    "keywords": keywords,
                    "exercise_recommendation": exercise_rec,
                },
            }
        )

    # 어려움 9건
    for i in range(9):
        data = generate_hard_data()
        condition, keywords, exercise_rec = get_expected_condition(data)

        test_cases.append(
            {
                "id": f"HD{str(i+22).zfill(3)}",
                "type": "health_analysis",
                "difficulty": "hard",
                "input_data": data,
                "expected": {
                    "condition_level": condition,
                    "keywords": keywords,
                    "exercise_recommendation": exercise_rec,
                },
            }
        )

    return {"test_cases": test_cases}


# ============================================
# 운동 추천 테스트 데이터 생성 (30건)
# ============================================

DIFFICULTY_OPTIONS = ["하", "중", "상"]
DURATION_OPTIONS = [15, 20, 30, 45, 60]


def generate_exercise_data():
    """
    운동 추천 테스트 데이터 30건 생성
    - 쉬움: 9건 (30%)
    - 보통: 12건 (40%)
    - 어려움: 9건 (30%)
    """
    test_cases = []

    # 쉬움 9건
    for i in range(9):
        data = generate_easy_data()
        options = {
            "difficulty": random.choice(DIFFICULTY_OPTIONS),
            "duration_min": random.choice(DURATION_OPTIONS),
        }
        expected = get_expected_exercise(data, options)

        test_cases.append(
            {
                "id": f"ED{str(i+1).zfill(3)}",
                "type": "exercise_recommendation",
                "difficulty": "easy",
                "input_data": data,
                "options": options,
                "expected": expected,
            }
        )

    # 보통 12건
    for i in range(12):
        data = generate_medium_data()
        options = {
            "difficulty": random.choice(DIFFICULTY_OPTIONS),
            "duration_min": random.choice(DURATION_OPTIONS),
        }
        expected = get_expected_exercise(data, options)

        test_cases.append(
            {
                "id": f"ED{str(i+10).zfill(3)}",
                "type": "exercise_recommendation",
                "difficulty": "medium",
                "input_data": data,
                "options": options,
                "expected": expected,
            }
        )

    # 어려움 9건
    for i in range(9):
        data = generate_hard_data()
        options = {
            "difficulty": random.choice(DIFFICULTY_OPTIONS),
            "duration_min": random.choice(DURATION_OPTIONS),
        }
        expected = get_expected_exercise(data, options)

        test_cases.append(
            {
                "id": f"ED{str(i+22).zfill(3)}",
                "type": "exercise_recommendation",
                "difficulty": "hard",
                "input_data": data,
                "options": options,
                "expected": expected,
            }
        )

    return {"test_cases": test_cases}


# ============================================
# 챗봇 대화 테스트 데이터 생성 (40건)
# ============================================

CHAT_SCENARIOS = {
    "devil_coach": {
        "easy": [
            {"message": "오늘 운동하기 싫어", "keywords": ["해야지", "변명", "시작"]},
            {"message": "운동 의욕이 없어", "keywords": ["의지", "시작", "당장"]},
            {"message": "헬스장 가기 귀찮아", "keywords": ["귀찮", "핑계", "움직여"]},
            {"message": "오늘 쉬어도 돼?", "keywords": ["안돼", "일어나", "게으름"]},
        ],
        "medium": [
            {"message": "다이어트 실패했어", "keywords": ["다시", "포기", "변명"]},
            {
                "message": "운동 습관 들이는 방법 알려줘",
                "keywords": ["꾸준", "매일", "시작"],
            },
            {"message": "작심삼일인데 어떡해?", "keywords": ["의지", "약해", "핑계"]},
            {"message": "살 안 빠져서 스트레스야", "keywords": ["노력", "부족", "더"]},
            {"message": "꾸준히 하는 게 힘들어", "keywords": ["핑계", "변명", "해"]},
            {
                "message": "목표를 어떻게 세워야 해?",
                "keywords": ["목표", "구체적", "실천"],
            },
        ],
        "hard": [
            {
                "message": "수면 부족인데 운동해야 할까?",
                "keywords": ["해야지", "변명", "컨디션"],
            },
            {
                "message": "몸이 안 좋은데 운동해도 돼?",
                "keywords": ["상태", "판단", "조절"],
            },
            {"message": "번아웃 온 것 같아", "keywords": ["쉬어", "회복", "다시"]},
            {"message": "의지가 약해서 못하겠어", "keywords": ["변명", "의지", "시작"]},
        ],
    },
    "angel_coach": {
        "easy": [
            {"message": "오늘 운동 잘했어!", "keywords": ["잘했어", "대단해", "최고"]},
            {"message": "목표 달성했어", "keywords": ["축하", "멋져", "자랑스러워"]},
            {"message": "1만보 걸었어!", "keywords": ["대단해", "훌륭해", "잘했어"]},
            {"message": "체중 줄었어!", "keywords": ["축하", "노력", "보람"]},
        ],
        "medium": [
            {"message": "한 달째 운동 중이야", "keywords": ["꾸준", "멋져", "대단"]},
            {
                "message": "더 열심히 하고 싶어",
                "keywords": ["응원", "할 수 있어", "멋져"],
            },
            {"message": "다음 목표는 뭐로 할까?", "keywords": ["목표", "도전", "응원"]},
            {
                "message": "운동이 재밌어지기 시작했어",
                "keywords": ["좋아", "기뻐", "멋져"],
            },
            {
                "message": "꾸준히 해서 뿌듯해",
                "keywords": ["자랑스러워", "대단", "훌륭"],
            },
        ],
        "hard": [
            {
                "message": "좀 더 강도 높여도 될까?",
                "keywords": ["조심", "천천히", "응원"],
            },
            {"message": "근육 붙은 것 같아", "keywords": ["멋져", "노력", "결과"]},
            {
                "message": "다음 단계로 가고 싶어",
                "keywords": ["도전", "응원", "할 수 있어"],
            },
            {
                "message": "오버트레이닝인지 모르겠어",
                "keywords": ["휴식", "회복", "조심"],
            },
        ],
    },
    "booster_coach": {
        "easy": [
            {"message": "힘내라고 해줘", "keywords": ["할 수 있어", "파이팅", "응원"]},
            {"message": "응원해줘", "keywords": ["최고", "믿어", "파이팅"]},
            {"message": "지쳤어", "keywords": ["괜찮아", "쉬어도", "힘내"]},
            {"message": "할 수 있을까?", "keywords": ["당연", "할 수 있어", "믿어"]},
        ],
        "medium": [
            {"message": "오늘 좀 힘들어", "keywords": ["괜찮아", "할 수 있어", "응원"]},
            {"message": "그래도 운동해야겠지?", "keywords": ["대단해", "의지", "응원"]},
            {"message": "의지가 약해", "keywords": ["괜찮아", "천천히", "할 수 있어"]},
            {"message": "자신감이 없어", "keywords": ["믿어", "할 수 있어", "대단"]},
            {
                "message": "잘하고 있는 거 맞아?",
                "keywords": ["잘하고 있어", "대단", "멋져"],
            },
            {
                "message": "끝까지 갈 수 있을까?",
                "keywords": ["당연", "믿어", "할 수 있어"],
            },
        ],
        "hard": [
            {
                "message": "포기하고 싶어",
                "keywords": ["포기하지마", "할 수 있어", "믿어"],
            },
            {
                "message": "남들보다 느린 것 같아",
                "keywords": ["비교하지마", "괜찮아", "멋져"],
            },
            {
                "message": "실패할 것 같아",
                "keywords": ["실패해도", "다시", "할 수 있어"],
            },
        ],
    },
}


def generate_chat_queries():
    """
    챗봇 대화 테스트 데이터 40건 생성
    - 쉬움: 12건 (30%)
    - 보통: 16건 (40%)
    - 어려움: 12건 (30%)
    """
    test_cases = []
    idx = 1

    for character, difficulties in CHAT_SCENARIOS.items():
        for difficulty, scenarios in difficulties.items():
            for scenario in scenarios:
                test_cases.append(
                    {
                        "id": f"CQ{str(idx).zfill(3)}",
                        "type": "chat",
                        "difficulty": difficulty,
                        "input_data": {
                            "message": scenario["message"],
                            "character": character,
                        },
                        "expected": {
                            "tone": {
                                "devil_coach": "tough_love",
                                "angel_coach": "supportive",
                                "booster_coach": "encouraging",
                            }[character],
                            "keywords": scenario["keywords"],
                        },
                    }
                )
                idx += 1

    return {"test_cases": test_cases}


# ============================================
# 메인 실행
# ============================================


def main():
    print("=" * 60)
    print("🚀 평가용 테스트 데이터셋 생성 시작")
    print("=" * 60)

    output_dir = Path(__file__).parent.parent / "datasets"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 기존 파일 삭제
    for old_file in ["health_queries.json", "exercise_queries.json"]:
        old_path = output_dir / old_file
        if old_path.exists():
            old_path.unlink()
            print(f"🗑️ 기존 파일 삭제: {old_file}")

    # 1. 건강 분석 데이터 생성 (30건)
    health_data = generate_health_data()
    health_path = output_dir / "health_data.json"
    with open(health_path, "w", encoding="utf-8") as f:
        json.dump(health_data, f, ensure_ascii=False, indent=2)

    easy = sum(1 for t in health_data["test_cases"] if t["difficulty"] == "easy")
    medium = sum(1 for t in health_data["test_cases"] if t["difficulty"] == "medium")
    hard = sum(1 for t in health_data["test_cases"] if t["difficulty"] == "hard")
    print(f"\n✅ 건강 분석: {len(health_data['test_cases'])}건")
    print(f"   - 쉬움: {easy}건, 보통: {medium}건, 어려움: {hard}건")
    print(f"   → {health_path}")

    # 2. 운동 추천 데이터 생성 (30건)
    exercise_data = generate_exercise_data()
    exercise_path = output_dir / "exercise_data.json"
    with open(exercise_path, "w", encoding="utf-8") as f:
        json.dump(exercise_data, f, ensure_ascii=False, indent=2)

    easy = sum(1 for t in exercise_data["test_cases"] if t["difficulty"] == "easy")
    medium = sum(1 for t in exercise_data["test_cases"] if t["difficulty"] == "medium")
    hard = sum(1 for t in exercise_data["test_cases"] if t["difficulty"] == "hard")
    print(f"\n✅ 운동 추천: {len(exercise_data['test_cases'])}건")
    print(f"   - 쉬움: {easy}건, 보통: {medium}건, 어려움: {hard}건")
    print(f"   → {exercise_path}")

    # 3. 챗봇 대화 데이터 생성 (40건)
    chat_data = generate_chat_queries()
    chat_path = output_dir / "chat_queries.json"
    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)

    easy = sum(1 for t in chat_data["test_cases"] if t["difficulty"] == "easy")
    medium = sum(1 for t in chat_data["test_cases"] if t["difficulty"] == "medium")
    hard = sum(1 for t in chat_data["test_cases"] if t["difficulty"] == "hard")
    print(f"\n✅ 챗봇 대화: {len(chat_data['test_cases'])}건")
    print(f"   - 쉬움: {easy}건, 보통: {medium}건, 어려움: {hard}건")
    print(f"   → {chat_path}")

    # 총계
    total = (
        len(health_data["test_cases"])
        + len(exercise_data["test_cases"])
        + len(chat_data["test_cases"])
    )

    print(f"\n{'=' * 60}")
    print(f"📊 총 {total}건 생성 완료")
    print(f"{'=' * 60}")

    # 요약 테이블
    print(f"\n| 서비스 | 쉬움 | 보통 | 어려움 | 총계 |")
    print(f"|--------|------|------|--------|------|")

    for name, data in [
        ("건강 분석", health_data),
        ("운동 추천", exercise_data),
        ("챗봇 대화", chat_data),
    ]:
        e = sum(1 for t in data["test_cases"] if t["difficulty"] == "easy")
        m = sum(1 for t in data["test_cases"] if t["difficulty"] == "medium")
        h = sum(1 for t in data["test_cases"] if t["difficulty"] == "hard")
        print(f"| {name} | {e}건 | {m}건 | {h}건 | {e+m+h}건 |")


if __name__ == "__main__":
    main()
