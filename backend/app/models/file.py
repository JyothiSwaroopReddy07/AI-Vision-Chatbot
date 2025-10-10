"""Uploaded file model"""

import uuid
from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UploadedFile(Base):
    """Uploaded file model"""
    
    __tablename__ = "uploaded_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_type = Column(String(50))
    file_size = Column(BigInteger)
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    extracted_text = Column(Text)
    file_metadata = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="uploaded_files")
    
    def __repr__(self):
        return f"<UploadedFile {self.filename}>"

