# app/api/endpoints/__init__.py
from .file_upload import router as file_upload_router
from .auto_upload import router as auto_upload_router
from .app_data import router as app_data_router
from .user import router as user_router
from .similar import router as similar_router
from .chat import router as chat_router

__all__ = [
    "file_upload_router",
    "auto_upload_router",
    "app_data_router",
    "user_router",
    "similar_router",
    "chat_router",
]
