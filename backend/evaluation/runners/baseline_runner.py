"""
Baseline 평가 실행기 v2.1
- 실행: python -m evaluation.runners.baseline_runner
- 파일 저장: evaluation/results/baseline/

v2.1 변경사항:
- 논문 인용 측정 분리:
  - citation_strict: 저자명 직접 인용 (Fine-tuning 효과 측정)
  - concept_application: 전문 개념 적용 (프롬프트 품질 측정)
- 운동 분석 함수 호출 인자 수정

v2 변경사항:
- 6등급 컨디션 기준 적용 (실제 서비스 health_interpreter.py 기준)
- 새 평가 지표 추가:
  - 응답 구조 일치율 (has_condition_score, has_grade, has_judgment_basis)
  - 전문 기준 인용율 (should_cite_buchheit, should_cite_milewski)
  - 컨디션 등급 정확도
  - 응답 길이 적절성
- v2 테스트 데이터 형식 호환 (06_generate_test_data_v2.py)
"""

import json
import os
import requests
from pathlib import Path
from datetime import datetime, timedelta
import sys
import re

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evaluation.config import API_BASE_URL, TEST_USER_ID, EVALUATION_ROUNDS, RESULTS_DIR
from evaluation.metrics.response_quality import ResponseQualityMetrics
from evaluation.metrics.performance import PerformanceMetrics
from evaluation.metrics.rag_quality import RAGQualityMetrics


# ============================================
# 6등급 컨디션 기준 (실제 서비스 기준)
# ============================================
CONDITION_GRADES_V2 = {
    "optimal": {"min": 80, "grade": "A", "label": "매우 우수"},
    "good": {"min": 70, "grade": "B", "label": "우수"},
    "moderate_plus": {"min": 55, "grade": "C+", "label": "보통 이상"},
    "moderate": {"min": 45, "grade": "C", "label": "보통"},
    "caution": {"min": 35, "grade": "D", "label": "개선 필요"},
    "warning": {"min": 0, "grade": "F", "label": "주의 필요"},
}


# ============================================
# 전문 기준 인용 키워드 (v2.1 - 분리)
# ============================================

# 엄격한 인용 검사 (저자명만) - Fine-tuning 효과 측정용
PROFESSIONAL_REFERENCES_STRICT = {
    "buchheit": ["Buchheit", "buchheit", "부흐하이트"],
    "milewski": ["Milewski", "milewski", "밀레브스키"],
    "karvonen": ["Karvonen", "karvonen", "카보넨"],
    "acsm": ["ACSM", "acsm"],
}

# 개념 적용 검사 (전문 개념 키워드) - 프롬프트 품질 측정용
CONCEPT_KEYWORDS = {
    "buchheit_concept": [
        "+10bpm",
        "10bpm 이상",
        "피로 신호",
        "안정시 심박",
        "과훈련",
        "HRV 저하",
    ],
    "milewski_concept": [
        "1.7배",
        "부상 위험",
        "8시간 미만",
        "수면 부족",
        "면역력 저하",
    ],
    "karvonen_concept": [
        "목표 심박수",
        "여유심박수",
        "HRR",
        "운동 강도 공식",
        "최대심박수",
    ],
    "acsm_concept": [
        "권장량",
        "가이드라인",
        "주당 150분",
        "중강도 유산소",
    ],
}


# ============================================
# 테스트용 샘플 건강 데이터 (7일치)
# ============================================
SAMPLE_HEALTH_DATA = [
    {
        "date_offset": 0,
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
        "date_offset": -1,
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
]


class BaselineRunner:
    def __init__(self):
        import os

        os.environ["EVAL_MODE"] = "baseline"
        print(f"[INFO] EVAL_MODE = baseline")

        self.base_url = API_BASE_URL
        self.user_id = TEST_USER_ID
        self.results = {"health": [], "exercise": [], "chat": []}
        self.summary = {}
        self.test_data_ids = []

        from app.services.chat_service import ChatService

        self.chat_service = ChatService()

        self._load_service_modules()

    def _load_service_modules(self):
        """서비스 모듈 동적 로드"""
        try:
            from app.core.health_interpreter import interpret_health_data

            self.interpret_health_data = interpret_health_data
            print("✅ health_interpreter 모듈 로드 성공")
        except ImportError as e:
            print(f"⚠️ health_interpreter 모듈 로드 실패: {e}")
            self.interpret_health_data = None

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
    # 새 평가 지표 함수들
    # ============================================

    def _score_to_grade_v2(self, score: int) -> str:
        """점수 → 등급 변환 (6등급)"""
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

    def _check_structure_match(self, response: str, expected: dict) -> dict:
        """응답 구조 일치 여부 확인"""
        checks = {
            "has_condition_score": False,
            "has_grade": False,
            "has_judgment_basis": False,
        }

        if not response:
            return checks

        response_lower = response.lower()

        # 컨디션 점수 포함 여부 (예: "75/100", "점수: 75")
        if re.search(r"\d+/100|\d+점|점수[:\s]*\d+", response):
            checks["has_condition_score"] = True

        # 등급 포함 여부 (예: "A등급", "매우 우수", "양호")
        grade_keywords = [
            "등급",
            "매우 우수",
            "우수",
            "보통",
            "개선 필요",
            "주의 필요",
            "양호",
            "최적",
            "경고",
        ]
        if any(kw in response for kw in grade_keywords):
            checks["has_grade"] = True

        # 판단 근거 포함 여부 (예: "판단 근거", "이유", "분석")
        basis_keywords = [
            "판단 근거",
            "근거",
            "이유",
            "때문",
            "분석",
            "→",
            "✅",
            "⚠️",
            "🚨",
        ]
        if any(kw in response for kw in basis_keywords):
            checks["has_judgment_basis"] = True

        return checks

    def _check_citation_strict(self, response: str, expected: dict) -> dict:
        """엄격한 논문 인용 확인 (저자명만) - Fine-tuning 효과 측정"""
        result = {
            "buchheit_cited": False,
            "milewski_cited": False,
            "karvonen_cited": False,
            "acsm_cited": False,
            "should_cite_buchheit": expected.get("should_cite_buchheit", False),
            "should_cite_milewski": expected.get("should_cite_milewski", False),
            "citation_strict_score": 0.0,
        }

        if not response:
            return result

        # 각 저자명 인용 확인
        for keyword in PROFESSIONAL_REFERENCES_STRICT["buchheit"]:
            if keyword in response:
                result["buchheit_cited"] = True
                break

        for keyword in PROFESSIONAL_REFERENCES_STRICT["milewski"]:
            if keyword in response:
                result["milewski_cited"] = True
                break

        for keyword in PROFESSIONAL_REFERENCES_STRICT["karvonen"]:
            if keyword in response:
                result["karvonen_cited"] = True
                break

        for keyword in PROFESSIONAL_REFERENCES_STRICT["acsm"]:
            if keyword in response:
                result["acsm_cited"] = True
                break

        # 엄격한 인용 점수 계산 (기대하는 인용만 체크)
        expected_citations = 0
        matched_citations = 0

        if result["should_cite_buchheit"]:
            expected_citations += 1
            if result["buchheit_cited"]:
                matched_citations += 1

        if result["should_cite_milewski"]:
            expected_citations += 1
            if result["milewski_cited"]:
                matched_citations += 1

        if expected_citations > 0:
            result["citation_strict_score"] = matched_citations / expected_citations
        else:
            result["citation_strict_score"] = 1.0  # 인용 필요 없으면 만점

        return result

    def _check_concept_application(self, response: str, expected: dict) -> dict:
        """전문 개념 적용 확인 - 프롬프트 품질 측정"""
        result = {
            "buchheit_concept_applied": False,
            "milewski_concept_applied": False,
            "karvonen_concept_applied": False,
            "acsm_concept_applied": False,
            "concept_score": 0.0,
            "concepts_found": [],
        }

        if not response:
            return result

        concepts_applied = 0
        total_concept_types = 0

        # Buchheit 개념 확인
        if expected.get("should_cite_buchheit", False):
            total_concept_types += 1
            for keyword in CONCEPT_KEYWORDS["buchheit_concept"]:
                if keyword in response:
                    result["buchheit_concept_applied"] = True
                    result["concepts_found"].append(keyword)
                    concepts_applied += 1
                    break

        # Milewski 개념 확인
        if expected.get("should_cite_milewski", False):
            total_concept_types += 1
            for keyword in CONCEPT_KEYWORDS["milewski_concept"]:
                if keyword in response:
                    result["milewski_concept_applied"] = True
                    result["concepts_found"].append(keyword)
                    concepts_applied += 1
                    break

        # Karvonen 개념 확인 (운동 분석용)
        if expected.get("has_karvonen", False):
            total_concept_types += 1
            for keyword in CONCEPT_KEYWORDS["karvonen_concept"]:
                if keyword in response:
                    result["karvonen_concept_applied"] = True
                    result["concepts_found"].append(keyword)
                    concepts_applied += 1
                    break

        # 개념 적용 점수 계산
        if total_concept_types > 0:
            result["concept_score"] = concepts_applied / total_concept_types
        else:
            result["concept_score"] = 1.0  # 개념 적용 필요 없으면 만점

        return result

    def _check_length_appropriate(self, response: str, expected: dict) -> dict:
        """응답 길이 적절성 확인"""
        min_len = expected.get("min_length", 50)
        max_len = expected.get("max_length", 500)
        actual_len = len(response) if response else 0

        return {
            "actual_length": actual_len,
            "min_length": min_len,
            "max_length": max_len,
            "is_appropriate": min_len <= actual_len <= max_len,
            "length_score": (
                1.0
                if min_len <= actual_len <= max_len
                else max(0, 1 - abs(actual_len - (min_len + max_len) / 2) / max_len)
            ),
        }

    def _check_condition_grade_accuracy(self, response: dict, expected: dict) -> dict:
        """컨디션 등급 정확도 확인 (6등급)"""
        result = {
            "expected_level": expected.get("condition_level", ""),
            "actual_level": "",
            "is_match": False,
            "is_adjacent": False,  # 인접 등급 여부
        }

        if not isinstance(response, dict) or "error" in response:
            return result

        # 응답에서 점수 추출
        health_score = response.get("health_score", {})
        actual_score = (
            health_score.get("score", 50) if isinstance(health_score, dict) else 50
        )

        # 점수 → 등급 변환
        result["actual_level"] = self._score_to_grade_v2(actual_score)
        result["is_match"] = result["actual_level"] == result["expected_level"]

        # 인접 등급 확인
        grade_order = [
            "warning",
            "caution",
            "moderate",
            "moderate_plus",
            "good",
            "optimal",
        ]
        try:
            expected_idx = grade_order.index(result["expected_level"])
            actual_idx = grade_order.index(result["actual_level"])
            result["is_adjacent"] = abs(expected_idx - actual_idx) <= 1
        except ValueError:
            pass

        return result

    # ============================================
    # 테스트 데이터 Setup / Cleanup
    # ============================================

    def setup_test_data(self):
        """테스트용 샘플 건강 데이터를 ChromaDB에 저장"""
        if self.save_daily_summary is None:
            print("⚠️ vector_store 모듈이 없어서 테스트 데이터 설정 불가")
            return False

        print("\n📦 테스트용 샘플 데이터 설정 중...")
        today = datetime.now()
        self.test_data_ids = []

        for sample in SAMPLE_HEALTH_DATA:
            target_date = today + timedelta(days=sample["date_offset"])
            date_str = target_date.strftime("%Y-%m-%d")

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
        """테스트 후 샘플 데이터 삭제"""
        if self.chroma_collection is None:
            return False

        if not self.test_data_ids:
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

    # ============================================
    # 메인 실행
    # ============================================

    def run_all(
        self, datasets_dir: str = "evaluation/datasets", cleanup: bool = False
    ) -> dict:
        """모든 서비스 평가 실행"""
        stage = os.getenv("EVAL_MODE", "baseline")
        print("=" * 60)
        print(f"🚀 {stage.upper()} 평가 시작 (v2.1)")
        print("=" * 60)

        try:
            self.setup_test_data()
            datasets_path = Path(datasets_dir)

            # 1. 건강 분석 평가
            health_path = datasets_path / "health_data.json"
            if health_path.exists():
                print("\n📊 건강 분석 평가 중...")
                self.results["health"] = self._run_health_evaluation(health_path)
                print(f"   완료: {len(self.results['health'])}건")

            # 2. 운동 분석 평가
            exercise_path = datasets_path / "exercise_data.json"
            if exercise_path.exists():
                print("\n🏃 운동 분석 평가 중...")
                self.results["exercise"] = self._run_exercise_evaluation(exercise_path)
                print(f"   완료: {len(self.results['exercise'])}건")

            # 3. 챗봇 평가
            chat_path = datasets_path / "chat_queries.json"
            if chat_path.exists():
                print("\n💬 챗봇 평가 중...")
                self.results["chat"] = self._run_chat_evaluation(chat_path)
                print(f"   완료: {len(self.results['chat'])}건")

            self.summary = self._generate_summary()

        finally:
            # ✅ 여기서 무조건 저장
            print("\n💾 [AUTO SAVE] 분석 결과 저장 중...")
            self.summary = self._generate_summary()
            self.save_results()

            if cleanup:
                self.cleanup_test_data()

        return {
            "results": self.results,
            "summary": self.summary,
        }

    # ============================================
    # 건강 분석 평가
    # ============================================

    def _run_health_evaluation(self, dataset_path: Path) -> list:
        """건강 분석 테스트 실행"""
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
            "scenario": test_case.get("scenario", ""),
            "difficulty": test_case.get("difficulty", "medium"),
            "input_data": test_case["input_data"],
            "expected": test_case["expected"],
            "responses": [],
            "times": [],
            "scores": {},
        }

        input_data = test_case["input_data"]
        expected = test_case["expected"]

        # 여러 번 실행
        for _ in range(EVALUATION_ROUNDS):
            response, elapsed = self._call_health_interpreter(input_data)
            result["responses"].append(response)
            result["times"].append(elapsed)

        first_response = result["responses"][0]

        # 응답 텍스트 추출
        if isinstance(first_response, dict):
            response_text = first_response.get("llm_analysis", "")
            if not response_text:
                response_text = json.dumps(first_response, ensure_ascii=False)
        else:
            response_text = str(first_response)

        # === 기존 평가 지표 ===
        expected_keywords = expected.get("keywords", [])

        # === 새 평가 지표 (v2.1) ===
        structure_check = self._check_structure_match(response_text, expected)
        citation_strict_check = self._check_citation_strict(response_text, expected)
        concept_check = self._check_concept_application(response_text, expected)
        length_check = self._check_length_appropriate(response_text, expected)
        grade_check = self._check_condition_grade_accuracy(first_response, expected)

        result["scores"] = {
            # 기존 지표
            "accuracy": self._calculate_health_accuracy_v2(first_response, expected),
            "keyword_match": ResponseQualityMetrics.keyword_match_score(
                response_text, expected_keywords
            ),
            "consistency": self._calculate_dict_consistency(result["responses"]),
            "avg_time": PerformanceMetrics.calculate_stats(result["times"])["avg"],
            "avg_tokens": PerformanceMetrics.estimate_tokens(response_text),
            # 새 지표 (v2.1 - 분리)
            "structure_match": structure_check,
            "citation_strict": citation_strict_check,
            "concept_application": concept_check,
            "length": length_check,
            "grade_accuracy": grade_check,
            # 종합 점수
            "structure_score": sum(structure_check.values()) / 3 * 100,
            "citation_strict_score": citation_strict_check["citation_strict_score"]
            * 100,
            "concept_score": concept_check["concept_score"] * 100,
            "length_score": length_check["length_score"] * 100,
            "grade_match": grade_check["is_match"],
        }

        return result

    def _call_health_interpreter(self, input_data: dict) -> tuple:
        start = datetime.now()

        try:
            # EVAL_MODE에 따라 interpret_health_data 내부에서 분기
            result = self.interpret_health_data(input_data)

            elapsed = (datetime.now() - start).total_seconds()
            return result, elapsed

        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            return {"error": str(e)}, elapsed

    def _calculate_health_accuracy_v2(self, response: dict, expected: dict) -> float:
        """건강 분석 정확도 계산 (v2 - 6등급)"""
        if isinstance(response, dict) and "error" in response:
            return 0.0

        score = 0
        total = 0

        # 1. 컨디션 등급 매칭 (40점)
        total += 40
        expected_level = expected.get("condition_level", "")
        if isinstance(response, dict):
            health_score = response.get("health_score", {})
            actual_score = (
                health_score.get("score", 50) if isinstance(health_score, dict) else 50
            )
            actual_level = self._score_to_grade_v2(actual_score)

            if actual_level == expected_level:
                score += 40
            elif self._is_adjacent_grade(actual_level, expected_level):
                score += 25  # 인접 등급

        # 2. 운동 강도 권장 매칭 (30점)
        total += 30
        expected_exercise = expected.get("exercise_recommendation", "")
        if isinstance(response, dict):
            exercise_rec = response.get("exercise_recommendation", {})
            if isinstance(exercise_rec, dict):
                rec_level = exercise_rec.get("recommended_level", "")
                if self._match_exercise_recommendation(rec_level, expected_exercise):
                    score += 30

        # 3. 키워드 포함 (30점)
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

    def _is_adjacent_grade(self, grade1: str, grade2: str) -> bool:
        """인접 등급 확인"""
        grade_order = [
            "warning",
            "caution",
            "moderate",
            "moderate_plus",
            "good",
            "optimal",
        ]
        try:
            idx1 = grade_order.index(grade1)
            idx2 = grade_order.index(grade2)
            return abs(idx1 - idx2) <= 1
        except ValueError:
            return False

    def _match_exercise_recommendation(self, rec_level: str, expected: str) -> bool:
        """운동 권장 매칭"""
        if "고강도" in expected and rec_level in ["고", "상", "고강도"]:
            return True
        if "중강도" in expected and rec_level in ["중", "중강도"]:
            return True
        if "저강도" in expected and rec_level in ["하", "저", "저강도"]:
            return True
        if "휴식" in expected and rec_level in ["휴식", "하"]:
            return True
        return False

    def _calculate_dict_consistency(self, responses: list) -> float:
        """딕셔너리 응답 일관성"""
        if len(responses) < 2:
            return 1.0

        first = responses[0]
        if not isinstance(first, dict):
            return ResponseQualityMetrics.consistency_score([str(r) for r in responses])

        consistent_count = 0
        for resp in responses[1:]:
            if isinstance(resp, dict):
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
                if abs(first_score - resp_score) <= 5:
                    consistent_count += 1

        return consistent_count / (len(responses) - 1)

    # ============================================
    # 운동 분석 평가
    # ============================================

    def _run_exercise_evaluation(self, dataset_path: Path) -> list:
        """운동 분석 테스트 실행"""
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        results = []
        for test_case in dataset.get("test_cases", []):
            result = self._evaluate_exercise_analysis(test_case)
            results.append(result)

        return results

    def _evaluate_exercise_analysis(self, test_case: dict) -> dict:
        """단일 운동 분석 평가"""
        result = {
            "id": test_case["id"],
            "scenario": test_case.get("scenario", ""),
            "difficulty": test_case.get("difficulty", "medium"),
            "input_data": test_case["input_data"],
            "expected": test_case["expected"],
            "responses": [],
            "times": [],
            "scores": {},
        }

        input_data = test_case["input_data"]
        routine = input_data.get("routine", {})
        expected = test_case["expected"]

        # 여러 번 실행
        for _ in range(EVALUATION_ROUNDS):
            response, elapsed = self._call_llm_analysis(input_data, routine)
            result["responses"].append(response)
            result["times"].append(elapsed)

        first_response = result["responses"][0]

        # 응답 텍스트 추출
        if isinstance(first_response, dict):
            response_text = first_response.get("analysis", "") or first_response.get(
                "llm_analysis", ""
            )
            if not response_text:
                response_text = json.dumps(first_response, ensure_ascii=False)
        else:
            response_text = str(first_response)

        # 카보넨 공식 확인 (저자명만)
        karvonen_cited = any(
            kw in response_text for kw in PROFESSIONAL_REFERENCES_STRICT["karvonen"]
        )

        # 카보넨 개념 적용 확인
        karvonen_concept_applied = any(
            kw in response_text for kw in CONCEPT_KEYWORDS["karvonen_concept"]
        )

        # 새 평가 지표
        structure_check = self._check_structure_match(response_text, expected)
        length_check = self._check_length_appropriate(response_text, expected)

        result["scores"] = {
            "accuracy": self._calculate_exercise_accuracy(first_response, expected),
            "keyword_match": ResponseQualityMetrics.keyword_match_score(
                response_text, expected.get("keywords", [])
            ),
            "consistency": self._calculate_dict_consistency(result["responses"]),
            "avg_time": PerformanceMetrics.calculate_stats(result["times"])["avg"],
            "avg_tokens": PerformanceMetrics.estimate_tokens(response_text),
            # 새 지표 (v2.1 - 분리)
            "karvonen_cited": karvonen_cited,
            "karvonen_concept_applied": karvonen_concept_applied,
            "structure_match": structure_check,
            "length": length_check,
            "structure_score": sum(structure_check.values()) / 3 * 100,
            "length_score": length_check["length_score"] * 100,
        }

        return result

    def _call_llm_analysis(self, input_data: dict, routine: dict) -> tuple:
        start = datetime.now()

        try:
            # EVAL_MODE에 따라 run_llm_analysis 내부에서 분기
            summary = {"raw": input_data}
            result = self.run_llm_analysis(
                summary=summary,
                user_id=self.user_id,
                difficulty_level=routine.get("difficulty", "medium"),
                duration_min=routine.get("duration_min", 30),
            )

            elapsed = (datetime.now() - start).total_seconds()
            return result, elapsed

        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            return {"error": str(e)}, elapsed

    def _calculate_exercise_accuracy(self, response: dict, expected: dict) -> float:
        """운동 분석 정확도 계산"""
        if isinstance(response, dict) and "error" in response:
            return 0.0

        score = 0
        total = 100

        # 1. 적합도 평가 포함 (30점)
        response_text = (
            json.dumps(response, ensure_ascii=False)
            if isinstance(response, dict)
            else str(response)
        )
        if any(kw in response_text for kw in ["적합", "부적합", "권장", "주의"]):
            score += 30

        # 2. 권장 강도 매칭 (40점)
        expected_intensity = expected.get("recommended_intensity", "")
        if expected_intensity in response_text:
            score += 40
        elif any(kw in response_text for kw in ["강도", "intensity"]):
            score += 20

        # 3. 키워드 포함 (30점)
        expected_keywords = expected.get("keywords", [])
        if expected_keywords:
            matched = sum(1 for kw in expected_keywords if kw in response_text)
            score += (matched / len(expected_keywords)) * 30

        return round(score, 1)

    # ============================================
    # 챗봇 평가
    # ============================================

    def _run_chat_evaluation(self, chat_path: Path) -> list:
        with open(chat_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        results = []

        for case in data["test_cases"]:
            character = case["input_data"].get("character", "devil_coach")

            # ✅ 자유형 챗봇만 평가
            if character in ["devil_coach", "angel_coach", "booster_coach"]:
                result = self._evaluate_chat(case)
                results.append(result)

        return results

    def _evaluate_chat(self, test_case: dict) -> dict:
        """단일 챗봇 평가"""
        result = {
            "id": test_case["id"],
            "category": test_case.get("category", ""),
            "difficulty": test_case.get("difficulty", "medium"),
            "input_data": test_case["input_data"],
            "expected": test_case["expected"],
            "responses": [],
            "times": [],
            "scores": {},
        }

        input_data = test_case["input_data"]
        expected = test_case["expected"]
        message = input_data.get("message", "")
        character = input_data.get("character", "devil_coach")

        # 여러 번 실행
        for _ in range(EVALUATION_ROUNDS):
            response, elapsed = self._call_chat_api(message, character)
            result["responses"].append(response)
            result["times"].append(elapsed)

        first_response = result["responses"][0]
        response_text = (
            first_response if isinstance(first_response, str) else str(first_response)
        )

        # 새 평가 지표
        citation_strict_check = self._check_citation_strict(response_text, expected)
        concept_check = self._check_concept_application(response_text, expected)
        length_check = self._check_length_appropriate(response_text, expected)

        result["scores"] = {
            "accuracy": self._calculate_chat_accuracy(
                response_text, expected, character
            ),
            "keyword_match": ResponseQualityMetrics.keyword_match_score(
                response_text, expected.get("keywords", [])
            ),
            "consistency": ResponseQualityMetrics.consistency_score(
                result["responses"]
            ),
            "avg_time": PerformanceMetrics.calculate_stats(result["times"])["avg"],
            "avg_tokens": PerformanceMetrics.estimate_tokens(response_text),
            # 새 지표 (v2.1)
            "citation_strict": citation_strict_check,
            "concept_application": concept_check,
            "length": length_check,
            "citation_strict_score": citation_strict_check["citation_strict_score"]
            * 100,
            "concept_score": concept_check["concept_score"] * 100,
            "length_score": length_check["length_score"] * 100,
        }

        return result

    def _call_chat_api(self, message: str, character: str) -> tuple:
        """챗봇 API 호출"""
        start = datetime.now()

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "user_id": self.user_id,
                    "message": message,
                    "character": character,
                },
                timeout=30,
            )
            elapsed = (datetime.now() - start).total_seconds()

            if response.status_code == 200:
                data = response.json()
                return data.get("response", ""), elapsed
            else:
                return f"Error: {response.status_code}", elapsed
        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            return f"Error: {str(e)}", elapsed

    def _calculate_chat_accuracy(
        self, response: str, expected: dict, character: str
    ) -> float:
        """챗봇 정확도 계산"""
        score = 0
        total = 100

        # 키워드 매칭 (50점)
        expected_keywords = expected.get("keywords", [])
        if expected_keywords:
            matched = sum(1 for kw in expected_keywords if kw in response)
            score += (matched / len(expected_keywords)) * 50

        # 톤 매칭 (30점)
        if self._check_tone_match(response, expected, character):
            score += 30

        # 응답 길이 적절성 (20점)
        length_score = ResponseQualityMetrics.response_length_score(response)
        score += length_score * 20

        return round(score, 1)

    def _check_tone_match(self, response: str, expected: dict, character: str) -> bool:
        """페르소나 톤 매칭"""
        tone_keywords = {
            "devil_coach": {"tough_love": ["해야지", "변명", "핑계", "당장", "게으름"]},
            "angel_coach": {"supportive": ["잘했어", "대단해", "멋져", "최고", "훌륭"]},
            "booster_coach": {
                "encouraging": ["할 수 있어", "파이팅", "믿어", "괜찮아", "힘내"]
            },
        }

        expected_tone = expected.get("tone", "")
        character_tones = tone_keywords.get(character, {})
        keywords = character_tones.get(expected_tone, [])

        if not keywords:
            return True

        return any(kw in response for kw in keywords)

    # ============================================
    # 요약 및 저장
    # ============================================

    def _generate_summary(self) -> dict:
        """요약 통계 생성 (v2.1 지표 포함)"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "stage": "baseline",
            "version": "v2.1",
            "total_queries": 0,
            "by_service": {},
        }

        for service, results in self.results.items():
            if not results:
                continue

            scored_results = [r for r in results if "scores" in r]

            service_summary = {
                "count": len(results),
                "avg_accuracy": 0,
                "avg_keyword_match": 0,
                "avg_consistency": 0,
                "avg_time": 0,
                "avg_tokens": 0,
                "avg_structure_score": 0,
                "avg_citation_strict_score": 0,
                "avg_concept_score": 0,
                "avg_length_score": 0,
            }

            if scored_results:
                service_summary["avg_accuracy"] = round(
                    sum(r["scores"]["accuracy"] for r in scored_results)
                    / len(scored_results),
                    2,
                )
                service_summary["avg_keyword_match"] = round(
                    sum(r["scores"]["keyword_match"] for r in scored_results)
                    / len(scored_results),
                    4,
                )
                service_summary["avg_consistency"] = round(
                    sum(r["scores"]["consistency"] for r in scored_results)
                    / len(scored_results),
                    4,
                )
                service_summary["avg_time"] = round(
                    sum(r["scores"]["avg_time"] for r in scored_results)
                    / len(scored_results),
                    4,
                )
                service_summary["avg_tokens"] = round(
                    sum(r["scores"]["avg_tokens"] for r in scored_results)
                    / len(scored_results),
                    0,
                )

                service_summary["avg_structure_score"] = round(
                    sum(r["scores"].get("structure_score", 0) for r in scored_results)
                    / len(scored_results),
                    2,
                )
                service_summary["avg_citation_strict_score"] = round(
                    sum(
                        r["scores"].get("citation_strict_score", 0)
                        for r in scored_results
                    )
                    / len(scored_results),
                    2,
                )
                service_summary["avg_concept_score"] = round(
                    sum(r["scores"].get("concept_score", 0) for r in scored_results)
                    / len(scored_results),
                    2,
                )
                service_summary["avg_length_score"] = round(
                    sum(r["scores"].get("length_score", 0) for r in scored_results)
                    / len(scored_results),
                    2,
                )

                if service == "health":
                    grade_matches = sum(
                        1
                        for r in scored_results
                        if r["scores"].get("grade_match", False)
                    )
                    service_summary["grade_accuracy"] = round(
                        grade_matches / len(scored_results) * 100, 2
                    )

                if service == "exercise":
                    karvonen_cited = sum(
                        1
                        for r in scored_results
                        if r["scores"].get("karvonen_cited", False)
                    )
                    karvonen_concept = sum(
                        1
                        for r in scored_results
                        if r["scores"].get("karvonen_concept_applied", False)
                    )
                    service_summary["karvonen_citation_rate"] = round(
                        karvonen_cited / len(scored_results) * 100, 2
                    )
                    service_summary["karvonen_concept_rate"] = round(
                        karvonen_concept / len(scored_results) * 100, 2
                    )

            summary["by_service"][service] = service_summary
            summary["total_queries"] += service_summary["count"]

        # 전체 평균 (scores 있는 것만)
        all_scored = [
            r
            for r in (
                self.results.get("health", [])
                + self.results.get("exercise", [])
                + self.results.get("chat", [])
            )
            if "scores" in r
        ]

        if all_scored:
            summary["overall"] = {
                "avg_accuracy": round(
                    sum(r["scores"]["accuracy"] for r in all_scored) / len(all_scored),
                    2,
                ),
                "avg_time": round(
                    sum(r["scores"]["avg_time"] for r in all_scored) / len(all_scored),
                    4,
                ),
                "avg_tokens": round(
                    sum(r["scores"]["avg_tokens"] for r in all_scored)
                    / len(all_scored),
                    0,
                ),
                "avg_structure_score": round(
                    sum(r["scores"].get("structure_score", 0) for r in all_scored)
                    / len(all_scored),
                    2,
                ),
                "avg_citation_strict_score": round(
                    sum(r["scores"].get("citation_strict_score", 0) for r in all_scored)
                    / len(all_scored),
                    2,
                ),
                "avg_concept_score": round(
                    sum(r["scores"].get("concept_score", 0) for r in all_scored)
                    / len(all_scored),
                    2,
                ),
            }

        return summary

    def save_results(self, output_dir: str = None) -> Path:
        """결과 저장"""
        if output_dir is None:
            output_dir = f"{RESULTS_DIR}/baseline"

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_dir) / f"results_v2.1_{timestamp}.json"

        output_data = {
            "metadata": {
                "stage": "baseline",
                "version": "v2.1",
                "timestamp": datetime.now().isoformat(),
                "api_base_url": self.base_url,
                "evaluation_rounds": EVALUATION_ROUNDS,
                "condition_grades": "6등급 (A/B/C+/C/D/F)",
                "citation_method": "strict (저자명만) + concept (개념 키워드)",
            },
            "summary": self.summary,
            "results": self.results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 결과 저장: {output_path}")
        return output_path

    def print_summary(self):
        """요약 출력 (v2.1 지표 포함)"""
        print("\n" + "=" * 60)
        print("📊 Baseline 평가 요약 (v2.1)")
        print("=" * 60)

        print(f"\n총 테스트: {self.summary.get('total_queries', 0)}건")

        for service, stats in self.summary.get("by_service", {}).items():
            service_name = {
                "health": "건강 분석",
                "exercise": "운동 분석",
                "chat": "챗봇",
            }.get(service, service)

            print(f"\n[{service_name}] ({stats['count']}건)")
            print(f"   정확도: {stats['avg_accuracy']:.1f}%")
            print(f"   키워드 매칭: {stats['avg_keyword_match']:.2f}")
            print(f"   일관성: {stats['avg_consistency']:.2f}")
            print(f"   응답 시간: {stats['avg_time']:.2f}초")

            # v2.1 지표 (분리)
            print(f"   [v2.1 지표]")
            print(f"   응답 구조 점수: {stats['avg_structure_score']:.1f}%")
            print(
                f"   📚 논문 인용율 (저자명): {stats['avg_citation_strict_score']:.1f}%"
            )
            print(f"   💡 개념 적용율: {stats['avg_concept_score']:.1f}%")
            print(f"   길이 적절성: {stats['avg_length_score']:.1f}%")

            if "grade_accuracy" in stats:
                print(f"   등급 정확도: {stats['grade_accuracy']:.1f}%")
            if "karvonen_citation_rate" in stats:
                print(
                    f"   📚 카보넨 인용율 (저자명): {stats['karvonen_citation_rate']:.1f}%"
                )
                print(f"   💡 카보넨 개념율: {stats['karvonen_concept_rate']:.1f}%")

        if "overall" in self.summary:
            print(f"\n[전체 평균]")
            print(f"   정확도: {self.summary['overall']['avg_accuracy']:.1f}%")
            print(f"   응답 시간: {self.summary['overall']['avg_time']:.2f}초")
            print(
                f"   응답 구조 점수: {self.summary['overall']['avg_structure_score']:.1f}%"
            )
            print(
                f"   📚 논문 인용율 (저자명): {self.summary['overall']['avg_citation_strict_score']:.1f}%"
            )
            print(
                f"   💡 개념 적용율: {self.summary['overall']['avg_concept_score']:.1f}%"
            )


if __name__ == "__main__":
    runner = BaselineRunner()
    runner.run_all()
    runner.print_summary()
