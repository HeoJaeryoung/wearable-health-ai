"""
인증 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ============================================================
# Request/Response 스키마
# ============================================================


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    token: str = None
    user_id: str = None
    email: str = None


class UserListResponse(BaseModel):
    success: bool
    users: list


# ============================================================
# API 엔드포인트
# ============================================================


@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignUpRequest, db: Session = Depends(get_db)):
    """회원가입"""
    try:
        if len(request.password) < 6:
            raise HTTPException(
                status_code=400, detail="비밀번호는 6자 이상이어야 합니다."
            )

        user = AuthService.signup(db, request.email, request.password)

        return AuthResponse(
            success=True,
            message="회원가입이 완료되었습니다.",
            user_id=str(user.id),
            email=user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """로그인"""
    try:
        result = AuthService.login(db, request.email, request.password)

        return AuthResponse(
            success=True,
            message="로그인 성공",
            token=result["token"],
            user_id=result["user_id"],
            email=result["email"],
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/users", response_model=UserListResponse)
async def get_users(db: Session = Depends(get_db)):
    """모든 사용자 조회 (테스트/디버그용)"""
    users = AuthService.get_all_users(db)

    return UserListResponse(
        success=True,
        users=[
            {"id": user.id, "email": user.email, "created_at": str(user.created_at)}
            for user in users
        ],
    )


@router.get("/me")
async def get_me():
    """현재 사용자 정보 (토큰 검증용 - 간단 구현)"""
    # 실제로는 토큰 검증 로직 필요
    return {"message": "토큰 검증 필요"}
