"""Starred message models"""

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Text, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


class StarredMessage(Base):
    """Starred message for quick access to important Q&A pairs"""
    __tablename__ = "starred_messages"
    __table_args__ = (
        UniqueConstraint('user_id', 'message_id', name='uq_user_message_star'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=True)  # The user's question (if message is assistant response)
    answer = Column(Text, nullable=False)  # The response content
    notes = Column(Text, nullable=True)  # Optional notes about why this was starred
    tags = Column(ARRAY(String), nullable=True, default=[])  # Array of tags for organization
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="starred_messages")
    message = relationship("ChatMessage", back_populates="starred_by")
    
    def __repr__(self):
        return f"<StarredMessage user={self.user_id} message={self.message_id}>"

