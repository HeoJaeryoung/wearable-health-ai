"""
LLM Fine-tuning 학습 데이터 생성 스크립트 v2
카테고리 1: 건강 데이터 해석 (400건)

핵심 변경사항:
- 응답 길이 ~500자 → ~200자로 축소
- 판단 근거 명시적 포함
- 형식 일관성 강화
"""

import json
import random
from pathlib import Path

# ============================================================
# 시스템 프롬프트
# ============================================================

SYSTEM_PROMPT = """당신은 스포츠의학 전문가입니다. 웨어러블 생체 데이터를 분석하여 간결하고 명확한 건강 상태 평가를 제공합니다.

적용 기준:
- ACSM Guidelines for Exercise Testing and Prescription
- Buchheit (2014): 안정시 심박수 +10bpm 이상 상승 시 피로/과훈련 신호
- Milewski et al. (2014): 8시간 미만 수면 시 부상 위험 1.7배 증가

응답 형식:
1. 컨디션 등급과 점수
2. 핵심 판단 근거 (2-3개)
3. 오늘의 운동 권장사항
4. 관련 연구 인용 (해당 시)"""


# ============================================================
# 판단 기준 상수
# ============================================================

# RHR 변화 기준 (Buchheit, 2014)
RHR_THRESHOLDS = {
    "normal": 5,  # ±5bpm: 정상 변동
    "mild": 10,  # +5~10bpm: 경미한 피로
    "fatigue": 15,  # +10~15bpm: 급성 피로
    "danger": 20,  # +15bpm 이상: 과훈련/질병
}

# 수면 기준 (Milewski et al., 2014)
SLEEP_THRESHOLDS = {
    "excellent": 8.0,  # 8시간+: 충분
    "good": 7.0,  # 7-8시간: 양호
    "fair": 6.0,  # 6-7시간: 부족
    "poor": 5.0,  # 5-6시간: 매우 부족
    "danger": 4.0,  # 5시간 미만: 위험
}

# 걸음수 기준 (WHO Guidelines)
STEPS_THRESHOLDS = {"excellent": 10000, "good": 7000, "fair": 5000, "poor": 3000}

# 산소포화도 기준
SPO2_THRESHOLDS = {"normal": 95, "borderline": 93, "low": 90}

# 컨디션 등급 (실제 서비스 health_interpreter.py 기준 - 6등급)
CONDITION_GRADES = {
    "A": {
        "min": 80,
        "emoji": "✅",
        "label": "매우 우수",
        "exercise": "고강도 포함 모든 운동 가능",
        "scenario": "optimal",
    },
    "B": {
        "min": 70,
        "emoji": "✅",
        "label": "우수",
        "exercise": "중-고강도 운동 가능",
        "scenario": "good",
    },
    "C+": {
        "min": 55,
        "emoji": "⚠️",
        "label": "보통 이상",
        "exercise": "중강도까지 권장",
        "scenario": "moderate_plus",
    },
    "C": {
        "min": 45,
        "emoji": "⚠️",
        "label": "보통",
        "exercise": "중강도까지 권장",
        "scenario": "moderate",
    },
    "D": {
        "min": 35,
        "emoji": "⚠️",
        "label": "개선 필요",
        "exercise": "저강도만 권장",
        "scenario": "caution",
    },
    "F": {
        "min": 0,
        "emoji": "🚨",
        "label": "주의 필요",
        "exercise": "휴식 권장",
        "scenario": "warning",
    },
}


# ============================================================
# 판단 함수
# ============================================================


def assess_rhr(current: int, usual: int) -> dict:
    """안정시 심박수 변화 평가"""
    change = current - usual

    if change <= RHR_THRESHOLDS["normal"]:
        return {
            "status": "normal",
            "emoji": "✅",
            "label": "정상",
            "detail": f"평소 대비 +{change}bpm (정상 범위)",
            "cite": None,
        }
    elif change <= RHR_THRESHOLDS["mild"]:
        return {
            "status": "mild",
            "emoji": "⚠️",
            "label": "경미한 피로",
            "detail": f"평소 대비 +{change}bpm",
            "cite": None,
        }
    elif change <= RHR_THRESHOLDS["fatigue"]:
        return {
            "status": "fatigue",
            "emoji": "🚨",
            "label": "피로 신호",
            "detail": f"평소 대비 +{change}bpm → 급성 피로 신호",
            "cite": "Buchheit (2014)",
        }
    else:
        return {
            "status": "danger",
            "emoji": "🚨",
            "label": "위험",
            "detail": f"평소 대비 +{change}bpm → 과훈련/질병 의심",
            "cite": "Buchheit (2014)",
        }


def assess_sleep(hours: float) -> dict:
    """수면 시간 평가"""
    if hours >= SLEEP_THRESHOLDS["excellent"]:
        return {
            "status": "excellent",
            "emoji": "✅",
            "label": "충분",
            "detail": f"{hours}시간 (권장량 7-9시간 충족)",
            "cite": None,
        }
    elif hours >= SLEEP_THRESHOLDS["good"]:
        return {
            "status": "good",
            "emoji": "✅",
            "label": "양호",
            "detail": f"{hours}시간 (권장 범위)",
            "cite": None,
        }
    elif hours >= SLEEP_THRESHOLDS["fair"]:
        return {
            "status": "fair",
            "emoji": "⚠️",
            "label": "부족",
            "detail": f"{hours}시간 (권장량 미달)",
            "cite": None,
        }
    elif hours >= SLEEP_THRESHOLDS["poor"]:
        return {
            "status": "poor",
            "emoji": "🚨",
            "label": "매우 부족",
            "detail": f"{hours}시간 → 부상 위험 증가",
            "cite": "Milewski (2014)",
        }
    else:
        return {
            "status": "danger",
            "emoji": "🚨",
            "label": "위험",
            "detail": f"{hours}시간 → 부상 위험 1.7배 증가",
            "cite": "Milewski (2014)",
        }


def assess_steps(steps: int) -> dict:
    """걸음수 평가"""
    if steps >= STEPS_THRESHOLDS["excellent"]:
        return {
            "status": "excellent",
            "emoji": "✅",
            "label": "매우 활동적",
            "detail": f"{steps:,}보",
        }
    elif steps >= STEPS_THRESHOLDS["good"]:
        return {
            "status": "good",
            "emoji": "✅",
            "label": "활동적",
            "detail": f"{steps:,}보",
        }
    elif steps >= STEPS_THRESHOLDS["fair"]:
        return {
            "status": "fair",
            "emoji": "⚠️",
            "label": "보통",
            "detail": f"{steps:,}보",
        }
    else:
        return {
            "status": "poor",
            "emoji": "⚠️",
            "label": "부족",
            "detail": f"{steps:,}보 (좌식 생활)",
        }


def assess_spo2(spo2: int) -> dict:
    """산소포화도 평가"""
    if spo2 >= SPO2_THRESHOLDS["normal"]:
        return {
            "status": "normal",
            "emoji": "✅",
            "label": "정상",
            "detail": f"{spo2}%",
        }
    elif spo2 >= SPO2_THRESHOLDS["borderline"]:
        return {
            "status": "borderline",
            "emoji": "⚠️",
            "label": "경계",
            "detail": f"{spo2}% (모니터링 필요)",
        }
    else:
        return {
            "status": "low",
            "emoji": "🚨",
            "label": "낮음",
            "detail": f"{spo2}% (의료 상담 권장)",
        }


def calculate_condition_score(
    rhr_result: dict, sleep_result: dict, steps_result: dict, spo2_result: dict
) -> int:
    """컨디션 점수 계산 (0-100)"""
    score_map = {
        "excellent": 100,
        "good": 85,
        "normal": 80,
        "fair": 60,
        "mild": 55,
        "borderline": 50,
        "poor": 35,
        "fatigue": 30,
        "low": 25,
        "danger": 15,
    }

    rhr_score = score_map.get(rhr_result["status"], 50) * 0.30
    sleep_score = score_map.get(sleep_result["status"], 50) * 0.30
    steps_score = score_map.get(steps_result["status"], 50) * 0.25
    spo2_score = score_map.get(spo2_result["status"], 50) * 0.15

    return round(rhr_score + sleep_score + steps_score + spo2_score)


def get_condition_grade(score: int) -> dict:
    """점수 → 등급 변환"""
    for grade, config in CONDITION_GRADES.items():
        if score >= config["min"]:
            return {"grade": grade, **config}
    return {"grade": "F", **CONDITION_GRADES["F"]}


# ============================================================
# 응답 생성 (간소화된 형식)
# ============================================================


def generate_response(data: dict) -> str:
    """간소화된 건강 분석 응답 생성"""

    # 판단 수행
    rhr_result = assess_rhr(
        data["resting_heart_rate"], data["usual_resting_heart_rate"]
    )
    sleep_result = assess_sleep(data["sleep_hr"])
    steps_result = assess_steps(data["steps"])
    spo2_result = assess_spo2(data["oxygen_saturation"])

    # 컨디션 점수 및 등급
    score = calculate_condition_score(
        rhr_result, sleep_result, steps_result, spo2_result
    )
    grade_info = get_condition_grade(score)

    # 핵심 판단 근거 수집
    key_factors = []
    citations = []

    # 수면 (가장 중요)
    key_factors.append(f"- 수면 {sleep_result['detail']} {sleep_result['emoji']}")
    if sleep_result.get("cite"):
        citations.append(sleep_result["cite"])

    # RHR
    key_factors.append(
        f"- 안정시 심박 {data['resting_heart_rate']}bpm ({rhr_result['detail']}) {rhr_result['emoji']}"
    )
    if rhr_result.get("cite"):
        citations.append(rhr_result["cite"])

    # 활동량 (간략히)
    key_factors.append(f"- 활동량 {steps_result['detail']} {steps_result['emoji']}")

    # 산소포화도 (이상 시에만)
    if spo2_result["status"] != "normal":
        key_factors.append(
            f"- 산소포화도 {spo2_result['detail']} {spo2_result['emoji']}"
        )

    # 응답 조립
    response = f"""{grade_info['emoji']} **컨디션: {grade_info['label']}** ({score}/100)

**판단 근거:**
{chr(10).join(key_factors)}

💡 **오늘의 권장:** {grade_info['exercise']}"""

    # 인용 추가 (있을 경우)
    if citations:
        unique_citations = list(set(citations))
        response += f"\n\n📚 참고: {', '.join(unique_citations)}"

    return response


# ============================================================
# 사용자 입력 생성
# ============================================================


def generate_user_input(data: dict) -> str:
    """사용자 입력 텍스트 생성"""
    rhr_change = data["resting_heart_rate"] - data["usual_resting_heart_rate"]

    return f"""나이: {data['age']}세, 성별: {data['gender']}
heart_rate: {data['heart_rate']}bpm
resting_heart_rate: {data['resting_heart_rate']}bpm (평소 {data['usual_resting_heart_rate']}bpm, {rhr_change:+d})
sleep_hr: {data['sleep_hr']}시간
steps: {data['steps']:,}보
distance_km: {data['distance_km']}km
active_calories: {data['active_calories']}kcal
oxygen_saturation: {data['oxygen_saturation']}%
weight: {data['weight']}kg, bmi: {data['bmi']}"""


# ============================================================
# 시나리오별 데이터 생성
# ============================================================


def generate_raw_data(scenario: str, seed: int) -> dict:
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
        },
        "good": {
            "rhr_change": (3, 7),
            "sleep": (6.5, 7.5),
            "steps": (6000, 8500),
            "spo2": (96, 98),
        },
        "moderate": {
            "rhr_change": (5, 10),
            "sleep": (5.5, 6.5),
            "steps": (4000, 6500),
            "spo2": (95, 97),
        },
        "caution": {
            "rhr_change": (10, 15),
            "sleep": (4.5, 5.5),
            "steps": (2500, 4500),
            "spo2": (94, 96),
        },
        "warning": {
            "rhr_change": (15, 22),
            "sleep": (3.0, 4.5),
            "steps": (1000, 3000),
            "spo2": (92, 95),
        },
    }

    config = scenarios.get(scenario, scenarios["moderate"])

    rhr_change = random.randint(*config["rhr_change"])
    resting_hr = usual_rhr + rhr_change

    return {
        "age": age,
        "gender": gender,
        "heart_rate": resting_hr + random.randint(5, 20),
        "resting_heart_rate": resting_hr,
        "usual_resting_heart_rate": usual_rhr,
        "sleep_hr": round(random.uniform(*config["sleep"]), 1),
        "steps": random.randint(*config["steps"]),
        "distance_km": round(random.randint(*config["steps"]) / 1300, 2),
        "active_calories": random.randint(50, 500),
        "oxygen_saturation": random.randint(*config["spo2"]),
        "weight": weight,
        "bmi": bmi,
    }


# ============================================================
# 학습 데이터 생성
# ============================================================


def generate_training_data(total_count: int = 400) -> list:
    """학습 데이터 생성"""

    # 시나리오별 분배
    scenario_distribution = {
        "optimal": int(total_count * 0.15),  # 60건
        "good": int(total_count * 0.25),  # 100건
        "moderate": int(total_count * 0.25),  # 100건
        "caution": int(total_count * 0.20),  # 80건
        "warning": int(total_count * 0.15),  # 60건
    }

    training_data = []

    for scenario, count in scenario_distribution.items():
        for i in range(count):
            seed = hash(f"health_v2_{scenario}_{i}") % (2**32)
            raw_data = generate_raw_data(scenario, seed)

            user_input = generate_user_input(raw_data)
            response = generate_response(raw_data)

            training_sample = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": response},
                ]
            }

            training_data.append(training_sample)

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
    print("🚀 건강 분석 학습 데이터 생성 v2")
    print("=" * 60)
    print("📋 변경사항:")
    print("   - 응답 길이 ~500자 → ~200자")
    print("   - 판단 근거 명시적 포함")
    print("   - 전문 기준 인용 패턴화")
    print()

    # 데이터 생성
    training_data = generate_training_data(400)

    # 저장
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "health_interpretation_data_v2.jsonl"
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
