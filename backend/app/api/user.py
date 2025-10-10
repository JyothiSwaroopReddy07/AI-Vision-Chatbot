"""User management endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.user_service import user_service


router = APIRouter()


class UserProfile(BaseModel):
    id: str
    email: str
    username: str
    full_name: str | None
    affiliation: str | None
    role: str
    created_at: str
    last_login: str | None


class UpdatePreferencesRequest(BaseModel):
    llm_model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    retrieval_k: int | None = None
    preferences: dict | None = None


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        affiliation=current_user.affiliation,
        role=current_user.role,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )


@router.put("/preferences", status_code=status.HTTP_200_OK)
async def update_preferences(
    request: UpdatePreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user preferences"""
    preferences = {}
    
    if request.llm_model is not None:
        preferences["llm_model"] = request.llm_model
    if request.temperature is not None:
        preferences["temperature"] = request.temperature
    if request.max_tokens is not None:
        preferences["max_tokens"] = request.max_tokens
    if request.retrieval_k is not None:
        preferences["retrieval_k"] = request.retrieval_k
    if request.preferences is not None:
        preferences["preferences"] = request.preferences
    
    await user_service.update_user_preferences(
        db=db,
        user_id=str(current_user.id),
        preferences=preferences
    )
    
    return {"status": "updated"}

