"""PubMed article model"""

import uuid
from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class PubMedArticle(Base):
    """PubMed article model for tracking indexed articles"""
    
    __tablename__ = "pubmed_articles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pmid = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(Text)
    abstract = Column(Text)
    authors = Column(Text)
    journal = Column(String(255))
    publication_date = Column(Date)
    doi = Column(String(255))
    pdf_url = Column(Text)
    indexed_at = Column(DateTime, default=datetime.utcnow)
    embedding_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    
    def __repr__(self):
        return f"<PubMedArticle PMID:{self.pmid}>"

