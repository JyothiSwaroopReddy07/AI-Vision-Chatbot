"""User service for authentication and user management"""

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.preference import UserPreference
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from app.core.config import settings


class UserService:
    """Service for user management and authentication"""
    
    async def create_user(
        self,
        db: AsyncSession,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        affiliation: Optional[str] = None
    ) -> User:
        """
        Create a new user
        
        Args:
            db: Database session
            email: User email
            username: Username
            password: Plain text password
            full_name: Optional full name
            affiliation: Optional affiliation
            
        Returns:
            User object
        """
        # Check if user exists
        existing_user = await self.get_user_by_email(db, email)
        if existing_user:
            raise ValueError("User with this email already exists")
        
        existing_username = await self.get_user_by_username(db, username)
        if existing_username:
            raise ValueError("Username already taken")
        
        # Create user
        user = User(
            email=email,
            username=username,
            password_hash=get_password_hash(password),
            full_name=full_name,
            affiliation=affiliation
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create default preferences
        preferences = UserPreference(
            user_id=user.id,
            llm_model=settings.OPENAI_MODEL if settings.LLM_PROVIDER == "openai" else settings.LOCAL_LLM_MODEL,
            temperature=settings.TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
            retrieval_k=settings.RETRIEVAL_K
        )
        db.add(preferences)
        await db.commit()
        
        return user
    
    async def authenticate_user(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user
        
        Args:
            db: Database session
            email: User email
            password: Plain text password
            
        Returns:
            User object if authenticated, None otherwise
        """
        user = await self.get_user_by_email(db, email)
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        return user
    
    async def get_user_by_email(
        self,
        db: AsyncSession,
        email: str
    ) -> Optional[User]:
        """
        Get user by email
        
        Args:
            db: Database session
            email: User email
            
        Returns:
            User object or None
        """
        result = await db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(
        self,
        db: AsyncSession,
        username: str
    ) -> Optional[User]:
        """
        Get user by username
        
        Args:
            db: Database session
            username: Username
            
        Returns:
            User object or None
        """
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(
        self,
        db: AsyncSession,
        user_id: str
    ) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            User object or None
        """
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    def create_tokens(self, user: User) -> dict:
        """
        Create access and refresh tokens for user
        
        Args:
            user: User object
            
        Returns:
            Dictionary with tokens
        """
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def update_user_preferences(
        self,
        db: AsyncSession,
        user_id: str,
        preferences: dict
    ):
        """
        Update user preferences
        
        Args:
            db: Database session
            user_id: User ID
            preferences: Preferences dictionary
        """
        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        user_pref = result.scalar_one_or_none()
        
        if not user_pref:
            user_pref = UserPreference(user_id=user_id)
            db.add(user_pref)
        
        # Update preferences
        for key, value in preferences.items():
            if hasattr(user_pref, key):
                setattr(user_pref, key, value)
        
        user_pref.updated_at = datetime.utcnow()
        await db.commit()


# Global user service instance
user_service = UserService()

