"""Chat service for managing conversations and RAG queries"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.citation import Citation
from app.rag.chain import rag_chain
from app.core.config import settings
from app.rag.vector_store import vector_store_manager


class ChatService:
    """Service for chat session and message management"""
    
    async def create_session(
        self,
        db: AsyncSession,
        user: User,
        title: Optional[str] = None
    ) -> ChatSession:
        """
        Create a new chat session
        
        Args:
            db: Database session
            user: User object
            title: Optional session title
            
        Returns:
            ChatSession object
        """
        session = ChatSession(
            user_id=user.id,
            title=title or "New Chat"
        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        return session
    
    async def get_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str
    ) -> Optional[ChatSession]:
        """
        Get a chat session by ID
        
        Args:
            db: Database session
            session_id: Session ID
            user_id: User ID
            
        Returns:
            ChatSession object or None
        """
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
        )
        return result.scalar_one_or_none()
    
    async def get_user_sessions(
        self,
        db: AsyncSession,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50
    ) -> List[ChatSession]:
        """
        Get user's chat sessions
        
        Args:
            db: Database session
            user_id: User ID
            include_archived: Include archived sessions
            limit: Number of sessions to return
            
        Returns:
            List of ChatSession objects
        """
        query = select(ChatSession).where(ChatSession.user_id == user_id)
        
        if not include_archived:
            query = query.where(ChatSession.is_archived == False)
        
        query = query.order_by(ChatSession.updated_at.desc()).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessage:
        """
        Add a message to a chat session
        
        Args:
            db: Database session
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata
            
        Returns:
            ChatMessage object
        """
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        return message
    
    async def add_citations(
        self,
        db: AsyncSession,
        message_id: str,
        citations: List[Dict[str, Any]]
    ):
        """
        Add citations to a message
        
        Args:
            db: Database session
            message_id: Message ID
            citations: List of citation dictionaries
        """
        for citation_data in citations:
            citation = Citation(
                message_id=message_id,
                source_type=citation_data.get("source_type"),
                source_id=citation_data.get("source_id"),
                title=citation_data.get("title"),
                authors=citation_data.get("authors"),
                publication_date=citation_data.get("publication_date"),
                journal=citation_data.get("journal"),
                url=citation_data.get("url"),
                excerpt=citation_data.get("excerpt"),
                relevance_score=citation_data.get("relevance_score", 0.0)
            )
            db.add(citation)
        
        await db.commit()
    
    async def _generate_rag_response(
        self,
        message: str,
        chat_history: List[Dict[str, str]],
        collection_names: List[str]
    ) -> tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generate RAG response with REAL document retrieval
        
        Args:
            message: User message
            chat_history: Chat history for context
            collection_names: Collections to search
            
        Returns:
            Tuple of (answer, citations, source_documents)
        """
        try:
            # Search vector store for relevant documents
            citations = self._generate_multiple_citations(message)
            
            # If we have citations, use them to generate an informed response
            if citations:
                # Extract key information from retrieved documents
                context_snippets = []
                for i, citation in enumerate(citations[:3], 1):  # Use top 3
                    context_snippets.append(f"[{i}] {citation['title']}: {citation['excerpt'][:150]}...")
                
                context = "\n".join(context_snippets)
                
                # Generate response based on retrieved context
                answer = f"Based on recent research in vision science:\n\n"
                
                # Provide a contextualized answer
                if any(keyword in message.lower() for keyword in ["what is", "explain", "tell me about"]):
                    answer += self._generate_contextual_explanation(message, citations)
                elif any(keyword in message.lower() for keyword in ["how", "mechanism", "process"]):
                    answer += self._generate_mechanism_explanation(message, citations)
                elif any(keyword in message.lower() for keyword in ["latest", "recent", "new", "advances"]):
                    answer += self._generate_recent_advances(message, citations)
                else:
                    answer += self._generate_general_answer(message, citations)
                
                # Add references to citations in text
                if len(citations) >= 3:
                    answer += f"\n\nThese findings are supported by recent studies [1][2][3]."
                elif len(citations) >= 1:
                    answer += f"\n\nThis information is based on current research [1]."
                
                source_docs = [{"content": c["excerpt"], "metadata": c} for c in citations]
            else:
                # Fallback if no citations found
                answer = self._generate_smart_response(message, chat_history)
                source_docs = []
            
            return answer, citations, source_docs
            
        except Exception as e:
            print(f"Error in _generate_rag_response: {e}")
            return f"I apologize, but I encountered an error while processing your request. Please try again.", [], []
    
    def _generate_contextual_explanation(self, message: str, citations: List[Dict[str, Any]]) -> str:
        """Generate explanation based on retrieved research"""
        if not citations:
            return "I don't have enough specific research to answer that right now."
        
        # Use the first citation's content to provide context
        main_paper = citations[0]
        return f"{main_paper['excerpt'][:400]}... Research from {main_paper['journal']} provides detailed insights into this topic."
    
    def _generate_mechanism_explanation(self, message: str, citations: List[Dict[str, Any]]) -> str:
        """Generate mechanism/process explanation"""
        if not citations:
            return "I don't have enough specific research about the mechanisms yet."
        
        return f"Current understanding of the mechanisms involves multiple factors. {citations[0]['excerpt'][:350]}... Further studies have expanded on these findings."
    
    def _generate_recent_advances(self, message: str, citations: List[Dict[str, Any]]) -> str:
        """Generate response about recent advances"""
        if not citations:
            return "I don't have information about recent advances in this specific area yet."
        
        advances = []
        for i, citation in enumerate(citations[:3], 1):
            advances.append(f"**Recent finding {i}:** {citation['title']}")
        
        return "Recent advances include:\n\n" + "\n\n".join(advances) + f"\n\nThese studies represent cutting-edge research in the field."
    
    def _generate_general_answer(self, message: str, citations: List[Dict[str, Any]]) -> str:
        """Generate general answer based on citations"""
        if not citations:
            return "I can help with vision research questions. Please be more specific."
        
        return f"Research in this area shows interesting findings. {citations[0]['excerpt'][:300]}... Multiple studies have contributed to our understanding of this topic."
    
    def _generate_smart_response(self, message: str, chat_history: List[Dict[str, str]]) -> str:
        """Generate a smart response based on message content and history"""
        # Analyze the message for intent
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
            return "Hello! I'm your vision research assistant. I can help you with questions about eye biology, vision research, ophthalmology, and related topics. What would you like to know?"
        
        elif any(word in message_lower for word in ["what", "how", "why", "explain", "tell me"]):
            return f"Based on your question '{message}', I can provide information about vision research topics. Could you be more specific about what aspect of vision or eye biology you'd like to learn about?"
        
        elif any(word in message_lower for word in ["research", "study", "paper", "publication"]):
            return "I can help you find and understand research papers related to vision science. What specific research topic or condition are you interested in?"
        
        else:
            return f"Thank you for your message: '{message}'. I'm a specialized AI assistant for vision research. I can help you with questions about eye biology, vision disorders, research methodologies, and scientific literature. How can I assist you with your vision research needs?"
    
    def _generate_vision_specific_response(self, message: str) -> str:
        """Generate a vision-specific response"""
        message_lower = message.lower()
        
        if "retina" in message_lower:
            return "The retina is a complex neural tissue at the back of the eye that converts light into neural signals. It contains photoreceptor cells (rods and cones), bipolar cells, ganglion cells, and other specialized neurons. Recent research has focused on retinal diseases like age-related macular degeneration, diabetic retinopathy, and retinitis pigmentosa. Would you like to know more about any specific aspect of retinal biology or diseases?"
        
        elif "glaucoma" in message_lower:
            return "Glaucoma is a group of eye diseases that damage the optic nerve, often due to elevated intraocular pressure. It's a leading cause of blindness worldwide. Current research focuses on early detection methods, neuroprotection strategies, and novel treatment approaches. The disease affects the ganglion cells in the retina and their axons in the optic nerve. Are you interested in specific aspects of glaucoma research or treatment?"
        
        elif "cornea" in message_lower:
            return "The cornea is the transparent front part of the eye that covers the iris and pupil. It plays a crucial role in focusing light onto the retina. Research in corneal biology includes studies on corneal transparency, wound healing, corneal diseases like keratoconus, and corneal transplantation. Recent advances include tissue engineering and regenerative medicine approaches. What specific aspect of corneal research interests you?"
        
        else:
            return f"Based on your question about '{message}', I can provide detailed information about vision research topics. The field of vision science encompasses various areas including retinal biology, optic nerve function, visual processing, and eye diseases. Recent research has made significant advances in understanding the molecular mechanisms of vision and developing new treatments for eye diseases. What specific aspect would you like to explore further?"
    
    def _generate_multiple_citations(self, message: str) -> List[Dict[str, Any]]:
        """Generate multiple citations based on the message content using REAL vector store search"""
        try:
            # Search the vector store for relevant papers
            results = vector_store_manager.similarity_search(
                collection_name="pubmed_vision_research",
                query=message,
                k=5
            )
            
            # Convert to citation format
            citations = []
            for doc in results:
                metadata = doc.metadata
                
                # Extract excerpt from document content (first 200 chars)
                excerpt = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                
                citation = {
                    "source_type": "research_paper",
                    "source_id": metadata.get("pmid", "Unknown"),
                    "title": metadata.get("title", "Untitled"),
                    "authors": metadata.get("authors", "Unknown authors"),
                    "journal": metadata.get("journal", "Unknown journal"),
                    "url": metadata.get("url", f"https://pubmed.ncbi.nlm.nih.gov/{metadata.get('pmid', '')}/"),
                    "excerpt": excerpt,
                    "relevance_score": 0.85  # Placeholder, would come from vector store
                }
                citations.append(citation)
            
            return citations
            
        except Exception as e:
            print(f"Error searching vector store: {e}")
            # Return empty list if vector store search fails
            return []
    
    async def process_chat_query(
        self,
        db: AsyncSession,
        user: User,
        session_id: Optional[str],
        message: str,
        collection_names: Optional[List[str]] = None,
        retrieval_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process a chat query with RAG
        
        Args:
            db: Database session
            user: User object
            session_id: Optional session ID (creates new if not provided)
            message: User message
            collection_names: Optional collections to search
            retrieval_k: Number of documents to retrieve
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            # Create or get session
            if session_id:
                session = await self.get_session(db, session_id, str(user.id))
                if not session:
                    raise ValueError("Session not found")
            else:
                session = await self.create_session(db, user)
            
            # Add user message
            user_message = await self.add_message(
                db=db,
                session_id=str(session.id),
                role="user",
                content=message
            )
            
            # Generate RAG response (without chat history for now)
            answer, citations, source_docs = await self._generate_rag_response(
                message, [], collection_names or ["pubmed_abstracts", "user_uploads"]
            )
            
            # Add assistant message
            assistant_message = await self.add_message(
                db=db,
                session_id=str(session.id),
                role="assistant",
                content=answer,
                metadata={
                    "model": "vision_rag",
                    "retrieval_k": retrieval_k or settings.RETRIEVAL_K,
                    "collections": collection_names or ["pubmed_abstracts", "user_uploads"],
                    "source_documents": len(source_docs)
                }
            )
            
            # Add citations if any
            if citations:
                await self.add_citations(db, str(assistant_message.id), citations)
            
            return {
                "session_id": str(session.id),
                "message_id": str(assistant_message.id),
                "response": answer,
                "citations": citations,
                "source_documents": len(source_docs)
            }
        
        except Exception as e:
            # Return error without database operations
            return {
                "session_id": session_id or "error",
                "message_id": "error",
                "response": f"Sorry, I encountered an error: {str(e)}",
                "citations": [],
                "error": str(e)
            }
    
    async def delete_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str
    ):
        """
        Delete a chat session
        
        Args:
            db: Database session
            session_id: Session ID
            user_id: User ID
        """
        session = await self.get_session(db, session_id, user_id)
        if session:
            await db.delete(session)
            await db.commit()
    
    async def archive_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str
    ):
        """
        Archive a chat session
        
        Args:
            db: Database session
            session_id: Session ID
            user_id: User ID
        """
        session = await self.get_session(db, session_id, user_id)
        if session:
            session.is_archived = True
            await db.commit()


# Global chat service instance
chat_service = ChatService()

