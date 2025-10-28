"""Bookmark models for organizing chat sessions"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class BookmarkFolder(Base):
    """Bookmark folder for organizing chat sessions"""
    __tablename__ = "bookmark_folders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(50), nullable=True, default="#6366f1")  # Indigo as default
    icon = Column(String(50), nullable=True, default="folder")  # Icon name for UI
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="bookmark_folders")
    bookmarks = relationship("ChatBookmark", back_populates="folder", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<BookmarkFolder {self.name}>"


class ChatBookmark(Base):
    """Association between bookmark folders and chat sessions"""
    __tablename__ = "chat_bookmarks"
    __table_args__ = (
        UniqueConstraint('folder_id', 'session_id', name='uq_folder_session'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("bookmark_folders.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    notes = Column(Text, nullable=True)  # Optional notes about why this was bookmarked
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    folder = relationship("BookmarkFolder", back_populates="bookmarks")
    session = relationship("ChatSession", back_populates="bookmarks")
    
    def __repr__(self):
        return f"<ChatBookmark folder={self.folder_id} session={self.session_id}>"

