"""MSigDB models for gene set search queries and results"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class MsigDBQuery(Base):
    """MSigDB search query history"""
    
    __tablename__ = "msigdb_queries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query_text = Column(Text, nullable=False)
    genes_list = Column(JSON, nullable=False)  # List of parsed gene symbols
    species = Column(String(20), nullable=False)  # 'human', 'mouse', 'both'
    search_type = Column(String(20), nullable=False)  # 'exact', 'fuzzy', 'both'
    collections = Column(JSON, nullable=True)  # List of collection names, or null for all
    num_results = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="msigdb_queries")
    results = relationship("MsigDBResult", back_populates="query", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<MsigDBQuery {self.id}: {self.query_text[:50]}>"


class MsigDBResult(Base):
    """Cached MSigDB search results"""
    
    __tablename__ = "msigdb_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("msigdb_queries.id", ondelete="CASCADE"), nullable=False)
    
    # Gene set information
    gene_set_id = Column(String(100), nullable=False)  # MSigDB gene set ID
    gene_set_name = Column(String(500), nullable=False)
    collection = Column(String(50), nullable=False)  # C1, C2, etc.
    sub_collection = Column(String(100), nullable=True)  # CP:KEGG, GO:BP, etc.
    description = Column(Text, nullable=True)
    
    # Species
    species = Column(String(20), nullable=False)  # 'human' or 'mouse'
    
    # Statistics
    gene_set_size = Column(Integer, nullable=False)  # Total genes in this set
    overlap_count = Column(Integer, nullable=False)  # Number of user genes in this set
    overlap_percentage = Column(Float, nullable=False)  # Percentage of user genes
    
    # Enrichment statistics
    p_value = Column(Float, nullable=True)
    adjusted_p_value = Column(Float, nullable=True)
    odds_ratio = Column(Float, nullable=True)
    
    # Gene details
    matched_genes = Column(JSON, nullable=False)  # List of genes from query that matched
    all_genes = Column(JSON, nullable=True)  # All genes in the gene set (optional, can be large)
    
    # URLs and references
    msigdb_url = Column(String(500), nullable=True)
    external_url = Column(String(500), nullable=True)  # Link to original database (KEGG, GO, etc.)
    
    # Ranking
    rank = Column(Integer, nullable=True)  # Rank by overlap or p-value
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    query = relationship("MsigDBQuery", back_populates="results")
    
    def __repr__(self):
        return f"<MsigDBResult {self.gene_set_name}: {self.overlap_count}/{self.gene_set_size}>"

