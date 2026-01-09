# Utils

## 역할

**공통 유틸리티** - 전처리, 플랫폼 감지, 임베딩 변환

## 파일 목록

| 파일                          | 역할                                 | 사용처                                   |
| ----------------------------- | ------------------------------------ | ---------------------------------------- |
| `preprocess.py`               | 건강 데이터 정규화, 요약 텍스트 생성 | auto_upload_service, file_upload_service |
| `platform_detection.py`       | 삼성/애플 플랫폼 자동 감지           | auto_upload_service                      |
| `preprocess_for_embedding.py` | 임베딩용 자연어 변환                 | vector_store                             |

## 처리 흐름

### preprocess.py

```
raw_json (앱/ZIP 데이터)
    │
    ├── normalize_raw()      # 데이터 정규화
    │       │
    │       ├── 수면 시간 변환 (분 ↔ 시간)
    │       ├── 체중/키 단위 변환
    │       ├── BMI 계산
    │       └── 칼로리 처리
    │
    ├── generate_summary_text()  # 요약 텍스트
    │
    └── preprocess_health_json() # 최종 결과
            │
            └── {created_at, summary_text, raw, platform}
```

### platform_detection.py

```
raw_json
    │
    ├── 삼성 전용 키 검사 (stepsCadence, totalCaloriesBurned 등)
    │
    ├── 애플 전용 키 검사 (sleepHours, activeEnergy 등)
    │
    └── 결과: "samsung" | "apple"
```
