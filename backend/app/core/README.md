# Core

## 역할

**AI/LLM 핵심 로직** - 분석, RAG, VectorDB, 챗봇 엔진

## 데이터 흐름

```
Services → Core → OpenAI API / ChromaDB
```

## 파일 목록

| 파일                    | 역할                        | 의존성                     |
| ----------------------- | --------------------------- | -------------------------- |
| `llm_analysis.py`       | LLM 건강 분석 + 운동 추천   | OpenAI API                 |
| `health_interpreter.py` | 건강 데이터 해석, 점수 계산 | -                          |
| `vector_store.py`       | ChromaDB 저장/검색          | ChromaDB, OpenAI Embedding |
| `rag_query.py`          | RAG 쿼리 빌더               | health_interpreter         |
| `adaptive_threshold.py` | 유사도 임계값 계산          | -                          |
| `db_parser.py`          | Samsung Health DB 파싱      | -                          |
| `db_to_json.py`         | SQLite → JSON 변환          | sqlite3                    |
| `unzipper.py`           | ZIP 압축 해제               | zipfile                    |

## chatbot_engine/ 폴더

| 파일                   | 역할                                   |
| ---------------------- | -------------------------------------- |
| `chat_generator.py`    | 챗봇 응답 생성 (메인)                  |
| `intent_classifier.py` | 의도 분류 (건강질문/루틴요청/일반대화) |
| `persona.py`           | 3가지 캐릭터 프롬프트                  |
| `rag_query.py`         | 챗봇용 RAG 쿼리                        |
| `fixed_responses.py`   | 고정 응답 생성                         |

## LLM 호출 흐름

```
chat_generator.py
    │
    ├── intent_classifier.py (의도 분류)
    │
    ├── rag_query.py (데이터 검색)
    │       │
    │       └── vector_store.py (ChromaDB)
    │
    ├── persona.py (캐릭터 프롬프트)
    │
    └── OpenAI API 호출 → 응답 생성
```
