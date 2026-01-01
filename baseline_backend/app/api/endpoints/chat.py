from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal
from app.services.chat_service import ChatService

router = APIRouter(prefix="/api")
chat_service = ChatService()

# 3가지 캐릭터 타입 정의
CharacterType = Literal[
    "devil_coach",  # 악마 코치
    "angel_coach",  # 천사 코치
    "booster_coach",  # 텐션업 부스터 코치
]


# ================================
# 1) 자유형 챗봇
# ================================
class ChatRequest(BaseModel):
    user_id: str  # 이메일 ID
    message: str
    character: CharacterType = "devil_coach"


@router.post("/chat")
async def chat(req: ChatRequest):

    result = chat_service.handle_chat(
        user_id=req.user_id, message=req.message, character=req.character
    )

    return result


# ================================
# 2) 고정형 챗봇
# ================================
class FixedRequest(BaseModel):
    user_id: str
    question_type: str
    character: CharacterType = "devil_coach"


@router.post("/chat/fixed")
async def chat_fixed(req: FixedRequest):

    result = chat_service.handle_fixed_chat(
        user_id=req.user_id, question_type=req.question_type, character=req.character
    )

    return result
