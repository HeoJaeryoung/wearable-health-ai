# 평가 시스템

## 개요

리팩토링 전후 성능 비교를 위한 평가 시스템

## 평가 단계

1. **Baseline** - 현재 코드 (LangChain 적용 전)
2. **LangChain** - 리팩토링 후
3. **Fine-tuned** - LLM 파인튜닝 후

## 평가 지표

### 응답 품질

- 키워드 매칭 점수
- 응답 길이 적절성
- 일관성 점수

### 성능

- 응답 시간 (초)
- 토큰 사용량 (추정)

### RAG 품질

- 검색 관련성
- 컨텍스트 활용도

## 실행 방법

```bash
# Baseline 평가
python evaluation/run_evaluation.py --stage baseline --dataset all

# 건강 질문만 평가
python evaluation/run_evaluation.py --stage baseline --dataset health
```

## 결과 확인

- `results/baseline/` - Baseline 결과
- `results/langchain/` - LangChain 결과
- `results/finetuned/` - Fine-tuned 결과
- `reports/` - 비교 리포트

```

---

## 체크리스트
```

[ ] evaluation/**init**.py
[ ] evaluation/config.py
[ ] evaluation/README.md
[ ] evaluation/datasets/**init**.py
[ ] evaluation/metrics/**init**.py
[ ] evaluation/metrics/response_quality.py
[ ] evaluation/metrics/performance.py
[ ] evaluation/metrics/rag_quality.py
[ ] evaluation/runners/**init**.py
[ ] evaluation/runners/baseline_runner.py
[ ] evaluation/run_evaluation.py
[ ] evaluation/results/baseline/ (폴더)
[ ] evaluation/results/langchain/ (폴더)
[ ] evaluation/results/finetuned/ (폴더)
[ ] evaluation/reports/ (폴더)

# evaluation 폴더 구조

baseline_backend/
├── app/
│ └── ...
│
├── evaluation/
│ ├── **init**.py
│ ├── config.py # 평가 설정
│ ├── README.md # 평가 방법 설명
│ │
│ ├── datasets/ # 테스트 데이터셋
│ │ ├── **init**.py
│ │ ├── health_queries.json # 건강 질문
│ │ ├── routine_queries.json # 루틴 요청
│ │ └── chat_queries.json # 챗봇 대화
│ │
│ ├── metrics/ # 평가 지표 계산
│ │ ├── **init**.py
│ │ ├── response_quality.py # 응답 품질
│ │ ├── performance.py # 성능 (시간, 토큰)
│ │ └── rag_quality.py # RAG 품질
│ │
│ ├── runners/ # 평가 실행기
│ │ ├── **init**.py
│ │ ├── baseline_runner.py # Baseline 평가
│ │ ├── langchain_runner.py # LangChain 평가
│ │ └── finetuned_runner.py # Fine-tuned 평가
│ │
│ ├── results/ # 결과 저장
│ │ ├── baseline/
│ │ ├── langchain/
│ │ └── finetuned/
│ │
│ ├── reports/ # 비교 리포트
│ │
│ └── run_evaluation.py # 평가 실행 스크립트
