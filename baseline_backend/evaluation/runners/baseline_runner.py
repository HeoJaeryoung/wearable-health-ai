"""
Baseline 평가 실행기
3개 서비스(건강분석, 운동추천, 챗봇) 모두 평가

서비스별 호출 방식:
- 건강 분석: interpret_health_data() 직접 호출 (생체 데이터 입력)
- 운동 추천: run_llm_analysis() 직접 호출 (생체 데이터 + 옵션 입력)
- 챗봇: /api/chat API 호출 (질문 텍스트 입력) + RAG 검색

챗봇 RAG 테스트를 위해:
- 테스트 시작 전 샘플 건강 데이터를 ChromaDB에 저장
- 테스트 종료 후 샘플 데이터 삭제
"""

import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
import sys

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evaluation.config import API_BASE_URL, TEST_USER_ID, EVALUATION_ROUNDS, RESULTS_DIR
from evaluation.metrics.response_quality import ResponseQualityMetrics
from evaluation.metrics.performance import PerformanceMetrics
from evaluation.metrics.rag_quality import RAGQualityMetrics


# ============================================
# 테스트용 샘플 건강 데이터 (7일치)
# ============================================
SAMPLE_HEALTH_DATA = [
    {
        "date_offset": 0,  # 오늘
        "raw": {
            "heart_rate": 72,
            "resting_heart_rate": 62,
            "sleep_hr": 7.5,
            "steps": 8500,
            "distance_km": 6.2,
            "active_calories": 380,
            "oxygen_saturation": 97,
            "weight": 72.0,
            "bmi": 23.5,
        },
    },
    {
        "date_offset": -1,  # 어제
        "raw": {
            "heart_rate": 68,
            "resting_heart_rate": 60,
            "sleep_hr": 8.0,
            "steps": 10200,
            "distance_km": 7.8,
            "active_calories": 450,
            "oxygen_saturation": 98,
            "weight": 71.8,
            "bmi": 23.4,
        },
    },
    {
        "date_offset": -2,
        "raw": {
            "heart_rate": 75,
            "resting_heart_rate": 65,
            "sleep_hr": 6.5,
            "steps": 6000,
            "distance_km": 4.5,
            "active_calories": 280,
            "oxygen_saturation": 96,
            "weight": 72.2,
            "bmi": 23.6,
        },
    },
    {
        "date_offset": -3,
        "raw": {
            "heart_rate": 70,
            "resting_heart_rate": 61,
            "sleep_hr": 7.8,
            "steps": 9000,
            "distance_km": 6.8,
            "active_calories": 400,
            "oxygen_saturation": 97,
            "weight": 72.0,
            "bmi": 23.5,
        },
    },
    {
        "date_offset": -4,
        "raw": {
            "heart_rate": 78,
            "resting_heart_rate": 68,
            "sleep_hr": 5.5,
            "steps": 4500,
            "distance_km": 3.2,
            "active_calories": 200,
            "oxygen_saturation": 95,
            "weight": 72.5,
            "bmi": 23.7,
        },
    },
    {
        "date_offset": -5,
        "raw": {
            "heart_rate": 65,
            "resting_heart_rate": 58,
            "sleep_hr": 8.5,
            "steps": 12000,
            "distance_km": 9.0,
            "active_calories": 520,
            "oxygen_saturation": 98,
            "weight": 71.5,
            "bmi": 23.3,
        },
    },
    {
        "date_offset": -6,
        "raw": {
            "heart_rate": 73,
            "resting_heart_rate": 63,
            "sleep_hr": 7.0,
            "steps": 7500,
            "distance_km": 5.5,
            "active_calories": 340,
            "oxygen_saturation": 97,
            "weight": 72.0,
            "bmi": 23.5,
        },
    },
]


class BaselineRunner:

    def __init__(self):
        self.base_url = API_BASE_URL
        self.user_id = TEST_USER_ID
        self.results = {"health": [], "exercise": [], "chat": []}
        self.summary = {}
        self.test_data_ids = []  # 저장된 테스트 데이터 ID 추적

        # 서비스 모듈 로드 (건강 분석, 운동 추천, 벡터 저장소)
        self._load_service_modules()

    def _load_service_modules(self):
        """서비스 모듈 동적 로드"""
        try:
            from app.core.health_interpreter import (
                interpret_health_data,
                build_health_context_for_llm,
            )

            self.interpret_health_data = interpret_health_data
            self.build_health_context_for_llm = build_health_context_for_llm
            print("✅ health_interpreter 모듈 로드 성공")
        except ImportError as e:
            print(f"⚠️ health_interpreter 모듈 로드 실패: {e}")
            self.interpret_health_data = None
            self.build_health_context_for_llm = None

        try:
            from app.core.llm_analysis import run_llm_analysis

            self.run_llm_analysis = run_llm_analysis
            print("✅ llm_analysis 모듈 로드 성공")
        except ImportError as e:
            print(f"⚠️ llm_analysis 모듈 로드 실패: {e}")
            self.run_llm_analysis = None

        try:
            from app.core.vector_store import save_daily_summary, collection

            self.save_daily_summary = save_daily_summary
            self.chroma_collection = collection
            print("✅ vector_store 모듈 로드 성공")
        except ImportError as e:
            print(f"⚠️ vector_store 모듈 로드 실패: {e}")
            self.save_daily_summary = None
            self.chroma_collection = None

    # ============================================
    # 테스트 데이터 Setup / Cleanup
    # ============================================

    def setup_test_data(self):
        """
        테스트용 샘플 건강 데이터를 ChromaDB에 저장
        챗봇 RAG 테스트를 위해 필요
        """
        if self.save_daily_summary is None:
            print("⚠️ vector_store 모듈이 없어서 테스트 데이터 설정 불가")
            return False

        print("\n📦 테스트용 샘플 데이터 설정 중...")

        today = datetime.now()
        self.test_data_ids = []

        for sample in SAMPLE_HEALTH_DATA:
            # 날짜 계산
            target_date = today + timedelta(days=sample["date_offset"])
            date_str = target_date.strftime("%Y-%m-%d")

            # summary 형식으로 변환
            summary = {
                "created_at": f"{date_str}T12:00:00",
                "platform": "test_evaluation",
                "raw": sample["raw"],
            }

            try:
                result = self.save_daily_summary(
                    summary=summary, user_id=self.user_id, source="test_eval"
                )
                doc_id = result.get("document_id")
                if doc_id:
                    self.test_data_ids.append(doc_id)
                print(f"   ✅ {date_str} 데이터 저장 완료")
            except Exception as e:
                print(f"   ❌ {date_str} 데이터 저장 실패: {e}")

        print(f"📦 총 {len(self.test_data_ids)}개 샘플 데이터 저장 완료\n")
        return True

    def cleanup_test_data(self):
        """
        테스트 후 샘플 데이터 삭제
        """
        if self.chroma_collection is None:
            print("⚠️ ChromaDB collection이 없어서 정리 불가")
            return False

        if not self.test_data_ids:
            print("ℹ️ 삭제할 테스트 데이터 없음")
            return True

        print("\n🧹 테스트 데이터 정리 중...")

        try:
            self.chroma_collection.delete(ids=self.test_data_ids)
            print(f"🧹 {len(self.test_data_ids)}개 테스트 데이터 삭제 완료\n")
            self.test_data_ids = []
            return True
        except Exception as e:
            print(f"❌ 테스트 데이터 삭제 실패: {e}")
            return False

    def run_all(
        self, datasets_dir: str = "evaluation/datasets", cleanup: bool = False
    ) -> dict:
        """
        모든 서비스 평가 실행

        Args:
            datasets_dir: 테스트 데이터셋 경로
            cleanup: 테스트 후 샘플 데이터 삭제 여부 (기본 False - 후속 테스트 위해 유지)
        """
        print("=" * 60)
        print("🚀 Baseline 평가 시작")
        print("=" * 60)

        # 0. 테스트용 샘플 데이터 설정 (챗봇 RAG용)
        self.setup_test_data()

        datasets_path = Path(datasets_dir)

        # 1. 건강 분석 평가 (생체 데이터 입력)
        health_path = datasets_path / "health_data.json"
        if health_path.exists():
            print("\n📊 건강 분석 평가 중...")
            self.results["health"] = self._run_health_evaluation(health_path)
            print(f"   완료: {len(self.results['health'])}건")
        else:
            print(f"\n⚠️ 건강 분석 데이터 없음: {health_path}")

        # 2. 운동 추천 평가 (생체 데이터 + 옵션 입력)
        exercise_path = datasets_path / "exercise_data.json"
        if exercise_path.exists():
            print("\n🏃 운동 추천 평가 중...")
            self.results["exercise"] = self._run_exercise_evaluation(exercise_path)
            print(f"   완료: {len(self.results['exercise'])}건")
        else:
            print(f"\n⚠️ 운동 추천 데이터 없음: {exercise_path}")

        # 3. 챗봇 평가 (질문 텍스트 입력)
        chat_path = datasets_path / "chat_queries.json"
        if chat_path.exists():
            print("\n💬 챗봇 평가 중...")
            self.results["chat"] = self._run_chat_evaluation(chat_path)
            print(f"   완료: {len(self.results['chat'])}건")
        else:
            print(f"\n⚠️ 챗봇 데이터 없음: {chat_path}")

        # 요약 생성
        self.summary = self._generate_summary()

        # 테스트 데이터 정리 (선택)
        if cleanup:
            self.cleanup_test_data()

        return {"results": self.results, "summary": self.summary}

    # ============================================
    # 건강 분석 평가 (생체 데이터 → interpret_health_data)
    # ============================================

    def _run_health_evaluation(self, dataset_path: Path) -> list:
        """
        건강 분석 테스트 실행
        입력: 생체 데이터 (9개 지표)
        호출: interpret_health_data() 직접 호출
        """
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        results = []

        for test_case in dataset.get("test_cases", []):
            result = self._evaluate_health_analysis(test_case)
            results.append(result)

        return results

    def _evaluate_health_analysis(self, test_case: dict) -> dict:
        """단일 건강 분석 평가"""
        result = {
            "id": test_case["id"],
            "difficulty": test_case.get("difficulty", "medium"),
            "input_data": test_case["input_data"],
            "expected": test_case["expected"],
            "responses": [],
            "times": [],
            "scores": {},
        }

        input_data = test_case["input_data"]
        expected = test_case["expected"]

        # 여러 번 실행 (일관성 측정)
        for _ in range(EVALUATION_ROUNDS):
            response, elapsed = self._call_health_interpreter(input_data)
            result["responses"].append(response)
            result["times"].append(elapsed)

        # 응답을 문자열로 변환 (딕셔너리인 경우)
        first_response = result["responses"][0]
        if isinstance(first_response, dict):
            response_text = json.dumps(first_response, ensure_ascii=False)
        else:
            response_text = str(first_response)

        # 점수 계산
        expected_keywords = expected.get("keywords", [])

        result["scores"] = {
            "accuracy": self._calculate_health_accuracy(first_response, expected),
            "keyword_match": ResponseQualityMetrics.keyword_match_score(
                response_text, expected_keywords
            ),
            "consistency": self._calculate_dict_consistency(result["responses"]),
            "condition_match": self._check_condition_match(first_response, expected),
            "avg_time": PerformanceMetrics.calculate_stats(result["times"])["avg"],
            "avg_tokens": PerformanceMetrics.estimate_tokens(response_text),
        }

        return result

    def _call_health_interpreter(self, input_data: dict) -> tuple:
        """건강 분석 모듈 직접 호출"""
        start = datetime.now()

        if self.interpret_health_data is None:
            elapsed = (datetime.now() - start).total_seconds()
            return {"error": "health_interpreter 모듈 로드 실패"}, elapsed

        try:
            result = self.interpret_health_data(input_data)
            elapsed = (datetime.now() - start).total_seconds()
            return result, elapsed
        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            return {"error": str(e)}, elapsed

    def _calculate_health_accuracy(self, response: dict, expected: dict) -> float:
        """건강 분석 정확도 계산"""
        if isinstance(response, dict) and "error" in response:
            return 0.0

        score = 0
        total = 0

        # 컨디션 레벨 매칭 (40점)
        total += 40
        expected_level = expected.get("condition_level", "")
        if isinstance(response, dict):
            # health_score 기반 컨디션 판정
            health_score = response.get("health_score", {})
            actual_score = (
                health_score.get("score", 50) if isinstance(health_score, dict) else 50
            )

            # 점수 → 컨디션 레벨 매핑
            if actual_score >= 80:
                actual_level = "optimal"
            elif actual_score >= 60:
                actual_level = "good"
            else:
                actual_level = "warning"

            if actual_level == expected_level:
                score += 40
            elif actual_level in ["optimal", "good"] and expected_level in [
                "optimal",
                "good",
            ]:
                score += 20  # 부분 점수

        # 운동 강도 권장 매칭 (30점)
        total += 30
        expected_exercise = expected.get("exercise_recommendation", "")
        if isinstance(response, dict):
            exercise_rec = response.get("exercise_recommendation", {})
            if isinstance(exercise_rec, dict):
                rec_level = exercise_rec.get("recommended_level", "")
                if "고강도" in expected_exercise and rec_level in ["고", "상"]:
                    score += 30
                elif "중강도" in expected_exercise and rec_level in ["중", "중상"]:
                    score += 30
                elif "저강도" in expected_exercise and rec_level in ["하", "저"]:
                    score += 30
                elif "휴식" in expected_exercise and rec_level in ["휴식", "하"]:
                    score += 30

        # 키워드 포함 (30점)
        total += 30
        expected_keywords = expected.get("keywords", [])
        if expected_keywords:
            response_text = (
                json.dumps(response, ensure_ascii=False)
                if isinstance(response, dict)
                else str(response)
            )
            matched = sum(1 for kw in expected_keywords if kw in response_text)
            score += (matched / len(expected_keywords)) * 30

        return round((score / total) * 100, 1) if total > 0 else 0.0

    def _check_condition_match(self, response: dict, expected: dict) -> bool:
        """컨디션 레벨 일치 여부"""
        if not isinstance(response, dict) or "error" in response:
            return False

        expected_level = expected.get("condition_level", "")
        health_score = response.get("health_score", {})
        actual_score = (
            health_score.get("score", 50) if isinstance(health_score, dict) else 50
        )

        if actual_score >= 80:
            actual_level = "optimal"
        elif actual_score >= 60:
            actual_level = "good"
        else:
            actual_level = "warning"

        return actual_level == expected_level

    def _calculate_dict_consistency(self, responses: list) -> float:
        """딕셔너리 응답들의 일관성 계산"""
        if len(responses) < 2:
            return 1.0

        # 첫 번째 응답과 나머지 비교
        first = responses[0]
        if not isinstance(first, dict):
            return ResponseQualityMetrics.consistency_score([str(r) for r in responses])

        consistent_count = 0
        for resp in responses[1:]:
            if isinstance(resp, dict):
                # 주요 키의 값이 일치하는지 확인
                first_score = (
                    first.get("health_score", {}).get("score", 0)
                    if isinstance(first.get("health_score"), dict)
                    else 0
                )
                resp_score = (
                    resp.get("health_score", {}).get("score", 0)
                    if isinstance(resp.get("health_score"), dict)
                    else 0
                )

                # 점수 차이가 5 이내면 일관성 있음
                if abs(first_score - resp_score) <= 5:
                    consistent_count += 1

        return consistent_count / (len(responses) - 1)

    # ============================================
    # 운동 추천 평가 (생체 데이터 + 옵션 → run_llm_analysis)
    # ============================================

    def _run_exercise_evaluation(self, dataset_path: Path) -> list:
        """
        운동 추천 테스트 실행
        입력: 생체 데이터 + 난이도/시간 옵션
        호출: run_llm_analysis() 직접 호출
        """
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        results = []

        for test_case in dataset.get("test_cases", []):
            result = self._evaluate_exercise_recommendation(test_case)
            results.append(result)

        return results

    def _evaluate_exercise_recommendation(self, test_case: dict) -> dict:
        """단일 운동 추천 평가"""
        result = {
            "id": test_case["id"],
            "difficulty": test_case.get("difficulty", "medium"),
            "input_data": test_case["input_data"],
            "options": test_case.get("options", {}),
            "expected": test_case["expected"],
            "responses": [],
            "times": [],
            "scores": {},
        }

        input_data = test_case["input_data"]
        options = test_case.get("options", {"difficulty": "중", "duration_min": 30})
        expected = test_case["expected"]

        # 여러 번 실행 (일관성 측정)
        for _ in range(EVALUATION_ROUNDS):
            response, elapsed = self._call_llm_analysis(input_data, options)
            result["responses"].append(response)
            result["times"].append(elapsed)

        # 응답을 문자열로 변환
        first_response = result["responses"][0]
        if isinstance(first_response, dict):
            response_text = json.dumps(first_response, ensure_ascii=False)
        else:
            response_text = str(first_response)

        # Fallback 상세 정보 추출
        fallback_info = self._get_fallback_info(first_response)

        # 점수 계산
        expected_keywords = expected.get("keywords", [])

        result["scores"] = {
            "accuracy": self._calculate_exercise_accuracy(first_response, expected),
            "keyword_match": ResponseQualityMetrics.keyword_match_score(
                response_text, expected_keywords
            ),
            "consistency": self._calculate_dict_consistency(result["responses"]),
            "has_warmup": self._check_has_warmup(first_response),
            "has_cooldown": self._check_has_cooldown(first_response),
            "intensity_match": self._check_intensity_match(first_response, expected),
            "used_fallback": fallback_info["used_fallback"],
            "fallback_reason": fallback_info["reason"],
            "avg_time": PerformanceMetrics.calculate_stats(result["times"])["avg"],
            "avg_tokens": PerformanceMetrics.estimate_tokens(response_text),
        }

        return result

    def _call_llm_analysis(self, input_data: dict, options: dict) -> tuple:
        """운동 추천 모듈 직접 호출"""
        start = datetime.now()

        if self.run_llm_analysis is None:
            elapsed = (datetime.now() - start).total_seconds()
            return {"error": "llm_analysis 모듈 로드 실패"}, elapsed

        try:
            # run_llm_analysis 호출
            result = self.run_llm_analysis(
                user_id=self.user_id,
                summary={"raw": input_data},
                difficulty_level=options.get("difficulty", "중"),
                duration_min=options.get("duration_min", 30),
            )
            elapsed = (datetime.now() - start).total_seconds()
            return result, elapsed
        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            return {"error": str(e)}, elapsed

    def _calculate_exercise_accuracy(self, response: dict, expected: dict) -> float:
        """운동 추천 정확도 계산"""
        if isinstance(response, dict) and "error" in response:
            return 0.0

        score = 0
        total = 0

        # 루틴 존재 여부 (20점)
        total += 20
        if isinstance(response, dict):
            routine = response.get("ai_recommended_routine", {})
            if routine and routine.get("items"):
                score += 20

        # 워밍업 포함 (20점)
        total += 20
        if expected.get("has_warmup", True):
            if self._check_has_warmup(response):
                score += 20

        # 쿨다운 포함 (20점)
        total += 20
        if expected.get("has_cooldown", True):
            if self._check_has_cooldown(response):
                score += 20

        # 강도 매칭 (20점)
        total += 20
        if self._check_intensity_match(response, expected):
            score += 20

        # 키워드 포함 (20점)
        total += 20
        expected_keywords = expected.get("keywords", [])
        if expected_keywords:
            response_text = (
                json.dumps(response, ensure_ascii=False)
                if isinstance(response, dict)
                else str(response)
            )
            matched = sum(1 for kw in expected_keywords if kw in response_text)
            score += (matched / len(expected_keywords)) * 20

        return round((score / total) * 100, 1) if total > 0 else 0.0

    def _check_has_warmup(self, response: dict) -> bool:
        """워밍업 포함 여부"""
        if not isinstance(response, dict):
            return False

        response_text = json.dumps(response, ensure_ascii=False).lower()
        warmup_keywords = ["워밍업", "warm", "준비", "스트레칭"]
        return any(kw in response_text for kw in warmup_keywords)

    def _check_has_cooldown(self, response: dict) -> bool:
        """쿨다운 포함 여부"""
        if not isinstance(response, dict):
            return False

        response_text = json.dumps(response, ensure_ascii=False).lower()
        cooldown_keywords = ["쿨다운", "cool", "마무리", "정리"]
        return any(kw in response_text for kw in cooldown_keywords)

    def _check_intensity_match(self, response: dict, expected: dict) -> bool:
        """운동 강도 매칭 여부"""
        if not isinstance(response, dict):
            return False

        expected_intensity = expected.get("intensity_level", "")
        response_text = json.dumps(response, ensure_ascii=False)

        if "저강도" in expected_intensity:
            return (
                "하" in response_text
                or "저" in response_text
                or "가벼운" in response_text
            )
        elif "중강도" in expected_intensity or "중-고강도" in expected_intensity:
            return "중" in response_text
        elif "고강도" in expected_intensity:
            return "상" in response_text or "고" in response_text

        return True  # 기본값

    def _get_fallback_info(self, response: dict) -> dict:
        """
        Fallback 상세 정보 추출

        Returns:
            {
                "used_fallback": bool,
                "reason": str  # "none", "low_score", "validation_failed", "parse_failed", "data_insufficient", "error"
            }
        """
        if not isinstance(response, dict):
            return {"used_fallback": False, "reason": "none"}

        # health_context에서 fallback_reason 확인
        health_context = response.get("health_context", {})
        fallback_reason = health_context.get("fallback_reason", "")

        if fallback_reason:
            # 사유 분류
            if (
                "점수" in fallback_reason
                or "40점" in fallback_reason
                or "미만" in fallback_reason
            ):
                return {"used_fallback": True, "reason": "low_score"}
            elif (
                "검증 실패" in fallback_reason
                or "validation" in fallback_reason.lower()
            ):
                return {"used_fallback": True, "reason": "validation_failed"}
            elif (
                "파싱" in fallback_reason
                or "JSON" in fallback_reason
                or "parse" in fallback_reason.lower()
            ):
                return {"used_fallback": True, "reason": "parse_failed"}
            elif "데이터" in fallback_reason or "부족" in fallback_reason:
                return {"used_fallback": True, "reason": "data_insufficient"}
            elif "오류" in fallback_reason or "error" in fallback_reason.lower():
                return {"used_fallback": True, "reason": "error"}
            else:
                return {"used_fallback": True, "reason": "other"}

        # used_data_ranked에서 확인
        used_data = response.get("used_data_ranked", {})
        primary = used_data.get("primary", "")
        if "fallback" in primary.lower() or "rule" in primary.lower():
            return {"used_fallback": True, "reason": "unknown"}

        # debug_info 확인 (Fallback에만 존재)
        if response.get("debug_info"):
            return {"used_fallback": True, "reason": "unknown"}

        # LLM 성공
        return {"used_fallback": False, "reason": "none"}

    def _check_used_fallback(self, response: dict) -> bool:
        """Fallback 사용 여부 (간단 버전)"""
        return self._get_fallback_info(response)["used_fallback"]

    # ============================================
    # 챗봇 평가 (질문 텍스트 → /api/chat API)
    # ============================================

    def _run_chat_evaluation(self, dataset_path: Path) -> list:
        """
        챗봇 대화 테스트 실행
        입력: 질문 텍스트 + 캐릭터
        호출: /api/chat API
        """
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        results = []

        for test_case in dataset.get("test_cases", []):
            result = self._evaluate_chat(test_case)
            results.append(result)

        return results

    def _evaluate_chat(self, test_case: dict) -> dict:
        """단일 챗봇 평가"""
        result = {
            "id": test_case["id"],
            "difficulty": test_case.get("difficulty", "medium"),
            "input_data": test_case["input_data"],
            "expected": test_case["expected"],
            "responses": [],
            "times": [],
            "scores": {},
        }

        input_data = test_case["input_data"]
        message = input_data.get("message", "")
        character = input_data.get("character", "devil_coach")
        expected = test_case["expected"]

        # 여러 번 실행 (일관성 측정)
        for _ in range(EVALUATION_ROUNDS):
            response, elapsed = self._call_chat_api(message, character)
            result["responses"].append(response)
            result["times"].append(elapsed)

        # 점수 계산
        expected_keywords = expected.get("keywords", [])
        first_response = result["responses"][0]

        result["scores"] = {
            "accuracy": self._calculate_chat_accuracy(
                first_response, expected, character
            ),
            "keyword_match": ResponseQualityMetrics.keyword_match_score(
                first_response, expected_keywords
            ),
            "consistency": ResponseQualityMetrics.consistency_score(
                result["responses"]
            ),
            "length_score": ResponseQualityMetrics.response_length_score(
                first_response
            ),
            "tone_match": self._check_tone_match(first_response, expected, character),
            "rag_utilization": self._check_rag_utilization(first_response),
            "avg_time": PerformanceMetrics.calculate_stats(result["times"])["avg"],
            "avg_tokens": PerformanceMetrics.estimate_tokens(first_response),
        }

        return result

    def _check_rag_utilization(self, response: str) -> float:
        """
        RAG 활용도 측정
        응답에 건강 데이터 관련 구체적 수치나 날짜가 포함되어 있는지 확인
        """
        if response.startswith("Error:"):
            return 0.0

        score = 0.0

        # 1. 수치 언급 (30점)
        import re

        numbers = re.findall(r"\d+\.?\d*", response)
        if len(numbers) >= 2:
            score += 0.3
        elif len(numbers) >= 1:
            score += 0.15

        # 2. 건강 관련 키워드 (30점)
        health_keywords = [
            "수면",
            "걸음",
            "심박",
            "칼로리",
            "운동",
            "컨디션",
            "체중",
            "산소",
        ]
        matched = sum(1 for kw in health_keywords if kw in response)
        score += min(0.3, matched * 0.1)

        # 3. 시간/날짜 언급 (20점)
        time_keywords = ["오늘", "어제", "최근", "지난", "이번 주", "일주일"]
        if any(kw in response for kw in time_keywords):
            score += 0.2

        # 4. 개인화된 조언 (20점)
        personalized_keywords = ["당신", "회원님", "데이터", "기록", "분석"]
        if any(kw in response for kw in personalized_keywords):
            score += 0.2

        return round(score, 2)

    def _call_chat_api(self, message: str, character: str = "devil_coach") -> tuple:
        """챗봇 API 호출"""
        url = f"{self.base_url}/api/chat"
        payload = {
            "user_id": self.user_id,
            "message": message,
            "character": character,
        }

        start = datetime.now()
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            elapsed = (datetime.now() - start).total_seconds()
            return result.get("response", ""), elapsed
        except requests.exceptions.ConnectionError:
            elapsed = (datetime.now() - start).total_seconds()
            return (
                "Error: 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.",
                elapsed,
            )
        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            return f"Error: {str(e)}", elapsed

    def _calculate_chat_accuracy(
        self, response: str, expected: dict, character: str
    ) -> float:
        """챗봇 응답 정확도 계산"""
        if response.startswith("Error:"):
            return 0.0

        score = 0
        total = 0

        # 키워드 매칭 (50점)
        total += 50
        expected_keywords = expected.get("keywords", [])
        if expected_keywords:
            matched = sum(1 for kw in expected_keywords if kw in response)
            score += (matched / len(expected_keywords)) * 50

        # 톤 매칭 (30점)
        total += 30
        if self._check_tone_match(response, expected, character):
            score += 30

        # 응답 길이 적절성 (20점)
        total += 20
        length_score = ResponseQualityMetrics.response_length_score(response)
        score += length_score * 20

        return round((score / total) * 100, 1) if total > 0 else 0.0

    def _check_tone_match(self, response: str, expected: dict, character: str) -> bool:
        """페르소나 톤 매칭 여부"""
        expected_tone = expected.get("tone", "")

        # 캐릭터별 톤 키워드
        tone_keywords = {
            "devil_coach": {
                "tough_love": ["해야지", "변명", "핑계", "당장", "뭐해", "게으름"]
            },
            "angel_coach": {
                "supportive": ["잘했어", "대단해", "멋져", "최고", "훌륭", "응원"]
            },
            "booster_coach": {
                "encouraging": ["할 수 있어", "파이팅", "믿어", "괜찮아", "힘내"]
            },
        }

        character_tones = tone_keywords.get(character, {})
        keywords = character_tones.get(expected_tone, [])

        if not keywords:
            return True  # 키워드 없으면 통과

        return any(kw in response for kw in keywords)

    # ============================================
    # 요약 및 저장
    # ============================================

    def _generate_summary(self) -> dict:
        """요약 통계 생성"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "stage": "baseline",
            "total_queries": 0,
            "by_service": {},
        }

        for service, results in self.results.items():
            if not results:
                continue

            service_summary = {
                "count": len(results),
                "avg_accuracy": 0,
                "avg_keyword_match": 0,
                "avg_consistency": 0,
                "avg_time": 0,
                "avg_tokens": 0,
                "by_difficulty": {},
            }

            if results:
                service_summary["avg_accuracy"] = round(
                    sum(r["scores"]["accuracy"] for r in results) / len(results), 2
                )
                service_summary["avg_keyword_match"] = round(
                    sum(r["scores"]["keyword_match"] for r in results) / len(results), 4
                )
                service_summary["avg_consistency"] = round(
                    sum(r["scores"]["consistency"] for r in results) / len(results), 4
                )
                service_summary["avg_time"] = round(
                    sum(r["scores"]["avg_time"] for r in results) / len(results), 4
                )
                service_summary["avg_tokens"] = round(
                    sum(r["scores"]["avg_tokens"] for r in results) / len(results), 0
                )

                # RAG 활용도 (챗봇만)
                if service == "chat":
                    rag_scores = [
                        r["scores"].get("rag_utilization", 0) for r in results
                    ]
                    if rag_scores:
                        service_summary["avg_rag_utilization"] = round(
                            sum(rag_scores) / len(rag_scores), 4
                        )

                # Fallback 비율 (운동 추천만)
                if service == "exercise":
                    # Fallback 사유별 집계
                    fallback_by_reason = {
                        "low_score": 0,
                        "validation_failed": 0,
                        "parse_failed": 0,
                        "data_insufficient": 0,
                        "error": 0,
                        "other": 0,
                    }

                    llm_results = []
                    fallback_results = []

                    for r in results:
                        if r["scores"].get("used_fallback", False):
                            reason = r["scores"].get("fallback_reason", "other")
                            if reason in fallback_by_reason:
                                fallback_by_reason[reason] += 1
                            else:
                                fallback_by_reason["other"] += 1
                            fallback_results.append(r)
                        else:
                            llm_results.append(r)

                    fallback_count = len(fallback_results)
                    llm_count = len(llm_results)

                    service_summary["fallback_rate"] = (
                        round(fallback_count / len(results), 4) if results else 0
                    )
                    service_summary["fallback_count"] = fallback_count
                    service_summary["llm_count"] = llm_count
                    service_summary["fallback_by_reason"] = {
                        k: v for k, v in fallback_by_reason.items() if v > 0
                    }

                    # LLM만 사용한 케이스 정확도
                    if llm_results:
                        service_summary["llm_accuracy"] = round(
                            sum(r["scores"]["accuracy"] for r in llm_results)
                            / len(llm_results),
                            2,
                        )
                    else:
                        service_summary["llm_accuracy"] = None

                    # Fallback 케이스 정확도
                    if fallback_results:
                        service_summary["fallback_accuracy"] = round(
                            sum(r["scores"]["accuracy"] for r in fallback_results)
                            / len(fallback_results),
                            2,
                        )
                    else:
                        service_summary["fallback_accuracy"] = None

                # 난이도별 통계
                for difficulty in ["easy", "medium", "hard"]:
                    diff_results = [r for r in results if r["difficulty"] == difficulty]
                    if diff_results:
                        service_summary["by_difficulty"][difficulty] = {
                            "count": len(diff_results),
                            "avg_accuracy": round(
                                sum(r["scores"]["accuracy"] for r in diff_results)
                                / len(diff_results),
                                2,
                            ),
                        }

            summary["by_service"][service] = service_summary
            summary["total_queries"] += service_summary["count"]

        # 전체 평균
        all_results = (
            self.results["health"] + self.results["exercise"] + self.results["chat"]
        )
        if all_results:
            summary["overall"] = {
                "avg_accuracy": round(
                    sum(r["scores"]["accuracy"] for r in all_results)
                    / len(all_results),
                    2,
                ),
                "avg_time": round(
                    sum(r["scores"]["avg_time"] for r in all_results)
                    / len(all_results),
                    4,
                ),
                "avg_tokens": round(
                    sum(r["scores"]["avg_tokens"] for r in all_results)
                    / len(all_results),
                    0,
                ),
            }

        return summary

    def save_results(self, output_dir: str = None) -> Path:
        """결과 저장"""
        if output_dir is None:
            output_dir = f"{RESULTS_DIR}/baseline"

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_dir) / f"results_{timestamp}.json"

        output_data = {
            "metadata": {
                "stage": "baseline",
                "timestamp": datetime.now().isoformat(),
                "api_base_url": self.base_url,
                "evaluation_rounds": EVALUATION_ROUNDS,
            },
            "summary": self.summary,
            "results": self.results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 결과 저장: {output_path}")
        return output_path

    def print_summary(self):
        """요약 출력"""
        print("\n" + "=" * 60)
        print("📊 Baseline 평가 요약")
        print("=" * 60)

        print(f"\n총 테스트: {self.summary.get('total_queries', 0)}건")

        for service, stats in self.summary.get("by_service", {}).items():
            service_name = {
                "health": "건강 분석",
                "exercise": "운동 추천",
                "chat": "챗봇",
            }.get(service, service)

            print(f"\n[{service_name}] ({stats['count']}건)")
            print(f"   정확도: {stats['avg_accuracy']:.1f}%")
            print(f"   키워드 매칭: {stats['avg_keyword_match']:.2f}")
            print(f"   일관성: {stats['avg_consistency']:.2f}")
            print(f"   응답 시간: {stats['avg_time']:.2f}초")
            print(f"   평균 토큰: {stats['avg_tokens']:.0f}")

            # 난이도별 정확도
            if stats.get("by_difficulty"):
                print(f"   난이도별 정확도:")
                for diff, diff_stats in stats["by_difficulty"].items():
                    diff_name = {
                        "easy": "쉬움",
                        "medium": "보통",
                        "hard": "어려움",
                    }.get(diff, diff)
                    print(
                        f"      - {diff_name}: {diff_stats['avg_accuracy']:.1f}% ({diff_stats['count']}건)"
                    )

            # RAG 활용도 (챗봇만)
            if "avg_rag_utilization" in stats:
                print(f"   RAG 활용도: {stats['avg_rag_utilization']:.2f}")

            # Fallback 비율 (운동 추천만)
            if "fallback_rate" in stats:
                print(
                    f"   Fallback 비율: {stats['fallback_rate']*100:.1f}% ({stats['fallback_count']}건 Fallback / {stats['llm_count']}건 LLM)"
                )

                # 사유별 상세
                if stats.get("fallback_by_reason"):
                    print(f"   Fallback 사유:")
                    reason_names = {
                        "low_score": "점수 낮음 (개선 불가)",
                        "validation_failed": "검증 실패 (개선 가능)",
                        "parse_failed": "파싱 실패 (개선 가능)",
                        "data_insufficient": "데이터 부족",
                        "error": "오류 발생",
                        "other": "기타",
                    }
                    for reason, count in stats["fallback_by_reason"].items():
                        reason_name = reason_names.get(reason, reason)
                        print(f"      - {reason_name}: {count}건")

                # LLM vs Fallback 정확도 비교
                if stats.get("llm_accuracy") is not None:
                    print(f"   LLM 정확도: {stats['llm_accuracy']:.1f}%")
                if stats.get("fallback_accuracy") is not None:
                    print(f"   Fallback 정확도: {stats['fallback_accuracy']:.1f}%")

        if "overall" in self.summary:
            print(f"\n[전체 평균]")
            print(f"   정확도: {self.summary['overall']['avg_accuracy']:.1f}%")
            print(f"   응답 시간: {self.summary['overall']['avg_time']:.2f}초")
            print(f"   평균 토큰: {self.summary['overall']['avg_tokens']:.0f}")


if __name__ == "__main__":
    runner = BaselineRunner()
    runner.run_all()
    runner.print_summary()
    runner.save_results()
