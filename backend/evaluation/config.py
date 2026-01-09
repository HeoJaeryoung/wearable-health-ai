"""
평가 시스템 설정
"""

# API 설정
API_BASE_URL = "http://localhost:8000"

# 평가 설정
EVALUATION_ROUNDS = 3  # 동일 질문 반복 횟수 (일관성 측정)
TIMEOUT_SECONDS = 30  # API 타임아웃

# 테스트 사용자
TEST_USER_ID = "test@eval.com"

# 결과 저장 경로
RESULTS_DIR = "evaluation/results"
REPORTS_DIR = "evaluation/reports"
DATASETS_DIR = "evaluation/datasets"

# 평가 단계
STAGES = ["baseline", "langchain", "finetuned"]

# 데이터셋 설정
DATASET_CONFIG = {
    "health": {
        "file": "health_queries.json",
        "count": 30,
        "api_endpoint": "/api/user/latest-analysis",
    },
    "exercise": {
        "file": "exercise_queries.json",
        "count": 30,
        "api_endpoint": "/api/user/latest-analysis",
    },
    "chat": {"file": "chat_queries.json", "count": 40, "api_endpoint": "/api/chat"},
}
