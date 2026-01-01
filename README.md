# 🏋️ Wearable Health AI - 웨어러블 기반 맞춤형 운동 추천 시스템

> **Samsung Health Connect + AI 기반 개인화 건강 분석 및 운동 추천 서비스**

---

## 📤 파일 업로드 하기 (Push)

```bash
cd C:\AI\project\final_re
git add .
git commit -m "커밋 메시지 입력"
git push origin main
```

---

## 📥 파일 다운로드 하기 (Clone / Pull)

### 처음 다운로드 (Clone)

```bash
git clone https://github.com/YOUR_USERNAME/wearable-health-ai.git
```

### 최신 버전으로 업데이트 (Pull)

```bash
git pull origin main
```

---

## 🖥️ 서버 실행 방법

### 1. PostgreSQL (Docker)

```bash
docker start postgres-wearable
```

또는 새로 생성:

```bash
docker run -d --name postgres-wearable -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=wearable_health -p 5432:5432 postgres:15
```

### 2. Backend (포트 8000)

```bash
cd baseline_backend
conda activate wearable
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend (포트 3000)

```bash
cd frontend
npm start
```

### 4. 갤럭시 앱 (Health Connect)

```bash
cd healthConnect
npx expo start
```

---

## ⚠️ IP 주소 변경 시 수정해야 할 파일들

PC IP가 바뀌면 아래 파일들의 IP 주소를 수정해야 합니다.

### 1. Frontend API 설정

**파일:** `frontend/src/api/wearable.js`

```javascript
const WEARABLE_API = axios.create({
  baseURL: 'http://192.168.45.xxx:8000', // 본인 IP로 변경
});
```

### 2. Backend CORS 설정

**파일:** `baseline_backend/app/config.py`

```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://192.168.XX.xxx:3000",  # 본인 IP로 변경
]
```

### 3. 갤럭시 앱 API 설정

**파일:** `healthConnect/.env`

```
EXPO_PUBLIC_API_URL=http://192.168.45.xxx:8000  # 본인 IP로 변경
```

### 💡 현재 IP 확인 방법

```bash
# Windows
ipconfig

# IPv4 주소 확인 (예: 192.168.45.243)
```

---

## 🔄 자주 쓰는 Git 명령어

| 명령어                   | 설명                    |
| ------------------------ | ----------------------- |
| `git status`             | 변경된 파일 확인        |
| `git add .`              | 모든 변경 파일 스테이징 |
| `git commit -m "메시지"` | 커밋 생성               |
| `git push origin main`   | GitHub에 업로드         |
| `git pull origin main`   | GitHub에서 다운로드     |
| `git log --oneline`      | 커밋 히스토리 확인      |

---

## 📁 프로젝트 구조

```
wearable-health-ai/
├── baseline_backend/           # FastAPI 백엔드 (포트 8000)
│   ├── app/
│   │   ├── api/endpoints/      # API 엔드포인트
│   │   ├── services/           # 비즈니스 로직
│   │   ├── core/               # AI/LLM 핵심 로직
│   │   │   └── chatbot_engine/ # 챗봇 엔진
│   │   └── utils/              # 유틸리티
│   ├── evaluation/             # 성능 평가 시스템
│   └── chroma_data/            # VectorDB 저장소
│
├── frontend/                   # React 웹 (포트 3000)
│   ├── src/
│   │   ├── pages/Wearable/     # 웨어러블 페이지
│   │   ├── components/         # 공통 컴포넌트
│   │   ├── api/                # API 호출
│   │   └── css/                # 스타일
│   └── public/
│
└── healthConnect/              # React Native 앱 (Expo)
    ├── app/                    # Expo Router 페이지
    ├── hooks/                  # Health Connect 연동
    └── components/             # UI 컴포넌트
```

---

## 🛠️ 기술 스택

| 분류         | 기술                                        |
| ------------ | ------------------------------------------- |
| **Frontend** | React 18, CSS Modules                       |
| **Mobile**   | React Native (Expo), Samsung Health Connect |
| **Backend**  | FastAPI, PostgreSQL                         |
| **AI/ML**    | OpenAI GPT-4o-mini, ChromaDB (RAG)          |
| **Infra**    | Docker                                      |

---

## ✨ 주요 기능

### 1. 건강 데이터 수집

- Samsung Health Connect API 연동
- ZIP/DB 파일 업로드 지원
- 23가지 생체 데이터 수집

### 2. AI 건강 분석

- GPT-4o-mini 기반 건강 상태 분석
- 건강 점수 산출 (수면, 활동량, 심박수)
- 맞춤형 운동 강도 권장

### 3. 운동 추천

- LLM 기반 운동 루틴 생성 (기본)
- Rule-based Fallback (검증 실패 시)
- MET 기반 칼로리 계산

### 4. AI 트레이너 챗봇

- 3가지 페르소나 (헬스코치, 트레이너, 영양사)
- RAG 기반 개인화 응답

---

## 📊 API 엔드포인트

| Method | Endpoint                    | 설명                     |
| ------ | --------------------------- | ------------------------ |
| POST   | `/api/file/upload`          | ZIP/DB 파일 업로드       |
| POST   | `/api/auto/upload`          | 앱에서 JSON 업로드       |
| GET    | `/api/user/latest-analysis` | AI 건강 분석 + 운동 추천 |
| POST   | `/api/chat`                 | 트레이너 챗봇            |
| GET    | `/api/app/latest`           | 최신 앱 데이터 조회      |

---

## 📈 버전 히스토리

| 버전     | 설명               | 날짜       |
| -------- | ------------------ | ---------- |
| **v1.0** | Baseline System    | 2026-01-01 |
| v2.0     | LangChain 리팩토링 | 예정       |
| v3.0     | LLM Fine-tuning    | 예정       |

---

## 👤 개발자

- **재령** - AI 시스템 개발
