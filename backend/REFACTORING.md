# LangChain 리팩토링 계획

## 개요

Baseline 시스템을 LangChain 기반으로 리팩토링하여 성능과 코드 품질을 개선합니다.

**브랜치:** `langchain`  
**시작일:** 2026-01-01  
**목표:** Baseline 대비 정확도 20% 이상 향상

---

## Baseline 평가 결과 (기준점)

| 서비스        | 정확도    | 주요 이슈                              |
| ------------- | --------- | -------------------------------------- |
| 건강 분석     | 50.2%     | 어려움 난이도 10.8%                    |
| 운동 추천     | 62.7%     | LLM 0%, Fallback 100% (검증 실패 27건) |
| 챗봇          | 39.4%     | 일관성 0.31, 응답 짧음 (토큰 25)       |
| **전체 평균** | **49.6%** | -                                      |

---

## 리팩토링 항목

### 1. ZIP 파싱 최적화

**문제:**

- ZIP 파일에 약 420일치 데이터 포함
- 전체 파싱 → 시간 오래 걸림

**해결:**

- 최근 30일만 파싱
- 나머지는 원본 ZIP만 보관 (필요시 추후 파싱)

**대상 파일:**

- `app/services/file_upload_service.py`
- `app/core/db_parser.py`

**예상 효과:**

- 파싱 시간 약 93% 감소 (420일 → 30일)
- 임베딩 API 호출 약 93% 감소
- 사용자 대기 시간 대폭 단축

**상태:** ✅ 완료

---

### 2. 운동 추천 Structured Output

**문제:**

- LLM이 자유 형식으로 응답 → JSON 파싱/검증 실패
- 27건 검증 실패 (시간 목표 미달)
- LLM 성공률 0%, Fallback 100%

**해결:**

- LangChain `with_structured_output()` 적용
- Pydantic 모델로 출력 형식 강제

**적용 전:**

```python
# LLM 자유 응답 → 파싱 실패 가능
response = llm.invoke("30분 운동 루틴 만들어줘")
# 결과: "네, 운동 루틴입니다! { ... }" (불안정)
```

**적용 후:**

```python
from pydantic import BaseModel

class Exercise(BaseModel):
    name: str
    duration_sec: int
    sets: int

class ExerciseRoutine(BaseModel):
    exercises: list[Exercise]
    total_time_sec: int

structured_llm = llm.with_structured_output(ExerciseRoutine)
result = structured_llm.invoke("30분 운동 루틴 만들어줘")
# 결과: ExerciseRoutine(exercises=[...], total_time_sec=1800) (안정)
```

**대상 파일:**

- `app/core/llm_analysis.py`

**예상 효과:**

- 검증 실패 27건 → 0건
- LLM 성공률 0% → 90% 이상

**상태:** ✅ 완료

---

### 3. 챗봇 LangChain Chain

**문제:**

- 일관성 0.31 (낮음)
- 평균 토큰 25 (응답 너무 짧음)
- RAG 활용도 0.18 (낮음)

**해결:**

- LangChain Chain으로 파이프라인 구조화
- 프롬프트 템플릿 표준화
- RAG 통합 개선

**대상 파일:**

- `app/core/chatbot_engine/chat_generator.py`
- `app/core/chatbot_engine/rag_query.py`

**예상 효과:**

- 일관성 0.31 → 0.7 이상
- 응답 품질 향상

**상태:** ✅ 완료

---

### 4. 건강 분석 Few-shot Prompting

**문제:**

- 쉬움 95% vs 어려움 10.8% (난이도별 급락)
- 복잡한 케이스 처리 미흡

**해결:**

- Few-shot 예시 추가
- 복잡한 케이스 처리 로직 개선

**대상 파일:**

- `app/core/health_interpreter.py`

**예상 효과:**

- 어려움 난이도 10.8% → 40% 이상

**상태:** ✅ 완료 (llm_analysis.py에 Few-shot 추가)

---

## 진행 순서

```
1. LangChain 기본 설정
   └── 패키지 설치 (langchain, langchain-openai)
   └── config 설정 추가

2. ZIP 파싱 최적화 (체감 효과 큼)
   └── 최근 30일만 파싱

3. 운동 추천 Structured Output (정확도 개선)
   └── LLM 성공률 향상

4. 챗봇 LangChain Chain (품질 개선)
   └── 일관성/응답 품질 향상

5. 건강 분석 Few-shot (선택)
   └── 어려움 난이도 개선

6. 평가 및 비교
   └── 동일 테스트셋 재평가
   └── Baseline vs LangChain 비교 리포트
```

---

## 진행 상황

| 항목                        | 상태    | 완료일     | 비고                                        |
| --------------------------- | ------- | ---------- | ------------------------------------------- |
| LangChain 설정              | ✅ 완료 | 2026-01-01 | langchain, langchain-openai, langchain-core |
| ZIP 파싱 최적화             | ✅ 완료 | 2026-01-01 | 420일 → 30일 (93% 감소)                     |
| 운동 추천 Structured Output | ✅ 완료 | 2026-01-01 | LangChain Chain + Pydantic                  |
| 챗봇 프롬프트 개선          | ✅ 완료 | 2026-01-01 | 3-5문장, 토큰 500                           |
| 건강 분석 Few-shot          | ✅ 완료 | 2026-01-01 | system_prompt에 예시 추가                   |
| 평가 시스템 구축            | ✅ 완료 | 2026-01-01 | langchain_runner.py 생성                    |
| LangChain 평가              | ⬜ 대기 | -          | 서버 시작 후 실행                           |
| 비교 리포트 작성            | ⬜ 대기 | -          | 평가 완료 후 작성                           |

---

## 수정된 파일 목록

| 파일                                        | 변경 내용                                    |
| ------------------------------------------- | -------------------------------------------- |
| `app/core/llm_analysis.py`                  | LangChain Chain, Structured Output, Few-shot |
| `app/core/chatbot_engine/chat_generator.py` | 프롬프트 개선, 토큰 증가                     |
| `app/services/file_upload_service.py`       | 30일 파싱 최적화                             |
| `evaluation/runners/langchain_runner.py`    | 신규 생성                                    |
| `evaluation/run_evaluation.py`              | langchain 스테이지 추가                      |
| `evaluation/config.py`                      | 포트 8000 수정                               |

---

## 실행 방법

```bash
# 1. 서버 시작
uvicorn app.main:app --reload --port 8000

# 2. LangChain 평가
python -m evaluation.run_evaluation --stage langchain

# 3. 결과 확인
evaluation/results/langchain/results_YYYYMMDD_HHMMSS.json
```

---

## 참고

- Baseline 평가 결과: `evaluation/results/baseline/results_20260101_230133.json`
- LangChain 평가 결과: `evaluation/results/langchain/` (평가 후 생성)
