"""Citation model for source tracking"""

import uuid
from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Citation(Base):
    """Citation model for tracking sources"""
    
    __tablename__ = "citations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50))  # pubmed, uploaded_file, etc.
    source_id = Column(String(255))  # PubMed ID, file hash, etc.
    title = Column(Text)
    authors = Column(Text)
    publication_date = Column(Date)
    journal = Column(String(255))
    url = Column(Text)
    excerpt = Column(Text)
    relevance_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("ChatMessage", back_populates="citations")
    
    def __repr__(self):
        return f"<Citation {self.id} - {self.source_type}>"

