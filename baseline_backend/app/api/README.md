# API Endpoints

## 데이터 흐름 순서

```
1. 데이터 입력
   ├── file_upload.py      # ZIP/DB 파일 업로드
   └── auto_upload.py      # 앱에서 JSON 전송
          │
          ▼
2. 데이터 조회
   └── app_data.py         # 저장된 데이터 조회
          │
          ▼
3. 데이터 분석
   ├── user.py             # AI 건강 분석 + 운동 추천
   └── similar.py          # 유사 데이터 RAG 검색
          │
          ▼
4. 사용자 상호작용
   └── chat.py             # 트레이너 챗봇
```

## 엔드포인트 목록

| 파일             | 엔드포인트                  | 메서드 | 설명                |
| ---------------- | --------------------------- | ------ | ------------------- |
| `file_upload.py` | `/api/file/upload`          | POST   | ZIP/DB 파일 업로드  |
| `auto_upload.py` | `/api/auto/upload`          | POST   | 앱에서 JSON 업로드  |
| `app_data.py`    | `/api/app/latest`           | GET    | 최신 앱 데이터 조회 |
| `app_data.py`    | `/api/app/history`          | GET    | 앱 데이터 히스토리  |
| `user.py`        | `/api/user/latest-analysis` | GET    | AI 건강 분석        |
| `user.py`        | `/api/user/raw-history`     | GET    | RAW 데이터 히스토리 |
| `similar.py`     | `/api/similar`              | POST   | 유사 데이터 검색    |
| `chat.py`        | `/api/chat`                 | POST   | 자유형 챗봇         |
| `chat.py`        | `/api/chat/fixed`           | POST   | 고정형 챗봇         |

## 호출 관계

```
endpoints/
    │
    ├── file_upload.py ──→ services/file_upload_service.py
    │                              │
    │                              ├──→ core/unzipper.py
    │                              ├──→ core/db_to_json.py
    │                              ├──→ core/db_parser.py
    │                              ├──→ core/vector_store.py
    │                              └──→ core/llm_analysis.py
    │
    ├── auto_upload.py ──→ services/auto_upload_service.py
    │                              │
    │                              ├──→ utils/preprocess.py
    │                              ├──→ core/vector_store.py
    │                              └──→ core/llm_analysis.py
    │
    ├── chat.py ──→ services/chat_service.py
    │                      │
    │                      └──→ core/chatbot_engine/
    │                                  ├── chat_generator.py
    │                                  ├── intent_classifier.py
    │                                  ├── persona.py
    │                                  └── rag_query.py
    │
    └── ...
```
