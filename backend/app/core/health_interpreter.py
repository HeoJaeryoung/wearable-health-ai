"""
Health Interpreter - LLM 분기 처리 버전

EVAL_MODE에 따라 분기 (모두 LLM 사용):
- baseline: OpenAI SDK + 수동 파싱 + 기존 프롬프트
- langchain: LangChain Chain + Structured Output + 강화 프롬프트
- finetuned: Azure Llama 3.1 8B Fine-tuned 모델
- 실패 시: 규칙 기반 Fallback
"""

import os
import json
import requests
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field


load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ===========================================
# 평가 모드 확인
# ===========================================
def get_eval_mode() -> str:
    """현재 평가 모드 반환"""
    return os.getenv("EVAL_MODE", "baseline")


# ============================================================
# Structured Output용 Pydantic 모델 (LangChain 모드용)
# ============================================================
class HealthScoreOutput(BaseModel):
    """건강 점수 스키마"""

    score: int = Field(description="건강 점수 0-100")
    grade: str = Field(description="등급 A/B+/B/C+/C/C-/D/F")
    grade_text: str = Field(description="등급 설명")
    factors: list[str] = Field(description="점수 산정 요인들")


class SleepAnalysisOutput(BaseModel):
    """수면 분석 스키마"""

    status: str = Field(description="상태: good/warning/critical/unknown")
    level: str = Field(description="상태 설명")
    message: str = Field(description="분석 메시지")
    recommendation: str = Field(description="권장 사항")


class ActivityAnalysisOutput(BaseModel):
    """활동량 분석 스키마"""

    activity_level: str = Field(description="활동 레벨")
    message: str = Field(description="분석 메시지")
    recommendation: str = Field(description="권장 사항")


class HeartRateAnalysisOutput(BaseModel):
    """심박수 분석 스키마"""

    fitness_level: str = Field(description="피트니스 레벨")
    message: str = Field(description="분석 메시지")


class ExerciseRecommendationOutput(BaseModel):
    """운동 권장 스키마"""

    recommended_level: str = Field(description="권장 강도: 상/중/하")
    intensity_score: float = Field(description="강도 점수 0.0-1.0")
    reasons: list[str] = Field(description="권장 이유들")


class HealthAnalysisResponse(BaseModel):
    """건강 분석 전체 응답 스키마"""

    health_score: HealthScoreOutput
    sleep: SleepAnalysisOutput
    activity: ActivityAnalysisOutput
    heart_rate: HeartRateAnalysisOutput
    exercise_recommendation: ExerciseRecommendationOutput


# ============================================================
# 유틸 함수
# ============================================================
def clean_json_text(text: str) -> str:
    """JSON 텍스트 정리"""
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    return text


def try_parse_json(text: str):
    """JSON 파싱 시도"""
    try:
        return json.loads(text)
    except Exception:
        return None


# ============================================================
# 공통 프롬프트
# ============================================================
def get_baseline_health_prompt() -> str:
    """Baseline용 건강 분석 프롬프트 (운동 추천 제외)"""
    return """당신은 10년 경력의 친근한 피트니스 트레이너입니다.
사용자의 생체 데이터를 보고, 친구에게 조언하듯 따뜻하고 상세하게 설명해주세요.
운동 추천은 하지 마세요. 순수하게 건강 데이터 해석에만 집중하세요.

## 톤 가이드
- 친근하고 격려하는 말투 사용 ("~해요", "~네요")
- 전문 용어 대신 쉬운 표현
- 부정적인 내용도 긍정적으로 표현
- 구체적인 수치를 언급하며 의미 설명

## 분석 기준

### 수면
- 7-9시간: 충분해요! 잘 주무셨네요
- 6-7시간: 괜찮지만 조금 더 주무시면 좋겠어요
- 5-6시간: 좀 부족해요, 피곤하실 수 있어요
- 5시간 미만: 많이 부족해요, 오늘은 무리하지 마세요

### 활동량
- 10,000보 이상: 정말 활발하게 움직이셨네요!
- 7,500-10,000보: 좋은 활동량이에요
- 5,000-7,500보: 적당히 움직이셨어요
- 3,000-5,000보: 조금 더 움직이면 좋겠어요
- 3,000보 미만: 오늘은 많이 앉아계셨나 봐요

### 심박수 (휴식기)
- 60-70bpm: 건강한 수준이에요
- 70-80bpm: 평균적인 수준이에요
- 80bpm 이상: 스트레스나 피로가 있을 수 있어요
- 데이터 없음: 측정되지 않았어요

## 응답 형식 (JSON)

⚠️ 매우 중요: 각 message는 반드시 3-4문장, 최소 80자 이상으로 상세하게 작성하세요!
짧은 한 문장은 절대 안됩니다.

{
    "health_score": {
        "score": 0-100,
        "grade": "A/B/C+/C/D/F",
        "grade_text": "등급 설명",
        "factors": ["점수에 영향을 준 요인들"]
    },
    "sleep": {
        "status": "good/fair/warning/critical/unknown",
        "level": "상태 레벨",
        "message": "3-4문장의 상세한 수면 분석. 반드시 80자 이상! 예시: '어젯밤 5.9시간 주무셨네요. 권장 수면 시간인 7-9시간보다 약 1-2시간 부족해요. 수면이 부족하면 낮에 피로감을 느끼거나 집중력이 떨어질 수 있어요. 가능하면 오늘 밤은 30분 일찍 잠자리에 드셔보는 건 어떨까요?'",
        "recommendation": "구체적인 개선 방안"
    },
    "activity": {
        "activity_level": "sedentary/low/moderate/active/very_active",
        "message": "3-4문장의 상세한 활동량 분석. 반드시 80자 이상! 예시: '오늘 1,034보 걸으셨네요. 권장 걸음수 10,000보의 약 10% 수준으로 많이 앉아계셨나 봐요. 장시간 앉아있으면 혈액순환이 잘 안되고 몸이 뻣뻣해질 수 있어요. 1시간마다 5분씩 일어나서 스트레칭하거나 짧게 걸어보세요!'",
        "recommendation": "구체적인 개선 방안"
    },
    "heart_rate": {
        "fitness_level": "athlete/excellent/good/average/below_average/poor/unknown",
        "message": "3-4문장의 상세한 심박수 분석. 반드시 80자 이상! 데이터가 없으면: '오늘 심박수 데이터가 측정되지 않았어요. 웨어러블 기기를 착용하고 계시다면 제대로 연결되어 있는지 확인해보세요. 심박수는 심폐 건강 상태를 파악하는 중요한 지표예요. 다음에는 측정된 데이터로 더 정확한 분석을 해드릴게요!'"
    },
    "exercise_recommendation": {
        "recommended_level": "상/중/하",
        "intensity_score": 0.0-1.0,
        "reasons": ["권장 강도 결정 이유들 (2-3개)"]
    }
}

⚠️ 필수 체크:
1. 각 message는 반드시 3-4문장, 80자 이상
2. 짧은 한 문장 응답은 절대 금지
3. 구체적인 수치와 그 의미를 설명
4. 친근하고 따뜻한 말투 유지
5. 운동 종류나 루틴은 절대 언급하지 않음"""


def get_enhanced_health_prompt() -> str:
    """LangChain/Finetuned용 강화 프롬프트"""
    return """당신은 건강 데이터 분석 전문가입니다.
사용자의 생체 데이터를 종합적으로 분석하여 건강 상태를 평가하세요.

## 평가 기준

### 수면 평가
- 7-9시간: 충분 (good)
- 6-7시간: 보통 (fair)
- 5-6시간: 부족 (warning)
- 5시간 미만: 심각 (critical)
- 9시간 초과: 과다 (over)

### 활동량 평가
- 10000보 이상: 매우 활발 (very_active)
- 7500-10000보: 활발 (active)
- 5000-7500보: 보통 (moderate)
- 3000-5000보: 부족 (low)
- 3000보 미만: 매우 부족 (sedentary)

### 심박수 평가 (휴식기 기준)
- 50bpm 미만: 운동선수 (athlete)
- 50-60bpm: 매우 우수 (excellent)
- 60-70bpm: 양호 (good)
- 70-80bpm: 평균 (average)
- 80-90bpm: 약간 높음 (below_average)
- 90bpm 이상: 높음 (poor)

### BMI 평가
- 18.5 미만: 저체중
- 18.5-23: 정상
- 23-25: 과체중
- 25 이상: 비만

## 건강 점수 기준 (0-100)
- 80점 이상: A등급 (매우 우수)
- 70-79점: B등급 (우수)
- 55-69점: C+등급 (보통 이상)
- 45-54점: C등급 (보통)
- 35-44점: D등급 (개선 필요)
- 35점 미만: F등급 (주의 필요)

## 운동 권장 강도
- 상: 건강 점수 70 이상, 수면 충분 → 고강도 가능
- 중: 건강 점수 50-69 → 중강도 권장
- 하: 건강 점수 50 미만 또는 수면 부족 → 저강도 권장"""


def get_user_health_prompt(raw: dict) -> str:
    """사용자 데이터 프롬프트"""
    sleep_hr = raw.get("sleep_hr", 0)
    steps = raw.get("steps", 0)
    heart_rate = raw.get("heart_rate", 0)
    resting_hr = raw.get("resting_heart_rate", 0)

    return f"""다음 건강 데이터를 상세하게 분석해주세요.

[오늘의 건강 데이터]
- 수면 시간: {sleep_hr}시간 (권장: 7-9시간)
- 걸음 수: {steps:,}보 (권장: 10,000보)
- 평균 심박수: {heart_rate}bpm
- 휴식기 심박수: {resting_hr}bpm (건강 기준: 60-70bpm)
- 활동 칼로리: {raw.get('active_calories', 0)}kcal
- BMI: {raw.get('bmi', 0)}
- 산소포화도: {raw.get('oxygen_saturation', 0)}%

각 항목에 대해 현재 수치가 건강에 어떤 의미를 갖는지, 
개선이 필요한 부분은 무엇인지 상세하게 분석해주세요.

JSON 형식으로만 응답하세요."""


# ============================================================
# 1) Baseline LLM 건강 분석 (OpenAI SDK + 수동 파싱)
# ============================================================
def interpret_health_data_baseline(raw: dict) -> dict:
    """Baseline: OpenAI SDK 직접 호출 + 수동 JSON 파싱"""
    from app.config import LLM_MODEL_MAIN, LLM_TEMPERATURE, LLM_MAX_TOKENS

    system_prompt = get_baseline_health_prompt()
    user_prompt = get_user_health_prompt(raw)

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL_MAIN,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
        )

        raw_text = resp.choices[0].message.content
        cleaned = clean_json_text(raw_text)
        parsed = try_parse_json(cleaned)

        if parsed:
            # BMI, 산소포화도는 규칙 기반으로 보완
            parsed["bmi"] = interpret_bmi(raw)
            parsed["oxygen"] = interpret_oxygen(raw)
            return parsed
        else:
            raise Exception("JSON 파싱 실패")

    except Exception as e:
        print(f"[ERROR] Baseline 건강 분석 실패: {e}")
        raise e


# ============================================================
# 2) LangChain LLM 건강 분석 (Chain + Structured Output)
# ============================================================
def interpret_health_data_langchain(raw: dict) -> dict:
    """LangChain: Chain + Structured Output으로 건강 분석"""
    from app.langchain.health_chain import HealthAnalysisChain

    try:
        # 체인 생성 및 빌드
        chain = HealthAnalysisChain()
        chain.build_chain()

        # 사용자 프롬프트 생성
        user_prompt = get_user_health_prompt(raw)

        # 체인 실행
        result = chain.chain.invoke({"user_prompt": user_prompt})

        # Pydantic 모델 → dict 변환
        if hasattr(result, "model_dump"):
            parsed = result.model_dump()
        elif hasattr(result, "dict"):
            parsed = result.dict()
        else:
            parsed = dict(result)

        # BMI, 산소포화도는 규칙 기반으로 보완
        parsed["bmi"] = interpret_bmi(raw)
        parsed["oxygen"] = interpret_oxygen(raw)

        return parsed

    except Exception as e:
        print(f"[ERROR] LangChain 건강 분석 실패: {e}")
        raise e


# ============================================================
# 3) Fine-tuned LLM 건강 분석 (Azure Llama)
# ============================================================
def interpret_health_data_finetuned(raw: dict) -> dict:
    """Fine-tuned: Azure Llama 3.1 8B 모델 호출"""
    from app.config import (
        FINETUNED_ENDPOINT,
        FINETUNED_API_KEY,
        LLM_TEMPERATURE,
        LLM_MAX_TOKENS,
    )

    if not FINETUNED_ENDPOINT or not FINETUNED_API_KEY:
        raise Exception("Fine-tuned 모델 설정이 없습니다. .env 파일을 확인하세요.")

    system_prompt = (
        get_enhanced_health_prompt()
        + """

## 응답 형식 (JSON만 출력)
{
    "health_score": {"score": 0-100, "grade": "등급", "grade_text": "설명", "factors": []},
    "sleep": {"status": "상태", "level": "레벨", "message": "메시지", "recommendation": "권장"},
    "activity": {"activity_level": "레벨", "message": "메시지", "recommendation": "권장"},
    "heart_rate": {"fitness_level": "레벨", "message": "메시지"},
    "exercise_recommendation": {"recommended_level": "상/중/하", "intensity_score": 0.0-1.0, "reasons": []}
}"""
    )

    user_prompt = get_user_health_prompt(raw)

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {FINETUNED_API_KEY}",
        }

        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": LLM_TEMPERATURE,
        }

        response = requests.post(
            f"{FINETUNED_ENDPOINT}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            raw_text = result["choices"][0]["message"]["content"]
            cleaned = clean_json_text(raw_text)
            parsed = try_parse_json(cleaned)

            if parsed:
                parsed["bmi"] = interpret_bmi(raw)
                parsed["oxygen"] = interpret_oxygen(raw)
                return parsed
            else:
                raise Exception("JSON 파싱 실패")
        else:
            raise Exception(f"API 오류: {response.status_code}")

    except Exception as e:
        print(f"[ERROR] Fine-tuned 건강 분석 실패: {e}")
        raise e


# ============================================================
# 규칙 기반 함수들 (Fallback용)
# ============================================================
def interpret_sleep(raw: dict) -> dict:
    """수면 상태 해석"""
    sleep_hr = raw.get("sleep_hr", 0)

    if sleep_hr <= 0:
        return {
            "status": "unknown",
            "level": "데이터 없음",
            "message": "수면 데이터가 기록되지 않았습니다.",
            "recommendation": "수면 추적을 활성화해주세요.",
        }

    if sleep_hr < 5:
        return {
            "status": "critical",
            "level": "심각한 수면 부족",
            "message": f"{sleep_hr:.1f}시간 수면은 매우 부족합니다.",
            "recommendation": "고강도 운동을 피하고 가벼운 스트레칭만 권장합니다.",
        }
    elif sleep_hr < 6:
        return {
            "status": "warning",
            "level": "수면 부족",
            "message": f"{sleep_hr:.1f}시간 수면으로 약간 부족합니다.",
            "recommendation": "중강도 운동을 권장하며, 무리하지 마세요.",
        }
    elif sleep_hr < 7:
        return {
            "status": "fair",
            "level": "보통",
            "message": f"{sleep_hr:.1f}시간 수면으로 괜찮은 편입니다.",
            "recommendation": "일반적인 운동 루틴을 수행할 수 있습니다.",
        }
    elif sleep_hr <= 9:
        return {
            "status": "good",
            "level": "충분한 수면",
            "message": f"{sleep_hr:.1f}시간의 충분한 수면을 취했습니다.",
            "recommendation": "컨디션이 좋으니 적극적인 운동이 가능합니다.",
        }
    else:
        return {
            "status": "over",
            "level": "과다 수면",
            "message": f"{sleep_hr:.1f}시간 수면은 다소 많습니다.",
            "recommendation": "가벼운 유산소로 몸을 깨워주세요.",
        }


def interpret_heart_rate(raw: dict) -> dict:
    """심박수 상태 해석"""
    hr = raw.get("heart_rate", 0)
    resting_hr = raw.get("resting_heart_rate", 0)

    result = {
        "avg_hr": hr,
        "resting_hr": resting_hr,
        "fitness_level": "unknown",
        "message": "",
    }

    if resting_hr <= 0 and hr <= 0:
        result["message"] = "심박수 데이터가 없습니다."
        return result

    check_hr = resting_hr if resting_hr > 0 else max(50, hr - 15)

    if check_hr < 50:
        result["fitness_level"] = "athlete"
        result["message"] = f"심박수 {check_hr}bpm은 운동선수 수준입니다."
    elif check_hr < 60:
        result["fitness_level"] = "excellent"
        result["message"] = f"심박수 {check_hr}bpm은 매우 건강한 수준입니다."
    elif check_hr < 70:
        result["fitness_level"] = "good"
        result["message"] = f"심박수 {check_hr}bpm은 양호한 수준입니다."
    elif check_hr < 80:
        result["fitness_level"] = "average"
        result["message"] = f"심박수 {check_hr}bpm은 평균 수준입니다."
    elif check_hr < 90:
        result["fitness_level"] = "below_average"
        result["message"] = f"심박수 {check_hr}bpm은 다소 높습니다."
    else:
        result["fitness_level"] = "poor"
        result["message"] = f"심박수 {check_hr}bpm은 높은 편입니다."

    return result


def interpret_activity(raw: dict) -> dict:
    """활동량 상태 해석"""
    steps = raw.get("steps", 0)

    if steps <= 0:
        return {
            "activity_level": "no_data",
            "message": "활동 데이터가 기록되지 않았습니다.",
            "recommendation": "",
        }
    elif steps < 3000:
        return {
            "activity_level": "sedentary",
            "message": f"오늘 {steps:,}보로 매우 적은 활동량입니다.",
            "recommendation": "전신 운동을 추천합니다.",
        }
    elif steps < 5000:
        return {
            "activity_level": "low",
            "message": f"오늘 {steps:,}보로 활동량이 부족합니다.",
            "recommendation": "유산소 운동을 추가하면 좋겠습니다.",
        }
    elif steps < 7500:
        return {
            "activity_level": "moderate",
            "message": f"오늘 {steps:,}보로 적당한 활동량입니다.",
            "recommendation": "균형 잡힌 운동 루틴이 적합합니다.",
        }
    elif steps < 10000:
        return {
            "activity_level": "active",
            "message": f"오늘 {steps:,}보로 활발한 하루입니다.",
            "recommendation": "근력 운동에 집중해도 좋습니다.",
        }
    else:
        return {
            "activity_level": "very_active",
            "message": f"오늘 {steps:,}보로 매우 활동적인 하루입니다!",
            "recommendation": "스트레칭과 회복에 집중하세요.",
        }


def interpret_bmi(raw: dict) -> dict:
    """BMI 상태 해석"""
    bmi = raw.get("bmi", 0)

    if bmi <= 0:
        return {"category": "unknown", "message": "BMI 데이터가 없습니다."}

    if bmi < 18.5:
        return {"category": "underweight", "message": f"BMI {bmi:.1f}로 저체중입니다."}
    elif bmi < 23:
        return {"category": "normal", "message": f"BMI {bmi:.1f}로 정상 체중입니다."}
    elif bmi < 25:
        return {"category": "overweight", "message": f"BMI {bmi:.1f}로 과체중입니다."}
    else:
        return {"category": "obese", "message": f"BMI {bmi:.1f}로 비만입니다."}


def interpret_oxygen(raw: dict) -> dict:
    """산소포화도 해석"""
    oxygen = raw.get("oxygen_saturation", 0)

    if oxygen <= 0:
        return {"status": "unknown", "message": "산소포화도 데이터가 없습니다."}
    elif oxygen >= 95:
        return {"status": "normal", "message": f"산소포화도 {oxygen}%로 정상입니다."}
    else:
        return {"status": "warning", "message": f"산소포화도 {oxygen}%로 낮습니다."}


def calculate_health_score(raw: dict) -> dict:
    """규칙 기반 건강 점수 계산"""
    score = 50
    factors = []

    sleep_hr = raw.get("sleep_hr", 0)
    if sleep_hr > 0:
        if 7 <= sleep_hr <= 9:
            score += 15
            factors.append("적정 수면 (+15)")
        elif 6 <= sleep_hr < 7:
            score += 10
            factors.append("양호한 수면 (+10)")
        elif sleep_hr < 5:
            score -= 10
            factors.append("수면 부족 (-10)")

    steps = raw.get("steps", 0)
    if steps > 0:
        if steps >= 10000:
            score += 15
            factors.append("활발한 활동량 (+15)")
        elif steps >= 7000:
            score += 10
            factors.append("좋은 활동량 (+10)")
        elif steps < 3000:
            score -= 5
            factors.append("낮은 활동량 (-5)")

    resting_hr = raw.get("resting_heart_rate", 0)
    if resting_hr > 0:
        if 50 <= resting_hr < 70:
            score += 10
            factors.append("건강한 심박수 (+10)")
        elif resting_hr >= 90:
            score -= 5
            factors.append("높은 심박수 (-5)")

    bmi = raw.get("bmi", 0)
    if bmi > 0:
        if 18.5 <= bmi < 23:
            score += 10
            factors.append("정상 BMI (+10)")
        elif bmi >= 25:
            score -= 5
            factors.append("높은 BMI (-5)")

    score = max(0, min(100, score))

    if score >= 80:
        grade, grade_text = "A", "매우 우수"
    elif score >= 70:
        grade, grade_text = "B", "우수"
    elif score >= 55:
        grade, grade_text = "C+", "보통 이상"
    elif score >= 45:
        grade, grade_text = "C", "보통"
    elif score >= 35:
        grade, grade_text = "D", "개선 필요"
    else:
        grade, grade_text = "F", "주의 필요"

    return {
        "score": score,
        "grade": grade,
        "grade_text": grade_text,
        "factors": factors,
    }


def recommend_exercise_intensity(raw: dict) -> dict:
    """규칙 기반 운동 강도 추천"""
    score_info = calculate_health_score(raw)
    score = score_info["score"]

    if score >= 70:
        return {
            "recommended_level": "상",
            "intensity_score": 0.9,
            "reasons": ["건강 점수 우수", "고강도 운동 가능"],
        }
    elif score >= 50:
        return {
            "recommended_level": "중",
            "intensity_score": 0.6,
            "reasons": ["건강 점수 보통", "중강도 운동 권장"],
        }
    else:
        return {
            "recommended_level": "하",
            "intensity_score": 0.3,
            "reasons": ["건강 점수 낮음", "저강도 운동 권장"],
        }


def interpret_health_data_rule_based(raw: dict) -> dict:
    """규칙 기반 건강 분석 (Fallback)"""
    return {
        "sleep": interpret_sleep(raw),
        "heart_rate": interpret_heart_rate(raw),
        "activity": interpret_activity(raw),
        "bmi": interpret_bmi(raw),
        "oxygen": interpret_oxygen(raw),
        "health_score": calculate_health_score(raw),
        "exercise_recommendation": recommend_exercise_intensity(raw),
    }


# ============================================================
# 메인 함수 (분기 처리) - 모두 LLM 사용
# ============================================================
def interpret_health_data(raw: dict) -> dict:
    """
    건강 데이터 종합 해석 (분기 처리)

    EVAL_MODE에 따라 (모두 LLM 사용):
    - baseline: OpenAI SDK + 수동 파싱 + 기존 프롬프트
    - langchain: LangChain Chain + Structured Output + 강화 프롬프트
    - finetuned: Azure Llama 3.1 8B + 강화 프롬프트
    - 실패 시: 규칙 기반 Fallback
    """
    eval_mode = get_eval_mode()

    try:
        if eval_mode == "baseline":
            print("[INFO] 건강 분석: Baseline (OpenAI SDK)")
            return interpret_health_data_baseline(raw)

        elif eval_mode == "langchain":
            print("[INFO] 건강 분석: LangChain (Structured Output)")
            return interpret_health_data_langchain(raw)

        elif eval_mode == "finetuned":
            print("[INFO] 건강 분석: Fine-tuned Llama")
            return interpret_health_data_finetuned(raw)

        else:
            print(f"[WARN] 알 수 없는 EVAL_MODE: {eval_mode}, Baseline 사용")
            return interpret_health_data_baseline(raw)

    except Exception as e:
        print(f"[WARN] LLM 건강 분석 실패 → 규칙 기반 Fallback: {e}")
        return interpret_health_data_rule_based(raw)


# ============================================================
# 기타 유틸 함수들 (기존 호환)
# ============================================================
def build_health_context_for_llm(raw: dict) -> str:
    """LLM 프롬프트에 포함할 건강 상태 컨텍스트 문자열 생성"""
    interpretation = interpret_health_data(raw)

    lines = []

    score_info = interpretation.get("health_score", {})
    lines.append(
        f"[종합 건강 점수] {score_info.get('score', 50)}점 ({score_info.get('grade', 'C')}등급)"
    )

    sleep_info = interpretation.get("sleep", {})
    if sleep_info.get("message"):
        lines.append(f"[수면] {sleep_info['message']}")

    activity_info = interpretation.get("activity", {})
    if activity_info.get("message"):
        lines.append(f"[활동량] {activity_info['message']}")

    hr_info = interpretation.get("heart_rate", {})
    if hr_info.get("message"):
        lines.append(f"[심박수] {hr_info['message']}")

    exercise_rec = interpretation.get("exercise_recommendation", {})
    lines.append(f"[권장 운동 강도] {exercise_rec.get('recommended_level', '중')}")

    return "\n".join(lines)


def build_analysis_text(
    raw: dict,
    difficulty_level: str,
    duration_min: int,
    item_count: int,
    total_time_sec: int,
) -> str:
    """규칙 기반 상세 분석 텍스트 생성"""
    health_info = interpret_health_data(raw)
    score_info = health_info.get("health_score", {})
    exercise_rec = health_info.get("exercise_recommendation", {})

    lines = []

    score = score_info.get("score", 50)
    grade = score_info.get("grade", "C")
    grade_text = score_info.get("grade_text", "보통")

    lines.append(f"📊 건강 점수: {score}점 ({grade}등급 - {grade_text})")

    rec_level = exercise_rec.get("recommended_level", difficulty_level)
    level_emoji = {"상": "🔥", "중": "💪", "하": "🌱"}.get(rec_level, "💪")

    lines.append(f"{level_emoji} 권장 운동 강도: {rec_level}")
    lines.append(
        f"🏃 오늘의 운동: 총 {item_count}개 운동, 약 {total_time_sec // 60}분 소요"
    )

    return "\n".join(lines)


def analyze_rag_patterns(similar_days: list) -> str:
    """RAG에서 가져온 과거 유사 패턴을 텍스트로 변환"""
    if not similar_days:
        return "📚 과거 유사 패턴 참고: 해당 없음"

    lines = ["📚 과거 유사 패턴 참고"]

    for day in similar_days[:3]:
        date = day.get("date", "날짜 미상")
        raw = day.get("raw", {}) or {}

        sleep = raw.get("sleep_hr", 0)
        steps = raw.get("steps", 0)

        parts = []
        if sleep > 0:
            parts.append(f"수면 {sleep:.1f}시간")
        if steps > 0:
            parts.append(f"걸음수 {steps:,}보")

        if parts:
            lines.append(f"- {date}: {', '.join(parts)}")

    return "\n".join(lines)
