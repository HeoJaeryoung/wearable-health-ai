from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.endpoints.file_upload import router as file_upload_router
from app.api.endpoints.auto_upload import router as auto_upload_router
from app.api.endpoints.app_data import router as app_data_router
from app.api.endpoints.similar import router as similar_router
from app.api.endpoints.chat import router as chat_router
from app.api.endpoints.user import router as user_router
from app.api.endpoints.auth import router as auth_router

from app.database import init_db

from dotenv import load_dotenv

load_dotenv()

print("🔥🔥 FASTAPI SERVER LOADED 🔥🔥")

app = FastAPI(
    title="Health Trainer API",
    description="웨어러블 기반 건강분석 및 운동 추천 서비스",
    version="1.0.0",
    default_response_class=ORJSONResponse,
)

# 앱 시작 시 DB 테이블 생성


@app.on_event("startup")
async def startup_event():
    init_db()
    print("✅ 데이터베이스 테이블 생성 완료")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록

app.include_router(auth_router)  # 인증 추가
app.include_router(file_upload_router)
app.include_router(auto_upload_router)
app.include_router(app_data_router)
app.include_router(similar_router)
app.include_router(chat_router)
app.include_router(user_router)


@app.get("/")
def root():
    return {"message": "API is running"}
