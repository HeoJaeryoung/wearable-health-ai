import os
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# 평가 모드 설정
# ============================================================
# baseline: OpenAI SDK + 수동 파싱 + 기존 프롬프트
# langchain: LangChain Chain + Structured Output + 강화 프롬프트
# finetuned: Azure Llama 3.1 8B Fine-tuned 모델
EVAL_MODE = os.getenv("EVAL_MODE", "baseline")

# ============================================================
# OpenAI 설정
# ============================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("⚠️ OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

# ============================================================
# LLM 설정
# ============================================================
LLM_MODEL_MAIN = "gpt-4o-mini"
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 1000


# ============================================================
# Fine-tuned 모델 설정 (Azure Llama 3.1 8B)
# ============================================================
FINETUNED_ENDPOINT = os.getenv("AZURE_LLAMA_ENDPOINT", "")
FINETUNED_API_KEY = os.getenv("AZURE_LLAMA_API_KEY", "")
FINETUNED_MODEL_NAME = os.getenv("AZURE_LLAMA_MODEL", "llama-3.1-8b-health")
FINETUNED_DEPLOYMENT_NAME = os.getenv("AZURE_LLAMA_DEPLOYMENT", "")


# ============================================================
# API 설정
# ============================================================
API_HOST = "0.0.0.0"
API_PORT = 8000


# ============================================================
# CORS 설정 (보안 강화)
# ============================================================
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://172.30.1.85:3000",
]

# ============================================================
# ChromaDB 설정
# ============================================================
CHROMA_PERSIST_DIR = "./chroma_data"
CHROMA_COLLECTION_NAME = "summaries"

# ============================================================
# RAG 설정
# ============================================================
RAG_TOP_K = 3
RAG_SIMILARITY_THRESHOLD = 0.5

# ============================================================
# 기타 설정
# ============================================================
DEFAULT_DIFFICULTY = "중"
DEFAULT_DURATION = 30
EMBEDDING_BATCH_SIZE = 100
