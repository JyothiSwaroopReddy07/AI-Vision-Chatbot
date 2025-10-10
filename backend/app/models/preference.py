"""User preference model"""

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserPreference(Base):
    """User preference model for storing user settings"""
    
    __tablename__ = "user_preferences"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    llm_model = Column(String(100))
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)
    retrieval_k = Column(Integer, default=5)
    preferences = Column(JSONB, default={})
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="preferences")
    
    def __repr__(self):
        return f"<UserPreference for user {self.user_id}>"

