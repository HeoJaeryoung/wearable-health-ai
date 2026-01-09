"""
인증 서비스 - 회원가입, 로그인, 토큰 관리
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.user import User


class AuthService:

    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호 해시 (SHA256)"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """비밀번호 검증"""
        return AuthService.hash_password(password) == password_hash

    @staticmethod
    def generate_token() -> str:
        """간단한 토큰 생성"""
        return secrets.token_hex(32)

    @staticmethod
    def signup(db: Session, email: str, password: str) -> User:
        """회원가입"""
        # 이메일 중복 확인
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("이미 등록된 이메일입니다.")

        # 사용자 생성
        user = User(email=email, password_hash=AuthService.hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def login(db: Session, email: str, password: str) -> dict:
        """로그인"""
        user = db.query(User).filter(User.email == email).first()

        if not user:
            raise ValueError("이메일 또는 비밀번호가 올바르지 않습니다.")

        if not AuthService.verify_password(password, user.password_hash):
            raise ValueError("이메일 또는 비밀번호가 올바르지 않습니다.")

        # 토큰 생성
        token = AuthService.generate_token()

        return {"token": token, "user_id": str(user.id), "email": user.email}

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User:
        """이메일로 사용자 조회"""
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_all_users(db: Session) -> list:
        """모든 사용자 조회 (테스트/디버그용)"""
        return db.query(User).all()
