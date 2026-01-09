"""
3단계 평가용 테스트 데이터 생성 스크립트

구조:
- 생체 데이터 60건: 건강 분석 + 운동 AI 분석 둘 다 평가
- 챗봇 질문 40건: 챗봇 평가
= 총 100건

목적:
- Baseline / LangChain / Fine-tuned 3단계를 동일한 데이터로 평가
- 단계별 개선 정도를 수치로 비교
"""

import json
import random
from datetime import datetime
from pathlib import Path

# ============================================================
# 평가 지표 정의
# ============================================================

# 컨디션 등급 기준 (실제 서비스 health_interpreter.py 기준 - 6등급)
CONDITION_GRADES = {
    "optimal": {"min_score": 80, "exercise_rec": "고강도 포함 모든 운동 가능"},
    "good": {"min_score": 70, "exercise_rec": "중-고강도 운동 가능"},
    "moderate_plus": {"min_score": 55, "exercise_rec": "중강도까지 권장"},
    "moderate": {"min_score": 45, "exercise_rec": "중강도까지 권장"},
    "caution": {"min_score": 35, "exercise_rec": "저강도만 권장"},
    "warning": {"min_score": 0, "exercise_rec": "휴식 권장"},
}

# 전문 기준 인용 키워드
PROFESSIONAL_REFERENCES = {
    "milewski": ["Milewski", "1.7배", "부상 위험", "8시간 미만"],
    "buchheit": ["Buchheit", "+10bpm", "피로 신호", "안정시 심박"],
    "acsm": ["ACSM", "권장량", "가이드라인"],
    "karvonen": ["카보넨", "Karvonen", "목표 심박수", "최대심박수"],
}


# ============================================================
# 생체 데이터 생성
# ============================================================


def generate_biometric_data(scenario: str, seed: int) -> dict:
    """시나리오별 생체 데이터 생성"""
    random.seed(seed)

    age = random.randint(25, 55)
    gender = random.choice(["남성", "여성"])
    weight = random.randint(50, 90) if gender == "여성" else random.randint(60, 95)
    height = (
        random.uniform(1.55, 1.75) if gender == "여성" else random.uniform(1.65, 1.85)
    )
    bmi = round(weight / (height**2), 1)
    usual_rhr = random.randint(58, 70)

    scenarios = {
        "optimal": {
            "rhr_change": (0, 4),
            "sleep": (7.5, 9.0),
            "steps": (8000, 12000),
            "spo2": (97, 99),
            "calories": (300, 500),
        },
        "good": {
            "rhr_change": (3, 7),
            "sleep": (7.0, 8.0),
            "steps": (7000, 9000),
            "spo2": (96, 98),
            "calories": (250, 400),
        },
        "moderate_plus": {
            "rhr_change": (5, 9),
            "sleep": (6.0, 7.0),
            "steps": (5500, 7500),
            "spo2": (95, 97),
            "calories": (200, 350),
        },
        "moderate": {
            "rhr_change": (7, 12),
            "sleep": (5.5, 6.5),
            "steps": (4500, 6000),
            "spo2": (95, 97),
            "calories": (150, 300),
        },
        "caution": {
            "rhr_change": (10, 15),
            "sleep": (4.5, 5.5),
            "steps": (2500, 4500),
            "spo2": (94, 96),
            "calories": (100, 200),
        },
        "warning": {
            "rhr_change": (15, 22),
            "sleep": (3.0, 4.5),
            "steps": (1000, 3000),
            "spo2": (92, 95),
            "calories": (50, 150),
        },
    }

    config = scenarios.get(scenario, scenarios["moderate"])
    rhr_change = random.randint(*config["rhr_change"])
    resting_hr = usual_rhr + rhr_change
    steps = random.randint(*config["steps"])

    return {
        "age": age,
        "gender": gender,
        "heart_rate": resting_hr + random.randint(5, 20),
        "resting_heart_rate": resting_hr,
        "usual_resting_heart_rate": usual_rhr,
        "sleep_hr": round(random.uniform(*config["sleep"]), 1),
        "steps": steps,
        "distance_km": round(steps / 1300, 2),
        "active_calories": random.randint(*config["calories"]),
        "oxygen_saturation": random.randint(*config["spo2"]),
        "weight": weight,
        "bmi": bmi,
    }


def calculate_expected_score(data: dict) -> int:
    """생체 데이터로부터 예상 컨디션 점수 계산"""
    score = 100

    # RHR 변화 감점
    rhr_change = data["resting_heart_rate"] - data["usual_resting_heart_rate"]
    if rhr_change >= 15:
        score -= 35
    elif rhr_change >= 10:
        score -= 25
    elif rhr_change >= 5:
        score -= 10

    # 수면 부족 감점
    sleep = data["sleep_hr"]
    if sleep < 5:
        score -= 30
    elif sleep < 6:
        score -= 20
    elif sleep < 7:
        score -= 10

    # 활동량 부족 감점
    steps = data["steps"]
    if steps < 3000:
        score -= 15
    elif steps < 5000:
        score -= 10

    # 산소포화도 감점
    spo2 = data["oxygen_saturation"]
    if spo2 < 93:
        score -= 15
    elif spo2 < 95:
        score -= 5

    return max(0, min(100, score))


def get_expected_grade(score: int) -> str:
    """점수 → 등급 (6등급 기준)"""
    if score >= 80:
        return "optimal"
    elif score >= 70:
        return "good"
    elif score >= 55:
        return "moderate_plus"
    elif score >= 45:
        return "moderate"
    elif score >= 35:
        return "caution"
    else:
        return "warning"


def generate_health_expected(data: dict, scenario: str) -> dict:
    """건강 분석 평가 기준 생성"""
    score = calculate_expected_score(data)
    grade = get_expected_grade(score)
    rhr_change = data["resting_heart_rate"] - data["usual_resting_heart_rate"]

    # 기본 키워드 (6등급 기준)
    keywords = []
    if grade in ["optimal", "good"]:
        keywords.extend(["양호", "정상", "충분"])
    elif grade in ["moderate_plus", "moderate"]:
        keywords.extend(["보통", "주의"])
    else:
        keywords.extend(["부족", "휴식", "피로"])

    # 전문 기준 인용 여부
    should_cite_buchheit = rhr_change >= 10
    should_cite_milewski = data["sleep_hr"] < 6

    return {
        # 기존 평가 지표
        "condition_level": grade,
        "expected_score_range": [max(0, score - 10), min(100, score + 10)],
        "keywords": keywords,
        "exercise_recommendation": CONDITION_GRADES[grade]["exercise_rec"],
        # 파인튜닝 평가 지표 (형식/패턴)
        "has_condition_score": True,
        "has_grade": True,
        "has_judgment_basis": True,  # 판단 근거 포함 여부
        # 전문 기준 인용 평가
        "should_cite_buchheit": should_cite_buchheit,
        "should_cite_milewski": should_cite_milewski,
        # 품질 지표
        "min_length": 80,
        "max_length": 300,
        "friendly_tone": True,
    }


def generate_exercise_expected(data: dict, scenario: str, duration_min: int) -> dict:
    """운동 분석 평가 기준 생성"""
    score = calculate_expected_score(data)
    grade = get_expected_grade(score)

    # 카보넨 공식 계산
    max_hr = 220 - data["age"]
    hr_reserve = max_hr - data["resting_heart_rate"]

    # 등급별 권장 강도 (6등급)
    intensity_map = {
        "optimal": (0.75, 0.90),
        "good": (0.65, 0.80),
        "moderate_plus": (0.55, 0.70),
        "moderate": (0.55, 0.70),
        "caution": (0.45, 0.60),
        "warning": (0.40, 0.55),
    }
    low_pct, high_pct = intensity_map[grade]

    target_hr_low = round(hr_reserve * low_pct + data["resting_heart_rate"])
    target_hr_high = round(hr_reserve * high_pct + data["resting_heart_rate"])

    return {
        # 기존 평가 지표
        "condition_level": grade,
        "recommended_intensity": {
            "optimal": "고강도",
            "good": "중-고강도",
            "moderate_plus": "중강도",
            "moderate": "중강도",
            "caution": "저-중강도",
            "warning": "저강도/휴식",
        }[grade],
        "keywords": ["루틴", "운동", "컨디션"],
        # 카보넨 공식 평가
        "has_karvonen": True,
        "expected_target_hr_low": target_hr_low,
        "expected_target_hr_high": target_hr_high,
        "target_hr_tolerance": 10,  # ±10bpm 허용
        # 형식 평가
        "has_fit_assessment": True,  # 적합도 평가 포함 여부
        "has_coach_comment": True,  # 코치 코멘트 포함 여부
        # 품질 지표
        "min_length": 100,
        "max_length": 350,
    }


# ============================================================
# 운동 루틴 생성 (실제 시드 운동 16종)
# ============================================================

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


def generate_routine(scenario: str, duration_min: int) -> list:
    """컨디션에 맞는 운동 루틴 생성 (실제 시드 운동 16종 사용)"""

    # 컨디션별 적합 난이도 매핑 (6등급)
    scenario_to_difficulty = {
        "optimal": ["low", "moderate", "high"],  # 모든 난이도 가능
        "good": ["low", "moderate", "high"],  # 모든 난이도 가능
        "moderate_plus": ["low", "moderate"],  # 중강도까지
        "moderate": ["low", "moderate"],  # 중강도까지
        "caution": ["low"],  # 저강도만
        "warning": ["low"],  # 저강도만
    }

    allowed_difficulties = scenario_to_difficulty.get(scenario, ["low", "moderate"])

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

    routine = []
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
# 챗봇 질문 생성
# ============================================================

CHAT_TEMPLATES = {
    # 수면 관련 (Milewski 인용 기대)
    "sleep": [
        {
            "question": "수면이 {hours}시간밖에 안 됐는데 운동해도 될까요?",
            "params": {"hours": [3, 4, 4.5, 5, 5.5]},
            "expected": {
                "keywords": ["수면", "부족", "휴식"],
                "should_cite_milewski": True,
                "should_cite_buchheit": False,
                "tone": "friendly",
                "min_length": 50,
                "max_length": 200,
            },
        },
        {
            "question": "7시간 잤는데 운동해도 되나요?",
            "expected": {
                "keywords": ["수면", "충분", "운동"],
                "should_cite_milewski": False,
                "should_cite_buchheit": False,
                "tone": "friendly",
                "min_length": 50,
                "max_length": 200,
            },
        },
        {
            "question": "수면이 운동에 왜 중요한가요?",
            "expected": {
                "keywords": ["수면", "회복", "근육"],
                "should_cite_milewski": True,
                "should_cite_buchheit": False,
                "tone": "friendly",
                "min_length": 80,
                "max_length": 250,
            },
        },
    ],
    # 심박수 관련 (Buchheit 인용 기대)
    "heart_rate": [
        {
            "question": "안정시 심박수가 평소보다 {change}bpm 높아요. 운동해도 될까요?",
            "params": {"change": [10, 12, 15, 18]},
            "expected": {
                "keywords": ["심박", "피로", "휴식"],
                "should_cite_milewski": False,
                "should_cite_buchheit": True,
                "tone": "friendly",
                "min_length": 50,
                "max_length": 200,
            },
        },
        {
            "question": "RHR이 뭐예요?",
            "expected": {
                "keywords": ["안정시", "심박", "측정"],
                "should_cite_milewski": False,
                "should_cite_buchheit": False,
                "tone": "friendly",
                "min_length": 50,
                "max_length": 200,
            },
        },
        {
            "question": "운동할 때 심박수 얼마까지 올려도 되나요?",
            "expected": {
                "keywords": ["최대", "심박", "강도"],
                "should_cite_milewski": False,
                "should_cite_buchheit": False,
                "has_karvonen": True,
                "tone": "friendly",
                "min_length": 80,
                "max_length": 250,
            },
        },
    ],
    # 운동 방법 (ACSM 인용 기대)
    "exercise": [
        {
            "question": "중강도 운동이 뭐예요?",
            "expected": {
                "keywords": ["강도", "심박", "운동"],
                "should_cite_acsm": True,
                "tone": "friendly",
                "min_length": 80,
                "max_length": 250,
            },
        },
        {
            "question": "워밍업 꼭 해야 하나요?",
            "expected": {
                "keywords": ["워밍업", "부상", "준비"],
                "tone": "friendly",
                "min_length": 50,
                "max_length": 200,
            },
        },
        {
            "question": "유산소랑 근력 운동 순서가 어떻게 되나요?",
            "expected": {
                "keywords": ["유산소", "근력", "순서"],
                "tone": "friendly",
                "min_length": 80,
                "max_length": 250,
            },
        },
        {
            "question": "HIIT가 뭐예요?",
            "expected": {
                "keywords": ["고강도", "인터벌", "운동"],
                "tone": "friendly",
                "min_length": 80,
                "max_length": 250,
            },
        },
    ],
    # 컨디션/피로
    "condition": [
        {
            "question": "오늘 컨디션이 안 좋은데 운동해야 할까요?",
            "expected": {
                "keywords": ["컨디션", "휴식", "무리"],
                "tone": "friendly",
                "min_length": 50,
                "max_length": 200,
            },
        },
        {
            "question": "매일 운동해도 되나요?",
            "expected": {
                "keywords": ["휴식", "회복", "주"],
                "should_cite_acsm": True,
                "tone": "friendly",
                "min_length": 80,
                "max_length": 250,
            },
        },
        {
            "question": "근육통이 있는데 운동해도 되나요?",
            "expected": {
                "keywords": ["근육통", "회복", "운동"],
                "tone": "friendly",
                "min_length": 50,
                "max_length": 200,
            },
        },
    ],
    # 활동량
    "activity": [
        {
            "question": "걸음수가 {steps}보밖에 안 돼요. 부족한가요?",
            "params": {"steps": [2000, 3000, 4000]},
            "expected": {
                "keywords": ["걸음", "활동", "권장"],
                "tone": "friendly",
                "min_length": 50,
                "max_length": 200,
            },
        },
        {
            "question": "만보 걷기가 정말 효과 있나요?",
            "expected": {
                "keywords": ["걷기", "효과", "건강"],
                "tone": "friendly",
                "min_length": 80,
                "max_length": 250,
            },
        },
    ],
}


def generate_chat_question(category: str, template: dict) -> dict:
    """챗봇 질문 및 평가 기준 생성"""
    question = template["question"]

    # 파라미터 치환
    if "params" in template:
        for key, values in template["params"].items():
            value = random.choice(values)
            question = question.replace(f"{{{key}}}", str(value))

    return {
        "question": question,
        "category": category,
        "expected": template["expected"],
    }


# ============================================================
# 테스트 데이터 생성
# ============================================================


def generate_biometric_test_cases(count: int = 60) -> list:
    """생체 데이터 테스트 케이스 생성 (건강 분석 + 운동 분석용)"""

    # 시나리오별 분배 (6등급)
    scenario_counts = {
        "optimal": int(count * 0.12),  # 7건 (A등급)
        "good": int(count * 0.15),  # 9건 (B등급)
        "moderate_plus": int(count * 0.18),  # 11건 (C+등급)
        "moderate": int(count * 0.18),  # 11건 (C등급)
        "caution": int(count * 0.20),  # 12건 (D등급)
        "warning": int(count * 0.17),  # 10건 (F등급)
    }

    test_cases = []
    durations = [15, 20, 30, 45]

    for scenario, cnt in scenario_counts.items():
        for i in range(cnt):
            seed = hash(f"bio_test_{scenario}_{i}") % (2**32)
            random.seed(seed)

            data = generate_biometric_data(scenario, seed)
            duration = random.choice(durations)
            routine = generate_routine(scenario, duration)

            test_case = {
                "id": f"BIO{len(test_cases)+1:03d}",
                "type": "biometric",
                "scenario": scenario,
                "input_data": data,
                "routine": {"duration_min": duration, "items": routine},
                "expected_health": generate_health_expected(data, scenario),
                "expected_exercise": generate_exercise_expected(
                    data, scenario, duration
                ),
            }

            test_cases.append(test_case)

    random.seed(42)
    random.shuffle(test_cases)

    return test_cases


def generate_chat_test_cases(count: int = 40) -> list:
    """챗봇 테스트 케이스 생성"""

    # 카테고리별 분배
    category_counts = {
        "sleep": int(count * 0.25),  # 10건
        "heart_rate": int(count * 0.25),  # 10건
        "exercise": int(count * 0.25),  # 10건
        "condition": int(count * 0.15),  # 6건
        "activity": int(count * 0.10),  # 4건
    }

    test_cases = []

    for category, cnt in category_counts.items():
        templates = CHAT_TEMPLATES[category]
        for i in range(cnt):
            template = templates[i % len(templates)]
            qa = generate_chat_question(category, template)

            test_case = {
                "id": f"CHAT{len(test_cases)+1:03d}",
                "type": "chat",
                "category": qa["category"],
                "input_data": {
                    "message": qa["question"],
                    "character": random.choice(
                        ["devil_coach", "angel_coach", "booster_coach"]
                    ),
                },
                "expected": qa["expected"],
            }

            test_cases.append(test_case)

    random.seed(42)
    random.shuffle(test_cases)

    return test_cases


def generate_all_test_data(bio_count: int = 60, chat_count: int = 40) -> dict:
    """전체 테스트 데이터 생성"""

    bio_cases = generate_biometric_test_cases(bio_count)
    chat_cases = generate_chat_test_cases(chat_count)

    return {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "version": "2.0",
            "description": "3단계 평가용 테스트 데이터 (Baseline/LangChain/Fine-tuned)",
            "total_count": bio_count + chat_count,
            "biometric_count": bio_count,
            "chat_count": chat_count,
        },
        "biometric_test_cases": bio_cases,
        "chat_test_cases": chat_cases,
    }


def save_test_data(data: dict, output_dir: str):
    """테스트 데이터 저장"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")

    # 통합 파일
    unified_file = output_path / f"test_data_unified_{timestamp}.json"
    with open(unified_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # baseline_runner.py 호환 파일들
    # 1. health_data.json (건강 분석용)
    health_data = {
        "metadata": data["metadata"],
        "test_cases": [
            {
                "id": tc["id"],
                "scenario": tc["scenario"],
                "difficulty": "medium",
                "input_data": tc["input_data"],
                "expected": tc["expected_health"],
            }
            for tc in data["biometric_test_cases"]
        ],
    }
    with open(output_path / "health_data.json", "w", encoding="utf-8") as f:
        json.dump(health_data, f, ensure_ascii=False, indent=2)

    # 2. exercise_data.json (운동 분석용)
    exercise_data = {
        "metadata": data["metadata"],
        "test_cases": [
            {
                "id": tc["id"],
                "scenario": tc["scenario"],
                "difficulty": "medium",
                "input_data": {**tc["input_data"], "routine": tc["routine"]},
                "expected": tc["expected_exercise"],
            }
            for tc in data["biometric_test_cases"]
        ],
    }
    with open(output_path / "exercise_data.json", "w", encoding="utf-8") as f:
        json.dump(exercise_data, f, ensure_ascii=False, indent=2)

    # 3. chat_queries.json (챗봇용)
    chat_data = {
        "metadata": data["metadata"],
        "test_cases": [
            {
                "id": tc["id"],
                "category": tc["category"],
                "difficulty": "medium",
                "input_data": tc["input_data"],
                "expected": tc["expected"],
            }
            for tc in data["chat_test_cases"]
        ],
    }
    with open(output_path / "chat_queries.json", "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)

    return {
        "unified": unified_file,
        "health": output_path / "health_data.json",
        "exercise": output_path / "exercise_data.json",
        "chat": output_path / "chat_queries.json",
    }


# ============================================================
# 메인 실행
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 3단계 평가용 테스트 데이터 생성")
    print("=" * 60)
    print()
    print("📋 구조:")
    print("   - 생체 데이터: 60건 (건강 분석 + 운동 분석)")
    print("   - 챗봇 질문: 40건")
    print("   - 총계: 100건")
    print()
    print("🎯 용도:")
    print("   - Baseline / LangChain / Fine-tuned 3단계 평가")
    print("   - 동일한 데이터로 단계별 개선 정도 비교")
    print()

    # 데이터 생성
    test_data = generate_all_test_data(bio_count=60, chat_count=40)

    # 저장
    output_dir = Path(__file__).parent / "datasets"
    files = save_test_data(test_data, output_dir)

    print("✅ 생성 완료!")
    print()
    print("📁 생성된 파일:")
    print(f"   - {files['unified']} (통합)")
    print(f"   - {files['health']} (건강 분석용)")
    print(f"   - {files['exercise']} (운동 분석용)")
    print(f"   - {files['chat']} (챗봇용)")
    print()

    # 시나리오별 분포 출력
    print("📊 생체 데이터 시나리오별 분포:")
    scenario_counts = {}
    for tc in test_data["biometric_test_cases"]:
        scenario = tc["scenario"]
        scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1
    for scenario, count in sorted(scenario_counts.items()):
        print(f"   - {scenario}: {count}건")

    print()
    print("📊 챗봇 카테고리별 분포:")
    category_counts = {}
    for tc in test_data["chat_test_cases"]:
        category = tc["category"]
        category_counts[category] = category_counts.get(category, 0) + 1
    for category, count in sorted(category_counts.items()):
        print(f"   - {category}: {count}건")

    # 샘플 출력
    print()
    print("=" * 60)
    print("📝 샘플 데이터:")
    print("=" * 60)

    print("\n[생체 데이터 샘플]")
    sample_bio = test_data["biometric_test_cases"][0]
    print(f"ID: {sample_bio['id']}")
    print(f"시나리오: {sample_bio['scenario']}")
    print(f"수면: {sample_bio['input_data']['sleep_hr']}시간")
    print(f"RHR: {sample_bio['input_data']['resting_heart_rate']}bpm")
    print(f"예상 등급: {sample_bio['expected_health']['condition_level']}")
    print(
        f"Buchheit 인용 필요: {sample_bio['expected_health']['should_cite_buchheit']}"
    )
    print(
        f"Milewski 인용 필요: {sample_bio['expected_health']['should_cite_milewski']}"
    )

    print("\n[챗봇 샘플]")
    sample_chat = test_data["chat_test_cases"][0]
    print(f"ID: {sample_chat['id']}")
    print(f"카테고리: {sample_chat['category']}")
    print(f"질문: {sample_chat['input_data']['message']}")
    print(f"키워드: {sample_chat['expected']['keywords']}")
