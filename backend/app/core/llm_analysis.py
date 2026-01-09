"""
LLM Analysis 책임
- “Python으로 계산 → Chain에 전달 → 결과 소비”
"""

import os
import json
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

from app.config import (
    LLM_MODEL_MAIN,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    EVAL_MODE,
    FINETUNED_ENDPOINT,
    FINETUNED_API_KEY,
    FINETUNED_MODEL_NAME,
)
from app.core.rag_query import (
    build_rag_query,
    classify_rag_strength,
)
from app.core.vector_store import search_similar_summaries
from app.core.health_interpreter import (
    interpret_health_data,
    build_health_context_for_llm,
    build_analysis_text,
    analyze_rag_patterns,
    recommend_exercise_intensity,
    calculate_health_score,
)

from app.langchain.exercise_chain import ExerciseAnalysisChain

_exercise_chain = ExerciseAnalysisChain()
_exercise_chain.build_chain()

load_dotenv()


# ==========================================================
# 체중 동적 추정
# ==========================================================
def estimate_weight(raw: dict) -> float:
    """
    체중 동적 추정 (우선순위)
    1. raw에서 직접 가져오기
    2. BMI + 키로 역산
    3. 키 기반 표준체중 계산
    4. 한국 성인 평균 (최후 수단)
    """
    weight = raw.get("weight", 0)
    if weight > 0:
        return float(weight)

    bmi = raw.get("bmi", 0)
    height_m = raw.get("height_m", 0)
    if bmi > 0 and height_m > 0:
        return round(bmi * (height_m**2), 1)

    height_cm = height_m * 100 if height_m > 0 else 0
    if height_cm > 0:
        return round((height_cm - 100) * 0.9, 1)

    return 65.0


# ==========================================================
# 건강 점수 기반 운동 설정 계산
# ==========================================================
def get_exercise_settings_by_score(score: int) -> dict:
    """
    건강 점수에 따른 운동 설정 반환

    등급별 칼로리 차이를 30~50kcal로 확대

    | 점수    | 등급 | 세트 | 운동시간 | MET    | 예상 칼로리 |
    |---------|------|------|----------|--------|-------------|
    | 80+     | A    | 5    | 50초     | 5.5-8  | ~200kcal    |
    | 70-79   | B    | 4-5  | 45초     | 5.0-6  | ~170kcal    |
    | 55-69   | C+   | 4    | 42초     | 4.5-5.5| ~145kcal    |
    | 45-54   | C    | 3    | 38초     | 4.0-4.5| ~115kcal    |
    | 35-44   | D    | 2    | 32초     | 3.0-3.8| ~85kcal     |
    | <35     | F    | 2    | 28초     | 2.5-3.2| ~70kcal     |
    """
    if score >= 80:
        return {
            "grade": "A",
            "intensity": "상",
            "base_sets": 5,
            "max_sets": 5,
            "rest_sec": 10,
            "met_min": 5.5,
            "met_max": 8.0,
            "duration_sec": 50,
            "calorie_multiplier": 1.0,
        }
    elif score >= 70:
        return {
            "grade": "B",
            "intensity": "중상",
            "base_sets": 4,
            "max_sets": 5,
            "rest_sec": 12,
            "met_min": 5.0,
            "met_max": 6.0,
            "duration_sec": 45,
            "calorie_multiplier": 1.0,
        }
    elif score >= 55:
        return {
            "grade": "C+",
            "intensity": "중",
            "base_sets": 4,
            "max_sets": 4,
            "rest_sec": 12,
            "met_min": 4.5,
            "met_max": 5.5,
            "duration_sec": 42,
            "calorie_multiplier": 1.0,
        }
    elif score >= 45:
        return {
            "grade": "C",
            "intensity": "중하",
            "base_sets": 3,
            "max_sets": 3,
            "rest_sec": 15,
            "met_min": 4.0,
            "met_max": 4.5,
            "duration_sec": 38,
            "calorie_multiplier": 1.0,
        }
    elif score >= 35:
        return {
            "grade": "D",
            "intensity": "하",
            "base_sets": 2,
            "max_sets": 2,
            "rest_sec": 18,
            "met_min": 3.0,
            "met_max": 3.8,
            "duration_sec": 32,
            "calorie_multiplier": 1.0,
        }
    else:
        return {
            "grade": "F",
            "intensity": "최하",
            "base_sets": 2,
            "max_sets": 2,
            "rest_sec": 20,
            "met_min": 2.5,
            "met_max": 3.2,
            "duration_sec": 28,
            "calorie_multiplier": 1.0,
        }


# ==========================================================
# 점수 기반 운동 풀 선택
# ==========================================================
def get_exercise_pool_by_score(score: int) -> list:
    """
    건강 점수에 따른 운동 풀 반환 (세분화)

    | 점수    | 운동 풀 구성                           |
    |---------|----------------------------------------|
    | 70+     | 저 + 중 + 고강도 전체                  |
    | 55-69   | 저 + 중강도 전체                       |
    | 45-54   | 저강도 + 중강도 일부 (MET 4.0-4.5)     |
    | 35-44   | 저강도만                               |
    | <35     | 최저강도만 (MET 3.5 이하)              |
    """

    # 최저강도 운동 (F등급, MET 3.5 이하)
    very_low_intensity = [
        {
            "exercise_name": "hip thrust",
            "category": [3, 2],
            "difficulty": 3,
            "met": 3.5,
        },
        {
            "exercise_name": "standing knee up",
            "category": [1, 3],
            "difficulty": 3,
            "met": 3.3,
        },
        {"exercise_name": "arm circle", "category": [1], "difficulty": 2, "met": 2.8},
        {
            "exercise_name": "shoulder stretch",
            "category": [1],
            "difficulty": 2,
            "met": 2.5,
        },
    ]

    low_intensity = [
        {
            "exercise_name": "standing knee up",
            "category": [1, 3],
            "difficulty": 3,
            "met": 3.8,
        },
        {
            "exercise_name": "hip thrust",
            "category": [3, 2],
            "difficulty": 3,
            "met": 3.5,
        },
        {
            "exercise_name": "standing side crunch",
            "category": [2, 3],
            "difficulty": 3,
            "met": 4.0,
        },
        {
            "exercise_name": "cross lunge",
            "category": [3, 2],
            "difficulty": 4,
            "met": 3.8,
        },
    ]

    mid_low_intensity = [
        {
            "exercise_name": "step forward dynamic lunge",
            "category": [3],
            "difficulty": 4,
            "met": 4.0,
        },
        {
            "exercise_name": "lying leg raise",
            "category": [3, 2],
            "difficulty": 4,
            "met": 4.0,
        },
        {"exercise_name": "crunch", "category": [2], "difficulty": 4, "met": 4.5},
        {
            "exercise_name": "scissor cross",
            "category": [2, 3],
            "difficulty": 4,
            "met": 4.5,
        },
        {
            "exercise_name": "Y-exercise",
            "category": [1, 2],
            "difficulty": 3,
            "met": 4.5,
        },
    ]

    mid_intensity = [
        {"exercise_name": "crunch", "category": [2], "difficulty": 4, "met": 4.5},
        {
            "exercise_name": "scissor cross",
            "category": [2, 3],
            "difficulty": 4,
            "met": 4.5,
        },
        {
            "exercise_name": "Y-exercise",
            "category": [1, 2],
            "difficulty": 3,
            "met": 4.5,
        },
        {
            "exercise_name": "knee push up",
            "category": [1, 2],
            "difficulty": 3,
            "met": 5.0,
        },
        {
            "exercise_name": "bicycle crunch",
            "category": [3, 2],
            "difficulty": 5,
            "met": 5.0,
        },
        {"exercise_name": "side lunge", "category": [3], "difficulty": 5, "met": 5.0},
        {
            "exercise_name": "good morning exercise",
            "category": [3],
            "difficulty": 5,
            "met": 5.0,
        },
    ]

    high_intensity = [
        {"exercise_name": "push up", "category": [1, 2], "difficulty": 4, "met": 6.0},
        {"exercise_name": "burpee test", "category": [4], "difficulty": 5, "met": 8.0},
        {"exercise_name": "plank", "category": [4], "difficulty": 5, "met": 8.0},
    ]

    if score >= 70:
        return low_intensity + mid_intensity + high_intensity
    elif score >= 55:
        return low_intensity + mid_intensity
    elif score >= 45:
        return low_intensity + mid_low_intensity
    elif score >= 35:
        return low_intensity
    else:
        return very_low_intensity


# ==========================================================
# 칼로리 계산 (동적)
# ==========================================================
def calculate_calories(
    avg_met: float, weight: float, duration_sec: int, multiplier: float = 1.0
) -> int:
    """
    칼로리 계산 공식 (MET 기반)

    공식: Calories = MET * 3.5 * Weight(kg) / 200 * Time(min)
    - MET: 운동 강도
    - 3.5: 산소 소비량 상수 (ml/kg/min)
    - 200: 칼로리 변환 상수
    - multiplier: 점수 기반 보정 계수
    """
    duration_min = duration_sec / 60
    base_calories = avg_met * 3.5 * weight / 200 * duration_min
    return int(base_calories * multiplier)


# ==========================================================
# 데이터 품질 확인
# ==========================================================
def check_data_quality(raw: dict) -> dict:
    has_sleep = raw.get("sleep_hr", 0) > 0
    has_activity = raw.get("steps", 0) > 0
    has_heart_rate = (
        raw.get("heart_rate", 0) > 0 or raw.get("resting_heart_rate", 0) > 0
    )
    has_body = raw.get("weight", 0) > 0 or raw.get("bmi", 0) > 0

    quality_score = sum([has_sleep, has_activity, has_heart_rate, has_body])

    return {
        "is_sufficient": has_sleep or has_activity,
        "has_sleep": has_sleep,
        "has_activity": has_activity,
        "has_heart_rate": has_heart_rate,
        "has_body": has_body,
        "quality_score": quality_score,
        "quality_level": (
            "high" if quality_score >= 3 else "medium" if quality_score >= 2 else "low"
        ),
    }


# ==========================================================
# SEED_JSON (17종 운동 목록)
# ==========================================================
SEED_JSON = """
[
  {"exercise_name": "standing side crunch", "category": [2, 3], "difficulty": 3, "met": 4.0},
  {"exercise_name": "standing knee up", "category": [1, 3], "difficulty": 3, "met": 3.8},
  {"exercise_name": "burpee test", "category": [4], "difficulty": 5, "met": 8.0},
  {"exercise_name": "step forward dynamic lunge", "category": [3], "difficulty": 4, "met": 4.0},
  {"exercise_name": "side lunge", "category": [3], "difficulty": 5, "met": 5.0},
  {"exercise_name": "cross lunge", "category": [3, 2], "difficulty": 4, "met": 3.8},
  {"exercise_name": "good morning exercise", "category": [3], "difficulty": 5, "met": 5.0},
  {"exercise_name": "lying leg raise", "category": [3, 2], "difficulty": 4, "met": 4.0},
  {"exercise_name": "crunch", "category": [2], "difficulty": 4, "met": 4.5},
  {"exercise_name": "bicycle crunch", "category": [3, 2], "difficulty": 5, "met": 5.0},
  {"exercise_name": "scissor cross", "category": [2, 3], "difficulty": 4, "met": 4.5},
  {"exercise_name": "hip thrust", "category": [3, 2], "difficulty": 3, "met": 3.5},
  {"exercise_name": "plank", "category": [4], "difficulty": 5, "met": 8.0},
  {"exercise_name": "push up", "category": [1, 2], "difficulty": 4, "met": 6.0},
  {"exercise_name": "knee push up", "category": [1, 2], "difficulty": 3, "met": 5.0},
  {"exercise_name": "Y-exercise", "category": [1, 2], "difficulty": 3, "met": 4.5}
]
"""

# ==========================================================
# 운동별 전문 지식 (트레이너 수준)
# ==========================================================
EXERCISE_KNOWLEDGE = {
    "standing side crunch": {
        "target": "외복사근, 복직근",
        "benefit": "코어 측면 강화, 허리 안정성 향상",
        "tip": "상체를 옆으로 구부릴 때 골반 고정 유지",
    },
    "standing knee up": {
        "target": "장요근, 복직근 하부",
        "benefit": "고관절 유연성 향상, 하복부 강화",
        "tip": "무릎을 높이 들어올릴수록 효과적",
    },
    "burpee test": {
        "target": "전신 (심폐 + 근력)",
        "benefit": "심폐지구력 향상, 전신 근력 강화",
        "tip": "동작 사이 쉬지 말고 연속 수행",
    },
    "step forward dynamic lunge": {
        "target": "대퇴사두근, 둔근",
        "benefit": "하체 근력 강화, 균형감각 향상",
        "tip": "앞무릎이 발끝을 넘지 않도록 주의",
    },
    "side lunge": {
        "target": "내전근, 대퇴사두근",
        "benefit": "내측 허벅지 강화, 고관절 가동성 향상",
        "tip": "이동하는 쪽 무릎 방향과 발끝 일치",
    },
    "cross lunge": {
        "target": "둔근, 대퇴사두근",
        "benefit": "둔근 활성화, 균형감각 향상",
        "tip": "뒤로 교차할 때 상체 수직 유지",
    },
    "good morning exercise": {
        "target": "척추기립근, 햄스트링",
        "benefit": "후면 사슬 강화, 자세 교정",
        "tip": "허리가 둥글어지지 않도록 복압 유지",
    },
    "lying leg raise": {
        "target": "복직근 하부, 장요근",
        "benefit": "하복부 집중 강화",
        "tip": "허리가 바닥에서 뜨지 않도록 주의",
    },
    "crunch": {
        "target": "복직근 상부",
        "benefit": "복근 기초 강화",
        "tip": "목이 아닌 복근으로 상체 들어올리기",
    },
    "bicycle crunch": {
        "target": "복직근, 외복사근",
        "benefit": "코어 전체 강화, 회전력 향상",
        "tip": "반대쪽 팔꿈치와 무릎이 만나도록",
    },
    "scissor cross": {
        "target": "복직근 하부, 내전근",
        "benefit": "하복부 강화, 고관절 유연성",
        "tip": "다리를 낮게 유지할수록 강도 증가",
    },
    "hip thrust": {
        "target": "둔근, 햄스트링",
        "benefit": "둔근 활성화, 골반 안정성",
        "tip": "정점에서 둔근 강하게 수축",
    },
    "plank": {
        "target": "코어 전체 (복근, 척추기립근)",
        "benefit": "코어 안정성, 전신 긴장 유지",
        "tip": "엉덩이가 처지거나 올라가지 않도록",
    },
    "push up": {
        "target": "대흉근, 삼두근, 전면 삼각근",
        "benefit": "상체 푸시 근력 강화",
        "tip": "몸 전체가 일직선 유지되도록",
    },
    "knee push up": {
        "target": "대흉근, 삼두근",
        "benefit": "푸시업 입문, 상체 기초 근력",
        "tip": "무릎부터 어깨까지 일직선 유지",
    },
    "Y-exercise": {
        "target": "승모근 하부, 후면 삼각근",
        "benefit": "어깨 안정성, 자세 교정",
        "tip": "엄지가 천장을 향하도록",
    },
}


# ==========================================================
# 메인 LLM 분석 함수 (하이브리드 버전)
# ==========================================================
def run_llm_analysis(
    summary: dict,
    user_id: str,
    difficulty_level: str,  # TODO: difficulty_level은 수동 강도 입력 비교 실험용으로 사용 예정
    duration_min: int,
) -> dict:
    """
    하이브리드 운동 분석 엔진

    구조:
    1. 루틴 생성: 규칙 기반 (Python) - 정확한 시간/칼로리 계산
    2. AI 분석: LLM - 건강 분석 참고 + 루틴에 대한 전문 트레이너 코멘트

    Fine-tuning 대상:
    - AI 분석 (analysis): 트레이너 수준 → 전문가 수준
    """
    eval_mode = os.environ.get("EVAL_MODE", "baseline")
    print(f"[INFO] 운동 추천 모드: {eval_mode}")

    raw = summary.get("raw", {})

    health_score_info = calculate_health_score(raw)
    score = health_score_info.get("score", 50)
    settings = get_exercise_settings_by_score(score)

    health_summary = {
        "score": score,
        "grade": settings["grade"],
        "recommended_intensity": settings["intensity"],
        "key_factors": health_score_info.get("factors", []),
        "data_quality": check_data_quality(raw),
    }

    # ============================================
    # 2) 규칙 기반 루틴 생성 (항상 Python으로)
    # ============================================
    routine_result = generate_rule_based_routine(score, duration_min, raw, settings)
    items = routine_result["items"]
    total_time_min = routine_result["total_time_min"]
    total_calories = routine_result["total_calories"]
    total_sec = routine_result["total_sec"]

    # ============================================
    # 3) 건강 분석 컨텍스트 준비
    # ============================================
    health_context = build_health_context_for_llm(raw)
    auto_intensity = settings["intensity"]
    weight = estimate_weight(raw)

    # RAG 검색
    rag_query = build_rag_query(raw)
    rag_result = search_similar_summaries(
        query_dict=rag_query,
        user_id=user_id,
        top_k=3,
    )
    similar_days = rag_result.get("similar_days", [])
    rag_strength = classify_rag_strength(similar_days)

    # ============================================
    # 4) LLM AI 분석 생성 (엔진 선택)
    # ============================================

    if eval_mode == "baseline":
        analysis_engine = generate_routine_analysis_baseline
    elif eval_mode == "langchain":
        analysis_engine = generate_routine_analysis_langchain
    elif eval_mode == "finetuned":
        analysis_engine = generate_routine_analysis_finetuned
    else:
        analysis_engine = generate_routine_analysis_baseline

    analysis = analysis_engine(
        health_summary,
        score,
        settings,
        items,
        health_context,
        rag_strength,
        weight,
    )

    # ============================================
    # 5) 결과 반환
    # ============================================
    return {
        "analysis": analysis,
        "ai_recommended_routine": {
            "total_time_min": total_time_min,
            "total_calories": total_calories,
            "items": items,
        },
        "used_data_ranked": {
            "primary": "health_score",
            "secondary": "rule_based_routine",
        },
        "health_context": {
            "health_score": health_score_info,
            "recommended_intensity": auto_intensity,
            "estimated_weight": weight,
            "data_quality": check_data_quality(raw),
        },
        "debug_info": {
            "health_score": score,
            "grade": settings["grade"],
            "intensity": settings["intensity"],
            "estimated_weight": weight,
            "total_exercise_sec": total_sec,
            "requested_time_min": duration_min,
            "actual_time_min": total_time_min,
            "routine_method": "rule_based",
            "analysis_method": eval_mode,
        },
    }


# ==========================================================
# 규칙 기반 루틴 생성 함수
# ==========================================================
def generate_rule_based_routine(
    score: int, duration_min: int, raw: dict, settings: dict
) -> dict:
    """
    규칙 기반 운동 루틴 생성 (정확한 시간/칼로리 계산)
    """
    exercise_pool = get_exercise_pool_by_score(score)

    met_min = settings["met_min"]
    met_max = settings["met_max"]
    filtered_pool = [ex for ex in exercise_pool if met_min <= ex["met"] <= met_max]

    if not filtered_pool:
        filtered_pool = sorted(
            exercise_pool, key=lambda x: abs(x["met"] - (met_min + met_max) / 2)
        )[:4]

    target_seconds = duration_min * 60
    base_sets = settings["base_sets"]
    duration_sec = settings["duration_sec"]
    rest_sec = settings["rest_sec"]

    items = []
    total_sec = 0
    idx = 0
    max_iterations = 20

    while total_sec < target_seconds * 0.80 and idx < max_iterations:
        ex = filtered_pool[idx % len(filtered_pool)]
        sets = base_sets

        item_time = (duration_sec * sets) + (rest_sec * (sets - 1))

        if total_sec + item_time > target_seconds * 1.2:
            remaining = target_seconds - total_sec
            adjusted_sets = max(2, int(remaining / (duration_sec + rest_sec)))
            if adjusted_sets >= 2:
                sets = adjusted_sets
                item_time = (duration_sec * sets) + (rest_sec * (sets - 1))
            else:
                break

        items.append(
            {
                "exercise_name": ex["exercise_name"],
                "category": ex["category"],
                "difficulty": ex["difficulty"],
                "met": ex["met"],
                "duration_sec": duration_sec,
                "rest_sec": rest_sec,
                "set_count": sets,
                "reps": None,
            }
        )

        total_sec += item_time
        idx += 1

    weight = estimate_weight(raw)
    avg_met = sum(item["met"] for item in items) / max(len(items), 1)
    total_calories = calculate_calories(
        avg_met=avg_met,
        weight=weight,
        duration_sec=total_sec,
        multiplier=settings["calorie_multiplier"],
    )

    actual_time_min = round(total_sec / 60)

    return {
        "items": items,
        "total_time_min": actual_time_min,
        "total_calories": total_calories,
        "total_sec": total_sec,
    }


# ==========================================================
# AI 분석 생성 - Baseline (OpenAI SDK, 전문 트레이너 수준)
# ==========================================================
def generate_routine_analysis_baseline(
    health_summary: dict,
    score: int,
    settings: dict,
    items: list,
    health_context: str,
    rag_strength: str,
    weight: float,
) -> str:
    """
    Baseline: OpenAI SDK 직접 호출
    역할:
    - 이미 계산된 건강 요약과 규칙 기반 루틴을 바탕으로
    - '왜 이 루틴이 적합한지'를 전문 트레이너 관점에서 설명

    주의:
    - 건강 상태 재판단 ❌
    - 운동 강도 재결정 ❌
    """

    print("[INFO] AI 분석: Baseline (전문 트레이너 수준)")

    # -------------------------------------------------
    # 1) 운동 목록 정리 (설명용)
    # -------------------------------------------------
    exercise_details = []
    for i, item in enumerate(items, 1):
        ex_name = item["exercise_name"]
        knowledge = EXERCISE_KNOWLEDGE.get(ex_name, {})

        exercise_details.append(
            f"{i}. {ex_name}\n"
            f"   - 구성: {item['set_count']}세트 × {item['duration_sec']}초\n"
            f"   - 휴식: {item['rest_sec']}초\n"
            f"   - 강도(MET): {item['met']}\n"
            f"   - 타겟근육: {knowledge.get('target', '전신')}\n"
            f"   - 기대효과: {knowledge.get('benefit', '전반적인 체력 향상')}"
        )
    exercise_block = "\n".join(exercise_details)

    # -------------------------------------------------
    # 2) 건강 요약 (LLM 입력용, 판단 금지)
    # -------------------------------------------------
    key_factors = health_summary.get("key_factors", [])
    data_quality = health_summary.get("data_quality", {})

    health_status_text = (
        "\n".join(f"- {factor}" for factor in key_factors)
        if key_factors
        else "- 건강 데이터가 제한적이므로 보수적으로 분석되었습니다."
    )

    rag_note = (
        "과거 유사한 건강 패턴이 확인되었습니다."
        if rag_strength == "strong"
        else "과거 유사 패턴 정보는 제한적입니다."
    )

    # -------------------------------------------------
    # 3) 프롬프트 구성
    # -------------------------------------------------

    system_prompt = """당신은 10년 경력의 전문 피트니스 트레이너입니다.

## 중요 규칙:
- 건강 상태, 운동 강도, 루틴 구성은 이미 결정되었습니다.
- 이를 다시 판단하거나 수정하지 마십시오.
- 당신의 역할은 '왜 이 루틴이 현재 상태에 적합한지'를 설명하는 것입니다.

## 코멘트 구성 (4-5문장)

1. 현재 건강 상태와 운동 강도의 연결 설명 (1문장)
2. 주요 운동 선택 이유와 기대 효과 (2문장)
3. 실행 시 주의사항 또는 효과를 높이는 팁 (1~2문장)

## 톤
- 전문적이되 이해하기 쉬운 설명
- 트레이너 관점의 실용적인 조언
"""

    user_prompt = f"""[사용자 건강 상태]
[건강 요약]
- 건강 점수: {health_summary['score']}점 ({health_summary['grade']} 등급)
- 권장 강도: {health_summary['recommended_intensity']}
- 데이터 품질: {data_quality.get('quality_level', 'unknown')}

주요 건강 요인:
{health_status_text}

[추가 건강 컨텍스트]
(이 정보는 참고용이며, 판단을 변경하지 않습니다)
{health_context}


참고 정보:
- {rag_note}

[추천된 운동 루틴]
총 {len(items)}개 운동으로 구성된 약 {settings['duration_sec']}초 단위 루틴

{exercise_block}

---
위 정보를 바탕으로, 전문 트레이너 관점에서 이 루틴에 대한 종합 코멘트를 작성해주세요.
"""


# ==========================================================
# AI 분석 생성 - LangChain (전문 트레이너 수준)
# ==========================================================
def generate_routine_analysis_langchain(
    health_summary: dict,
    score: int,
    settings: dict,
    items: list,
    health_context: str,
    rag_strength: str,
    weight: float,
) -> str:
    print("[INFO] AI 분석: LangChain (트레이너 수준)")

    analysis_text = _exercise_chain.run(
        health_summary=health_summary,
        score=score,
        settings=settings,
        items=items,
        health_context=health_context,
        rag_strength=rag_strength,
        weight=weight,
    )

    return analysis_text or ""


# ==========================================================
# AI 분석 생성 - Fine-tuned (전문가 수준)
# ==========================================================
def generate_routine_analysis_finetuned(
    health_summary: dict,
    score: int,
    settings: dict,
    items: list,
    health_context: str,
    rag_strength: str,
    weight: float,
) -> str:
    """
    Fine-tuned: Azure Llama 3.1 8B
    전문가 수준의 루틴 코멘트 생성

    Fine-tuning 후 기대 효과:
    - 운동생리학적 근거 포함
    - 각 운동의 타겟 근육, 효과, 주의사항 상세 설명
    - 개인 건강 상태에 맞춘 전문적 조언
    - 의학적 용어와 근거 기반 설명
    """
    print(f"[INFO] AI 분석: Fine-tuned (전문가 수준)")

    # TODO: Fine-tuned 모델 구현
    return generate_routine_analysis_baseline(
        health_summary, score, settings, items, health_context, rag_strength, weight
    )


# ==========================================================
# 헬퍼 함수들
# ==========================================================
def get_health_analysis_context(raw: dict) -> str:
    return build_health_context_for_llm(raw)


def get_health_score(raw: dict) -> dict:
    return calculate_health_score(raw)


# ==========================================================
# Structured Output용 Pydantic 모델
# ==========================================================
# class ExerciseItem(BaseModel):
#     """운동 항목 스키마"""

#     exercise_name: str = Field(description="운동 이름")
#     category: list[int] = Field(description="운동 카테고리 [1:상체, 2:코어, 3:하체]")
#     difficulty: int = Field(description="난이도 1-5")
#     met: float = Field(description="MET 값")
#     duration_sec: int = Field(description="운동 시간(초) 30-60")
#     rest_sec: int = Field(description="휴식 시간(초)")
#     set_count: int = Field(description="세트 수")
#     reps: Optional[int] = Field(default=None, description="반복 횟수")


# class ExerciseRoutine(BaseModel):
#     """운동 루틴 스키마"""

#     total_time_min: int = Field(description="총 운동 시간(분)")
#     total_calories: int = Field(description="예상 소모 칼로리")
#     items: list[ExerciseItem] = Field(description="운동 항목 리스트")


# class UsedDataRanked(BaseModel):
#     """사용된 데이터 우선순위 스키마"""

#     primary: str = Field(description="주요 데이터")
#     secondary: str = Field(description="보조 데이터")


# class LLMAnalysisResponse(BaseModel):
#     """LLM 분석 응답 스키마"""

#     analysis: str = Field(description="건강 상태 분석 (3-4문장)")
#     ai_recommended_routine: ExerciseRoutine = Field(description="추천 운동 루틴")
#     used_data_ranked: UsedDataRanked = Field(description="사용된 데이터 우선순위")
