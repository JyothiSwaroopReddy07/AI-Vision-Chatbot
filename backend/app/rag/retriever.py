"""Retriever management for RAG pipeline"""

from typing import List, Optional, Dict, Any
from langchain.schema import Document
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CohereRerank, LLMChainExtractor
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

from app.rag.vector_store import vector_store_manager
from app.core.config import settings


class RetrieverManager:
    """Manages document retrieval strategies for RAG"""
    
    def __init__(self):
        self.vector_store = vector_store_manager
    
    def get_basic_retriever(
        self,
        collection_name: str,
        k: int = None,
        filter: Optional[Dict[str, Any]] = None
    ):
        """
        Get basic vector store retriever
        
        Args:
            collection_name: Name of the collection
            k: Number of documents to retrieve
            filter: Optional metadata filter
            
        Returns:
            Vector store retriever
        """
        k = k or settings.RETRIEVAL_K
        collection = self.vector_store.get_or_create_collection(collection_name)
        
        return collection.as_retriever(
            search_kwargs={
                "k": k,
                "filter": filter
            }
        )
    
    def get_mmr_retriever(
        self,
        collection_name: str,
        k: int = None,
        fetch_k: int = 20,
        lambda_mult: float = 0.5
    ):
        """
        Get Maximum Marginal Relevance (MMR) retriever for diverse results
        
        Args:
            collection_name: Name of the collection
            k: Number of documents to retrieve
            fetch_k: Number of documents to fetch before MMR
            lambda_mult: Diversity parameter (0=max diversity, 1=max relevance)
            
        Returns:
            MMR retriever
        """
        k = k or settings.RETRIEVAL_K
        collection = self.vector_store.get_or_create_collection(collection_name)
        
        return collection.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": k,
                "fetch_k": fetch_k,
                "lambda_mult": lambda_mult
            }
        )
    
    def retrieve_documents(
        self,
        query: str,
        collection_names: List[str],
        k: int = None,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Retrieve documents from multiple collections
        
        Args:
            query: Query text
            collection_names: List of collection names to search
            k: Number of documents per collection
            filter: Optional metadata filter
            
        Returns:
            List of retrieved documents
        """
        k = k or settings.RETRIEVAL_K
        all_documents = []
        
        for collection_name in collection_names:
            docs = self.vector_store.similarity_search(
                collection_name=collection_name,
                query=query,
                k=k,
                filter=filter
            )
            all_documents.extend(docs)
        
        return all_documents
    
    def retrieve_with_scores(
        self,
        query: str,
        collection_name: str,
        k: int = None,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[tuple[Document, float]]:
        """
        Retrieve documents with relevance scores
        
        Args:
            query: Query text
            collection_name: Collection name
            k: Number of documents to retrieve
            filter: Optional metadata filter
            
        Returns:
            List of (document, score) tuples
        """
        k = k or settings.RETRIEVAL_K
        
        return self.vector_store.similarity_search_with_score(
            collection_name=collection_name,
            query=query,
            k=k,
            filter=filter
        )
    
    def hybrid_search(
        self,
        query: str,
        collection_name: str,
        documents: List[Document],
        k: int = None
    ) -> List[Document]:
        """
        Perform hybrid search combining vector search and BM25
        
        Args:
            query: Query text
            collection_name: Collection name for vector search
            documents: Documents for BM25 search
            k: Number of documents to retrieve
            
        Returns:
            List of retrieved documents
        """
        k = k or settings.RETRIEVAL_K
        
        # Vector retriever
        vector_retriever = self.get_basic_retriever(collection_name, k=k)
        
        # BM25 retriever
        bm25_retriever = BM25Retriever.from_documents(documents)
        bm25_retriever.k = k
        
        # Ensemble retriever
        ensemble_retriever = EnsembleRetriever(
            retrievers=[vector_retriever, bm25_retriever],
            weights=[0.7, 0.3]  # 70% vector, 30% BM25
        )
        
        return ensemble_retriever.get_relevant_documents(query)


# Global retriever manager instance
retriever_manager = RetrieverManager()

