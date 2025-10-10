"""Vector store management using ChromaDB"""

from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document

from app.core.config import settings
from app.rag.embeddings import embedding_manager


class VectorStoreManager:
    """Manages ChromaDB vector store for document storage and retrieval"""
    
    def __init__(self):
        self.chroma_client = None
        self.collections = {}
        self._initialize_chroma()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client"""
        try:
            self.chroma_client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT,
                settings=ChromaSettings(
                    anonymized_telemetry=False
                )
            )
        except Exception as e:
            print(f"Error initializing ChromaDB: {e}")
            # Fallback to persistent client
            self.chroma_client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR
            )
    
    def get_or_create_collection(
        self,
        collection_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Chroma:
        """
        Get or create a ChromaDB collection
        
        Args:
            collection_name: Name of the collection
            metadata: Optional metadata for the collection
            
        Returns:
            Chroma vector store instance
        """
        if collection_name not in self.collections:
            # Provide default metadata if none given
            default_metadata = {"description": f"Collection for {collection_name}"}
            self.collections[collection_name] = Chroma(
                client=self.chroma_client,
                collection_name=collection_name,
                embedding_function=embedding_manager.get_embedding_function(),
                collection_metadata=metadata or default_metadata
            )
        
        return self.collections[collection_name]
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[Document],
        ids: Optional[List[str]] = None
    ):
        """
        Add documents to a collection
        
        Args:
            collection_name: Name of the collection
            documents: List of documents to add
            ids: Optional list of document IDs
        """
        collection = self.get_or_create_collection(collection_name)
        collection.add_documents(documents=documents, ids=ids)
    
    def similarity_search(
        self,
        collection_name: str,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Perform similarity search on a collection
        
        Args:
            collection_name: Name of the collection
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of similar documents
        """
        collection = self.get_or_create_collection(collection_name)
        return collection.similarity_search(query, k=k, filter=filter)
    
    def similarity_search_with_score(
        self,
        collection_name: str,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[tuple[Document, float]]:
        """
        Perform similarity search with relevance scores
        
        Args:
            collection_name: Name of the collection
            query: Query text
            k: Number of results to return
            filter: Optional metadata filter
            
        Returns:
            List of (document, score) tuples
        """
        collection = self.get_or_create_collection(collection_name)
        return collection.similarity_search_with_score(query, k=k, filter=filter)
    
    def delete_collection(self, collection_name: str):
        """
        Delete a collection
        
        Args:
            collection_name: Name of the collection to delete
        """
        try:
            self.chroma_client.delete_collection(name=collection_name)
            if collection_name in self.collections:
                del self.collections[collection_name]
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {e}")
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get statistics for a collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dictionary with collection statistics
        """
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            return {
                "name": collection_name,
                "count": collection.count(),
                "metadata": collection.metadata
            }
        except Exception as e:
            return {
                "name": collection_name,
                "count": 0,
                "error": str(e)
            }


# Global vector store manager instance
vector_store_manager = VectorStoreManager()

