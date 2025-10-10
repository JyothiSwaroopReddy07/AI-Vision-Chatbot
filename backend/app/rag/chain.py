"""RAG chain for question answering with citations"""

from typing import List, Dict, Any, Optional
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain.schema import Document, BaseMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_community.llms import HuggingFacePipeline
from langchain.chains.question_answering import load_qa_chain

from app.core.config import settings
from app.rag.retriever import retriever_manager


class RAGChain:
    """RAG Chain for conversational question answering with citations"""
    
    def __init__(self):
        self.llm = None
        self.retriever = None
        self.memory = None
        self.chain = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure the chain is initialized"""
        if not self._initialized:
            self.llm = self._initialize_llm()
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )
            self._initialized = True
    
    def _initialize_llm(self):
        """Initialize the language model"""
        if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            return ChatOpenAI(
                model=settings.OPENAI_MODEL,
                temperature=settings.TEMPERATURE,
                max_tokens=settings.MAX_TOKENS,
                openai_api_key=settings.OPENAI_API_KEY
            )
        else:
            # Local LLM using HuggingFace
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            
            tokenizer = AutoTokenizer.from_pretrained(settings.LOCAL_LLM_MODEL)
            model = AutoModelForCausalLM.from_pretrained(
                settings.LOCAL_LLM_MODEL,
                device_map=settings.LOCAL_LLM_DEVICE
            )
            
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=settings.MAX_TOKENS,
                temperature=settings.TEMPERATURE,
                top_p=settings.TOP_P
            )
            
            return HuggingFacePipeline(pipeline=pipe)
    
    def create_chain(
        self,
        collection_names: List[str],
        chat_history: Optional[List[tuple]] = None
    ):
        """
        Create a conversational retrieval chain
        
        Args:
            collection_names: List of collection names to search
            chat_history: Optional chat history
        """
        # Create retriever for multiple collections
        if len(collection_names) == 1:
            self.retriever = retriever_manager.get_basic_retriever(collection_names[0])
        else:
            # For multiple collections, we'll handle this in the query method
            self.retriever = retriever_manager.get_basic_retriever(collection_names[0])
        
        # Create memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        # Add existing chat history if provided
        if chat_history:
            for human, ai in chat_history:
                self.memory.chat_memory.add_user_message(human)
                self.memory.chat_memory.add_ai_message(ai)
        
        # Create custom prompt
        prompt_template = """You are a specialized AI assistant for vision research and eye biology. 
Your role is to provide accurate, scientific answers based on the provided research literature.

Use the following pieces of context from scientific literature to answer the question. 
If you don't know the answer or if the context doesn't contain relevant information, say so honestly.
Always cite your sources by mentioning the relevant research when possible.

Context:
{context}

Chat History:
{chat_history}

Question: {question}

Please provide a detailed, accurate answer based on the context above. Include relevant citations.

Answer:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "chat_history", "question"]
        )
        
        # Create chain
        self.chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever,
            memory=self.memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": PROMPT},
            verbose=True
        )
    
    def query(
        self,
        question: str,
        collection_names: Optional[List[str]] = None,
        chat_history: Optional[List[tuple]] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG chain
        
        Args:
            question: User question
            collection_names: Optional list of collections to search
            chat_history: Optional chat history
            
        Returns:
            Dictionary with answer and source documents
        """
        # Create chain if not exists or if collection changed
        if self.chain is None:
            if not collection_names:
                collection_names = ["pubmed_abstracts"]
            self.create_chain(collection_names, chat_history)
        
        # Query the chain
        result = self.chain({"question": question})
        
        # Extract answer and sources
        answer = result["answer"]
        source_documents = result.get("source_documents", [])
        
        # Format citations
        citations = self._format_citations(source_documents)
        
        return {
            "answer": answer,
            "source_documents": source_documents,
            "citations": citations
        }
    
    def query_with_custom_retrieval(
        self,
        question: str,
        collection_names: List[str],
        k: int = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Query with custom retrieval from multiple collections
        
        Args:
            question: User question
            collection_names: List of collections to search
            k: Number of documents to retrieve
            chat_history: Optional chat history
            
        Returns:
            Dictionary with answer and source documents
        """
        k = k or settings.RETRIEVAL_K
        
        # Retrieve documents from all collections
        retrieved_docs = retriever_manager.retrieve_documents(
            query=question,
            collection_names=collection_names,
            k=k
        )
        
        # Format chat history for prompt
        chat_history_text = ""
        if chat_history:
            for msg in chat_history[-5:]:  # Last 5 messages
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    chat_history_text += f"Human: {content}\n"
                elif role == "assistant":
                    chat_history_text += f"Assistant: {content}\n"
        
        # Create context from retrieved documents
        context = "\n\n".join([
            f"[Source {i+1}]: {doc.page_content}"
            for i, doc in enumerate(retrieved_docs)
        ])
        
        # Create prompt
        prompt = f"""You are a specialized AI assistant for vision research and eye biology.
Your role is to provide accurate, scientific answers based on the provided research literature.

Context from scientific literature:
{context}

Chat History:
{chat_history_text}

Question: {question}

Please provide a detailed, accurate answer based on the context above. Cite sources by referring to [Source N] when applicable.

Answer:"""
        
        # Get response from LLM
        if hasattr(self.llm, 'predict'):
            answer = self.llm.predict(prompt)
        else:
            answer = self.llm(prompt)
        
        # Format citations
        citations = self._format_citations(retrieved_docs)
        
        return {
            "answer": answer,
            "source_documents": retrieved_docs,
            "citations": citations
        }
    
    def _format_citations(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """
        Format source documents into citation objects
        
        Args:
            documents: List of source documents
            
        Returns:
            List of citation dictionaries
        """
        citations = []
        
        for i, doc in enumerate(documents):
            metadata = doc.metadata
            
            citation = {
                "source_type": metadata.get("source", "unknown"),
                "source_id": metadata.get("pmid") or metadata.get("source"),
                "title": metadata.get("title", "Untitled"),
                "authors": metadata.get("authors"),
                "journal": metadata.get("journal"),
                "publication_date": metadata.get("publication_date"),
                "url": metadata.get("url"),
                "excerpt": doc.page_content[:500],  # First 500 chars
                "relevance_score": metadata.get("score", 0.0)
            }
            
            citations.append(citation)
        
        return citations
    
    def clear_memory(self):
        """Clear conversation memory"""
        if self.memory:
            self.memory.clear()


# Global RAG chain instance - lazy loaded
rag_chain = None

def get_rag_chain():
    """Get or create RAG chain instance"""
    global rag_chain
    if rag_chain is None:
        rag_chain = RAGChain()
    return rag_chain

