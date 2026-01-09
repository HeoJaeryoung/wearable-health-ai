# Fine-tuning 학습 데이터 README

## 📋 개요

웨어러블 생체 데이터 전문 해석을 위한 LLM Fine-tuning 학습 데이터입니다.

| 항목      | 내용                       |
| --------- | -------------------------- |
| 총 데이터 | 1,500건                    |
| Train     | 1,200건 (80%)              |
| Valid     | 300건 (20%)                |
| 형식      | JSONL (OpenAI Chat Format) |

---

## 📁 파일 구조

```
finetuning/
├── scripts/
│   ├── 01_health_interpretation_generator.py  # 건강 해석 (700건)
│   ├── 02_exercise_prescription_generator.py  # 운동 추천 (500건)
│   ├── 03_coaching_chat_generator.py          # 코칭 대화 (300건)
│   └── 04_merge_and_split.py                  # 통합 및 분할
├── data/
│   ├── train_20251230.jsonl                   # 학습 데이터
│   └── valid_20251230.jsonl                   # 검증 데이터
└── docs/
    ├── 01_LLM_Finetuning_계획서.md
    ├── 02_전문기준_정리.md
    └── 03_README.md
```

---

## 📊 데이터 스키마

### 입력 필드 (9개)

| 필드명               | 타입  | 단위 | 설명          |
| -------------------- | ----- | ---- | ------------- |
| `heart_rate`         | int   | bpm  | 현재 심박수   |
| `resting_heart_rate` | int   | bpm  | 안정시 심박수 |
| `sleep_hr`           | float | 시간 | 수면 시간     |
| `steps`              | int   | 보   | 걸음수        |
| `distance_km`        | float | km   | 이동 거리     |
| `active_calories`    | int   | kcal | 활동 칼로리   |
| `oxygen_saturation`  | int   | %    | 산소포화도    |
| `weight`             | float | kg   | 체중          |
| `bmi`                | float | -    | 체질량지수    |

### JSONL 형식

```json
{
  "messages": [
    { "role": "system", "content": "시스템 프롬프트..." },
    { "role": "user", "content": "사용자 입력..." },
    { "role": "assistant", "content": "AI 응답..." }
  ]
}
```

---

## 🚀 로컬 실행 방법

### 1. 환경 설정

```bash
cd wearable_backend/finetuning/scripts
```

### 2. 데이터 생성

```bash
# 개별 실행
python 01_health_interpretation_generator.py
python 02_exercise_prescription_generator.py
python 03_coaching_chat_generator.py
python 04_merge_and_split.py

# 또는 순차 실행
python 01_health_interpretation_generator.py && \
python 02_exercise_prescription_generator.py && \
python 03_coaching_chat_generator.py && \
python 04_merge_and_split.py
```

### 3. 출력 파일

- `train_YYYYMMDD.jsonl` - 학습 데이터
- `valid_YYYYMMDD.jsonl` - 검증 데이터

---

## ☁️ Azure AI Foundry 업로드 가이드

### 1. Azure AI Foundry 접속

1. [Azure AI Foundry](https://ai.azure.com/) 접속
2. 프로젝트 선택 또는 생성

### 2. 데이터 업로드

1. **Fine-tuning** 메뉴 선택
2. **+ Create** 클릭
3. Base Model: **Llama 3.1 8B Instruct** 선택
4. Training data: `train_20251230.jsonl` 업로드
5. Validation data: `valid_20251230.jsonl` 업로드

### 3. 하이퍼파라미터 설정 (권장)

| 파라미터      | 권장값 |
| ------------- | ------ |
| Epochs        | 3      |
| Batch Size    | 4      |
| Learning Rate | 2e-4   |
| LoRA Rank     | 16     |
| LoRA Alpha    | 32     |

### 4. Fine-tuning 실행

1. **Submit** 클릭
2. 예상 소요 시간: 1-3시간
3. 완료 후 모델 엔드포인트 생성

---

## 🔧 wearable_backend 통합

### 1. 환경 변수 설정

```env
# .env
AZURE_FINETUNED_ENDPOINT=https://your-endpoint.azure.com
AZURE_FINETUNED_API_KEY=your-api-key
AZURE_FINETUNED_MODEL_NAME=your-model-name
```

### 2. API 호출 예시

```python
import requests

def call_finetuned_model(health_data: dict) -> str:
    endpoint = os.getenv("AZURE_FINETUNED_ENDPOINT")
    api_key = os.getenv("AZURE_FINETUNED_API_KEY")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": format_health_data(health_data)}
        ]
    }

    response = requests.post(endpoint, headers=headers, json=payload)
    return response.json()["choices"][0]["message"]["content"]
```

---

## 📈 데이터 분포

### 카테고리별

| 카테고리         | 건수  | 비율 |
| ---------------- | ----- | ---- |
| 건강 데이터 해석 | 700건 | 47%  |
| 운동 추천        | 500건 | 33%  |
| 코칭 대화        | 300건 | 20%  |

### 시나리오별 (건강 해석)

| 시나리오 | 건수  | 컨디션 |
| -------- | ----- | ------ |
| optimal  | 100건 | 최적   |
| good     | 150건 | 양호   |
| moderate | 150건 | 보통   |
| caution  | 150건 | 주의   |
| warning  | 100건 | 경고   |
| danger   | 50건  | 위험   |

---

## ✅ 체크리스트

### 데이터 생성 완료

- [x] 건강 데이터 해석 (700건)
- [x] 운동 추천 (500건)
- [x] 코칭 대화 (300건)
- [x] Train/Valid 분할 (80/20)

### Azure 업로드 (예정)

- [ ] train_20251230.jsonl 업로드
- [ ] valid_20251230.jsonl 업로드
- [ ] Fine-tuning Job 생성
- [ ] 모델 배포
- [ ] wearable_backend 통합

---

## 📚 참고 자료

- [Azure AI Foundry 문서](https://learn.microsoft.com/azure/ai-studio/)
- [Llama 3.1 Fine-tuning 가이드](https://ai.meta.com/llama/)
- [ACSM Guidelines](https://www.acsm.org/)
