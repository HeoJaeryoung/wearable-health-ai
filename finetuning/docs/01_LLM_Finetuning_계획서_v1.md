# LLM Fine-tuning 계획서

## 📋 프로젝트 개요

| 항목          | 내용                                    |
| ------------- | --------------------------------------- |
| **목표**      | 웨어러블 생체 데이터 전문 해석 LLM 구축 |
| **Base 모델** | Llama 3.1 8B Instruct                   |
| **방법**      | LoRA (Low-Rank Adaptation)              |
| **플랫폼**    | Azure AI Foundry                        |
| **데이터**    | 1,500건 (Train 1,200 / Valid 300)       |

---

## 🎯 Fine-tuning 목적

### AS-IS (현재)

- GPT-4o-mini로 일반적인 건강 조언 생성
- 전문 기준(ACSM, WHO) 미적용
- 일관성 없는 응답 형식

### TO-BE (목표)

- **전문 기준 기반** 건강 데이터 해석
- **일관된 형식**의 분석 리포트
- **맞춤형 운동 처방** (카보넨 공식 적용)
- **친근한 코칭** 대화

---

## 📊 학습 데이터 구성

### 총 1,500건

| 카테고리         | 건수  | 비율 | 설명                           |
| ---------------- | ----- | ---- | ------------------------------ |
| 건강 데이터 해석 | 700건 | 47%  | 생체 데이터 → 종합 분석 리포트 |
| 운동 추천        | 500건 | 33%  | 컨디션 기반 맞춤 운동 처방     |
| 코칭 대화        | 300건 | 20%  | 친근한 Q&A 스타일 상담         |

### 데이터 분할

| 구분  | 건수    | 비율 |
| ----- | ------- | ---- |
| Train | 1,200건 | 80%  |
| Valid | 300건   | 20%  |

---

## 🔬 적용 전문 기준

### 1. ACSM Guidelines

- American College of Sports Medicine
- 운동 강도 분류 (저/중/고강도)
- 카보넨 공식 (목표 심박수 계산)

### 2. WHO Physical Activity Guidelines 2020

- 주당 150-300분 중강도 유산소
- 주 2회 이상 근력 운동

### 3. Buchheit (2014)

- 안정시 심박수 모니터링
- +10bpm 이상 상승 시 피로/질병 신호

### 4. Milewski et al. (2014)

- 수면 부족과 부상 위험 상관관계
- 8시간 미만 수면 시 부상 위험 1.7배

---

## 📋 입력 데이터 스키마 (9개 필드)

| #   | 필드명               | 타입  | 단위 | 설명          |
| --- | -------------------- | ----- | ---- | ------------- |
| 1   | `heart_rate`         | int   | bpm  | 현재 심박수   |
| 2   | `resting_heart_rate` | int   | bpm  | 안정시 심박수 |
| 3   | `sleep_hr`           | float | 시간 | 수면 시간     |
| 4   | `steps`              | int   | 보   | 걸음수        |
| 5   | `distance_km`        | float | km   | 이동 거리     |
| 6   | `active_calories`    | int   | kcal | 활동 칼로리   |
| 7   | `oxygen_saturation`  | int   | %    | 산소포화도    |
| 8   | `weight`             | float | kg   | 체중          |
| 9   | `bmi`                | float | -    | 체질량지수    |

---

## 🏗️ 시스템 프롬프트

### 1. 건강 데이터 해석

```
당신은 ACSM 인증 스포츠의학 전문가입니다. 웨어러블 생체 데이터를 분석하여
과학적 근거에 기반한 건강 상태 평가를 제공합니다.

적용 기준:
- ACSM Guidelines for Exercise Testing and Prescription
- WHO Physical Activity Guidelines 2020
- Buchheit (2014) HR monitoring 연구
- Milewski et al. (2014) 수면 연구
```

### 2. 운동 추천

```
당신은 ACSM 인증 운동처방 전문가입니다. 사용자의 건강 상태와 목표를 분석하여
과학적 근거 기반의 맞춤형 운동 프로그램을 설계합니다.

적용 기준:
- ACSM Guidelines for Exercise Testing and Prescription
- 카보넨 공식 (Karvonen Formula)
- WHO Physical Activity Guidelines 2020
```

### 3. 코칭 대화

```
당신은 스포츠의학 지식을 갖춘 친근한 피트니스 코치입니다.
전문 지식을 쉽게 설명하고, 실천 가능한 조언을 제공합니다.
```

---

## ⚙️ Fine-tuning 설정 (예정)

| 파라미터      | 값                    | 설명            |
| ------------- | --------------------- | --------------- |
| Base Model    | Llama 3.1 8B Instruct | Meta 공식 모델  |
| Method        | LoRA                  | 효율적 파인튜닝 |
| Epochs        | 3                     | 학습 반복 횟수  |
| Batch Size    | 4                     | 배치 크기       |
| Learning Rate | 2e-4                  | 학습률          |
| LoRA Rank     | 16                    | LoRA 랭크       |
| LoRA Alpha    | 32                    | LoRA 알파       |

---

## 📁 파일 구조

```
wearable_backend/
└── finetuning/
    ├── scripts/
    │   ├── 01_health_interpretation_generator.py
    │   ├── 02_exercise_prescription_generator.py
    │   ├── 03_coaching_chat_generator.py
    │   └── 04_merge_and_split.py
    ├── data/
    │   ├── train_20251230.jsonl      ← Azure 업로드
    │   └── valid_20251230.jsonl      ← Azure 업로드
    └── docs/
        ├── 01_LLM_Finetuning_계획서.md
        ├── 02_전문기준_정리.md
        └── 03_README.md
```

---

## 🚀 실행 계획

### Day 1 ✅ 완료

- 전문 기준 수집 및 정리
- 학습 데이터 구조 설계

### Day 2 ✅ 완료

- 학습 데이터 생성 (1,500건)
- Train/Valid 분할

### Day 3 (예정)

- Azure AI Foundry Fine-tuning 실행
- 모델 테스트 및 평가
- wearable_backend 통합

---

## 📈 기대 효과

1. **전문성 강화**: ACSM/WHO 기준 적용으로 신뢰도 향상
2. **일관성 확보**: 동일 입력에 일관된 형식의 출력
3. **맞춤화**: 개인 건강 데이터 기반 맞춤 분석
4. **비용 절감**: GPT-4 대비 저렴한 운영 비용
5. **포트폴리오 임팩트**: B2B 헬스케어 전문성 어필
