"""Authentication endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.security import security
from app.services.user_service import user_service


router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: str | None = None
    affiliation: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user_id: str
    email: str
    username: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    try:
        user = await user_service.create_user(
            db=db,
            email=request.email,
            username=request.username,
            password=request.password,
            full_name=request.full_name,
            affiliation=request.affiliation
        )
        
        tokens = user_service.create_tokens(user)
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            user_id=str(user.id),
            email=user.email,
            username=user.username
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login user"""
    user = await user_service.authenticate_user(
        db=db,
        email=request.email,
        password=request.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tokens = user_service.create_tokens(user)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        user_id=str(user.id),
        email=user.email,
        username=user.username
    )

