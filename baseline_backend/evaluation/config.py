"""
평가 설정
"""

# API 설정
API_BASE_URL = "http://localhost:8001"

# 평가 설정
EVALUATION_ROUNDS = 3  # 동일 질문 반복 횟수 (일관성 측정)
TIMEOUT_SECONDS = 30  # API 타임아웃

# 테스트 사용자
TEST_USER_ID = "test@evaluation.com"

# 결과 저장 경로
RESULTS_DIR = "evaluation/results"
REPORTS_DIR = "evaluation/reports"
