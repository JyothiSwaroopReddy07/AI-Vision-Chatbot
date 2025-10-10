"""Pathway analysis job model"""

import uuid
from datetime import datetime
from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class PathwayJob(Base):
    """Pathway analysis job model"""
    
    __tablename__ = "pathway_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="SET NULL"))
    gene_list = Column(ARRAY(Text), nullable=False)
    parameters = Column(JSONB, default={})
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    results = Column(JSONB)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="pathway_jobs")
    session = relationship("ChatSession", back_populates="pathway_jobs")
    
    def __repr__(self):
        return f"<PathwayJob {self.id} - {self.status}>"

