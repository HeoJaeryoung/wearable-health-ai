# Services

## 역할

API 엔드포인트와 Core 로직 사이의 **비즈니스 로직 계층**

## 데이터 흐름

```
API Endpoints → Services → Core/Utils
```

## 파일 목록

| 파일                     | 역할             | 호출하는 Core/Utils                                         |
| ------------------------ | ---------------- | ----------------------------------------------------------- |
| `file_upload_service.py` | ZIP/DB 파일 처리 | unzipper, db_to_json, db_parser, vector_store, llm_analysis |
| `auto_upload_service.py` | 앱 JSON 처리     | preprocess, vector_store, llm_analysis                      |
| `chat_service.py`        | 챗봇 로직        | chatbot_engine                                              |
| `similar_service.py`     | 유사도 검색      | vector_store                                                |

## 처리 흐름 예시

### file_upload_service.py

```
1. ZIP 파일 저장
2. ZIP 압축 해제 (unzipper.py)
3. DB → JSON 변환 (db_to_json.py)
4. 날짜별 데이터 파싱 (db_parser.py)
5. VectorDB 저장 (vector_store.py)
6. LLM 분석 (llm_analysis.py)
7. 결과 반환
```

### chat_service.py

```
1. 캐릭터 검증
2. ChatGenerator 호출
3. 응답 반환
```
