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
        from app.models.chat import ChatMessage
        from uuid import UUID
        
        # Convert string IDs to UUID
        session_uuid = UUID(session_id) if isinstance(session_id, str) else session_id
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_uuid, ChatSession.user_id == user_uuid)
            .options(
                selectinload(ChatSession.messages).selectinload(ChatMessage.citations)
            )
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
        from datetime import date
        
        for citation_data in citations:
            # Parse publication_date if it's a string
            pub_date = citation_data.get("publication_date")
            if pub_date and isinstance(pub_date, str):
                try:
                    # Try to parse year only (e.g., "1988")
                    if len(pub_date) == 4 and pub_date.isdigit():
                        pub_date = date(int(pub_date), 1, 1)
                    elif '-' in pub_date:
                        # Try YYYY-MM-DD format
                        parts = pub_date.split('-')
                        pub_date = date(int(parts[0]), int(parts[1]) if len(parts) > 1 else 1, int(parts[2]) if len(parts) > 2 else 1)
                    else:
                        # Can't parse, set to None
                        pub_date = None
                except:
                    # If parsing fails, set to None
                    pub_date = None
            
            citation = Citation(
                message_id=message_id,
                source_type=citation_data.get("source_type"),
                source_id=citation_data.get("source_id"),
                title=citation_data.get("title"),
                authors=citation_data.get("authors"),
                publication_date=pub_date,
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
        Generate RAG response using LLM with retrieved documents
        
        Args:
            message: User message
            chat_history: Chat history for context
            collection_names: Collections to search
            
        Returns:
            Tuple of (answer, citations, source_documents)
        """
        try:
            # Use the proper RAG chain with LLM
            from app.rag.chain import get_rag_chain
            
            rag_chain = get_rag_chain()
            
            # Convert chat history format
            history_tuples = []
            for msg in chat_history[-5:]:  # Last 5 messages
                if msg.get("role") == "user":
                    history_tuples.append((msg.get("content", ""), ""))
                elif msg.get("role") == "assistant":
                    if history_tuples:
                        history_tuples[-1] = (history_tuples[-1][0], msg.get("content", ""))
            
            # Query the RAG chain with LLM
            result = rag_chain.query_with_custom_retrieval(
                question=message,
                collection_names=collection_names,
                k=5,
                chat_history=chat_history
            )
            
            answer = result["answer"]
            citations = result["citations"]
            source_docs = result["source_documents"]
            
            return answer, citations, source_docs
            
        except Exception as e:
            print(f"Error in _generate_rag_response: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to simple response
            return f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again.", [], []
    
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
            # Get existing session or prepare to create new one
            if session_id:
                session = await self.get_session(db, session_id, str(user.id))
                if not session:
                    raise ValueError("Session not found")
            else:
                # Only create session when we actually have a message to add
                # Generate a title from the first message
                title = message[:50] + "..." if len(message) > 50 else message
                session = await self.create_session(db, user, title=title)
            
            # Build chat history for context BEFORE adding the current message
            # This way the current question isn't included in the context
            chat_history = []
            if session_id:
                # For existing sessions, get the message history
                from sqlalchemy import select
                from app.models.chat import ChatMessage
                
                result = await db.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == str(session.id))
                    .order_by(ChatMessage.created_at)
                )
                messages = result.scalars().all()
                
                # Build history from existing messages (last 10 messages for context)
                for msg in messages[-10:]:
                    chat_history.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Now add the current user message
            user_message = await self.add_message(
                db=db,
                session_id=str(session.id),
                role="user",
                content=message
            )
            
            # Check if it's a simple greeting or casual message
            message_lower = message.lower().strip()
            is_greeting = any(word in message_lower for word in [
                "hi", "hello", "hey", "greetings", "good morning", "good afternoon", 
                "good evening", "howdy", "sup", "what's up", "whats up"
            ])
            is_simple_message = len(message.split()) <= 3 and not any(char in message for char in ["?", "what", "how", "why", "when", "where"])
            
            # Handle greetings without RAG
            if is_greeting and is_simple_message:
                answer = "Hello! I'm your vision research assistant, trained on PubMed scientific literature. I can help you with questions about:\n\n• Eye biology and anatomy\n• Vision disorders and diseases\n• Ophthalmology research\n• Retinal diseases (AMD, diabetic retinopathy, etc.)\n• Glaucoma and optic nerve disorders\n• Gene therapy and CRISPR for eye diseases\n• Single-cell research in vision\n\nWhat would you like to know about vision research?"
                citations = []
                source_docs = []
            else:
                # Generate RAG response with chat history for context
                answer, citations, source_docs = await self._generate_rag_response(
                    message, chat_history, collection_names or ["pubmed_vision_research"]
                )
                
                # Check if the response is out of scope
                if "OUT_OF_SCOPE" in answer.strip():
                    # Replace with user-friendly static message
                    answer = "I apologize, but this question is outside my scope of expertise. I am a specialized AI assistant trained exclusively on PubMed literature related to eye and vision research. I can only answer questions about:\n\n• Eye biology, anatomy, and physiology\n• Vision research and visual neuroscience\n• Ophthalmology and eye diseases\n• Retinal disorders (AMD, diabetic retinopathy, etc.)\n• Glaucoma and optic nerve conditions\n• Corneal diseases and treatments\n• Gene therapy and treatments for eye conditions\n• Visual processing and perception\n\nPlease feel free to ask me any questions related to eye and vision research!"
                    # Clear citations for out-of-scope questions
                    citations = []
                    source_docs = []
            
            # Add assistant message
            assistant_message = await self.add_message(
                db=db,
                session_id=str(session.id),
                role="assistant",
                content=answer,
                metadata={
                    "model": "vision_rag",
                    "retrieval_k": retrieval_k or settings.RETRIEVAL_K,
                    "collections": collection_names or ["pubmed_vision_research"],
                    "source_documents": len(source_docs)
                }
            )
            
            # Add citations only if any exist (will be empty for out-of-scope questions)
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

