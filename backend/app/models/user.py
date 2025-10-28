"""User model"""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User model for authentication and profile"""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    affiliation = Column(String(255))
    role = Column(String(50), default="user")  # user, admin
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="user", cascade="all, delete-orphan")
    pathway_jobs = relationship("PathwayJob", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    bookmark_folders = relationship("BookmarkFolder", back_populates="user", cascade="all, delete-orphan")
    starred_messages = relationship("StarredMessage", back_populates="user", cascade="all, delete-orphan")
    msigdb_queries = relationship("MsigDBQuery", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username}>"

