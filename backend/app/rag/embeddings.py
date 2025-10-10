"""Embedding management for RAG pipeline"""

from typing import List
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


class EmbeddingManager:
    """Manages embedding models for document and query encoding"""
    
    def __init__(self):
        self.embedding_model = None
        self._initialize_embeddings()
    
    def _initialize_embeddings(self):
        """Initialize the embedding model based on configuration"""
        # Check if OpenAI is properly configured
        use_openai = (
            settings.LLM_PROVIDER == "openai" and 
            settings.OPENAI_API_KEY and 
            settings.OPENAI_API_KEY != "" and
            not settings.OPENAI_API_KEY.startswith("your-")
        )
        
        if use_openai:
            print("Initializing OpenAI embeddings...")
            self.embedding_model = OpenAIEmbeddings(
                model=settings.OPENAI_EMBEDDING_MODEL,
                openai_api_key=settings.OPENAI_API_KEY
            )
        else:
            # Use local Hugging Face embeddings (default)
            print(f"Initializing local embeddings: {settings.EMBEDDING_MODEL}")
            self.embedding_model = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={
                    'device': settings.EMBEDDING_DEVICE
                },
                encode_kwargs={
                    'batch_size': settings.EMBEDDING_BATCH_SIZE,
                    'normalize_embeddings': True
                }
            )
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents
        
        Args:
            texts: List of document texts
            
        Returns:
            List of embeddings
        """
        return self.embedding_model.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query
        
        Args:
            text: Query text
            
        Returns:
            Query embedding
        """
        return self.embedding_model.embed_query(text)
    
    def get_embedding_function(self):
        """
        Get the underlying embedding function
        
        Returns:
            Embedding function
        """
        return self.embedding_model


# Global embedding manager instance
embedding_manager = EmbeddingManager()

