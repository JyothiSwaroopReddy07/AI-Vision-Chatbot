"""Starred message service for managing starred Q&A pairs"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from uuid import UUID

from app.models.user import User
from app.models.starred import StarredMessage
from app.models.chat import ChatMessage, ChatSession


class StarredService:
    """Service for starred message management"""
    
    async def star_message(
        self,
        db: AsyncSession,
        user_id: UUID,
        message_id: UUID,
        notes: Optional[str] = None,
        tags: Optional[str] = None
    ) -> Optional[StarredMessage]:
        """
        Star a message
        
        Args:
            db: Database session
            user_id: User ID
            message_id: Message ID
            notes: Optional notes
            tags: Optional comma-separated tags
            
        Returns:
            StarredMessage object or None
        """
        # Verify message exists and belongs to user's session
        message_result = await db.execute(
            select(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                and_(
                    ChatMessage.id == message_id,
                    ChatSession.user_id == user_id
                )
            )
        )
        message = message_result.scalar_one_or_none()
        if not message:
            return None
        
        # Check if already starred
        existing_result = await db.execute(
            select(StarredMessage).where(
                and_(
                    StarredMessage.user_id == user_id,
                    StarredMessage.message_id == message_id
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            # Update existing star if notes or tags provided
            if notes is not None:
                existing.notes = notes
            if tags is not None:
                # Parse tags string into array
                tag_list = [t.strip() for t in tags.split(',')] if tags else []
                existing.tags = tag_list
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            return existing
        
        # Get the session_id
        session_id = message.session_id
        
        # For user messages, the answer is the next assistant message
        # For assistant messages, the question is the previous user message
        question_text = None
        answer_text = message.content
        
        if message.role == 'user':
            # If starring a user message, find the assistant's response
            next_msg_result = await db.execute(
                select(ChatMessage)
                .where(
                    and_(
                        ChatMessage.session_id == session_id,
                        ChatMessage.created_at > message.created_at,
                        ChatMessage.role == 'assistant'
                    )
                )
                .order_by(ChatMessage.created_at)
                .limit(1)
            )
            next_msg = next_msg_result.scalar_one_or_none()
            question_text = message.content
            answer_text = next_msg.content if next_msg else message.content
        else:
            # If starring an assistant message, find the previous user message
            prev_msg_result = await db.execute(
                select(ChatMessage)
                .where(
                    and_(
                        ChatMessage.session_id == session_id,
                        ChatMessage.created_at < message.created_at,
                        ChatMessage.role == 'user'
                    )
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(1)
            )
            prev_msg = prev_msg_result.scalar_one_or_none()
            question_text = prev_msg.content if prev_msg else None
            answer_text = message.content
        
        # Parse tags string into array
        tag_list = [t.strip() for t in tags.split(',')] if tags else []
        
        # Create new starred message
        starred = StarredMessage(
            user_id=user_id,
            message_id=message_id,
            session_id=session_id,
            question=question_text,
            answer=answer_text,
            notes=notes,
            tags=tag_list
        )
        
        db.add(starred)
        await db.commit()
        await db.refresh(starred)
        
        return starred
    
    async def unstar_message(
        self,
        db: AsyncSession,
        user_id: UUID,
        message_id: UUID
    ) -> bool:
        """
        Unstar a message
        
        Args:
            db: Database session
            user_id: User ID
            message_id: Message ID
            
        Returns:
            True if unstarred, False if not found
        """
        result = await db.execute(
            select(StarredMessage).where(
                and_(
                    StarredMessage.user_id == user_id,
                    StarredMessage.message_id == message_id
                )
            )
        )
        starred = result.scalar_one_or_none()
        
        if not starred:
            return False
        
        await db.delete(starred)
        await db.commit()
        
        return True
    
    async def is_message_starred(
        self,
        db: AsyncSession,
        user_id: UUID,
        message_id: UUID
    ) -> bool:
        """
        Check if a message is starred
        
        Args:
            db: Database session
            user_id: User ID
            message_id: Message ID
            
        Returns:
            True if starred, False otherwise
        """
        result = await db.execute(
            select(StarredMessage).where(
                and_(
                    StarredMessage.user_id == user_id,
                    StarredMessage.message_id == message_id
                )
            )
        )
        return result.scalar_one_or_none() is not None
    
    async def get_starred_messages(
        self,
        db: AsyncSession,
        user_id: UUID,
        tag: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all starred messages for a user
        
        Args:
            db: Database session
            user_id: User ID
            tag: Optional tag filter
            limit: Number of messages to return
            offset: Offset for pagination
            
        Returns:
            List of starred message dictionaries with full context
        """
        query = (
            select(StarredMessage, ChatMessage, ChatSession)
            .join(ChatMessage, StarredMessage.message_id == ChatMessage.id)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(StarredMessage.user_id == user_id)
            .options(
                selectinload(StarredMessage.message).selectinload(ChatMessage.citations)
            )
        )
        
        if tag:
            query = query.where(StarredMessage.tags.contains(tag))
        
        query = query.order_by(StarredMessage.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        rows = result.all()
        
        starred_list = []
        for starred, message, session in rows:
            # Get the user message (question) that precedes this assistant message
            user_message_result = await db.execute(
                select(ChatMessage)
                .where(
                    and_(
                        ChatMessage.session_id == session.id,
                        ChatMessage.created_at < message.created_at,
                        ChatMessage.role == "user"
                    )
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(1)
            )
            user_message = user_message_result.scalar_one_or_none()
            
            # Get assistant message (if this is a user message, get the following assistant message)
            assistant_message = None
            if message.role == "user":
                assistant_result = await db.execute(
                    select(ChatMessage)
                    .where(
                        and_(
                            ChatMessage.session_id == session.id,
                            ChatMessage.created_at > message.created_at,
                            ChatMessage.role == "assistant"
                        )
                    )
                    .order_by(ChatMessage.created_at.asc())
                    .limit(1)
                )
                assistant_message = assistant_result.scalar_one_or_none()
            else:
                assistant_message = message
            
            starred_item = {
                "id": str(starred.id),
                "message_id": str(message.id),
                "session_id": str(session.id),
                "session_title": session.title,
                "question": starred.question,
                "answer": starred.answer,
                "notes": starred.notes,
                "tags": starred.tags if starred.tags else [],
                "starred_at": starred.created_at.isoformat(),
                "updated_at": starred.updated_at.isoformat(),
                "message_created_at": message.created_at.isoformat()
            }
            
            starred_list.append(starred_item)
        
        return starred_list
    
    async def update_starred_message(
        self,
        db: AsyncSession,
        starred_id: UUID,
        user_id: UUID,
        notes: Optional[str] = None,
        tags: Optional[str] = None
    ) -> Optional[StarredMessage]:
        """
        Update notes or tags for a starred message
        
        Args:
            db: Database session
            starred_id: Starred message ID
            user_id: User ID (for security check)
            notes: Optional new notes
            tags: Optional new tags
            
        Returns:
            Updated StarredMessage or None
        """
        result = await db.execute(
            select(StarredMessage).where(
                and_(
                    StarredMessage.id == starred_id,
                    StarredMessage.user_id == user_id
                )
            )
        )
        starred = result.scalar_one_or_none()
        
        if not starred:
            return None
        
        if notes is not None:
            starred.notes = notes
        if tags is not None:
            # Parse tags string into array
            tag_list = [t.strip() for t in tags.split(',')] if tags else []
            starred.tags = tag_list
        
        starred.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(starred)
        
        return starred
    
    async def get_starred_count(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """
        Get count of starred messages for a user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Count of starred messages
        """
        result = await db.execute(
            select(StarredMessage).where(StarredMessage.user_id == user_id)
        )
        return len(result.scalars().all())
    
    async def search_starred_messages(
        self,
        db: AsyncSession,
        user_id: UUID,
        search_query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search starred messages by content, notes, or tags
        
        Args:
            db: Database session
            user_id: User ID
            search_query: Search query string
            limit: Maximum results to return
            
        Returns:
            List of matching starred message dictionaries
        """
        search_pattern = f"%{search_query}%"
        
        query = (
            select(StarredMessage, ChatMessage, ChatSession)
            .join(ChatMessage, StarredMessage.message_id == ChatMessage.id)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .where(
                and_(
                    StarredMessage.user_id == user_id,
                    or_(
                        StarredMessage.question.ilike(search_pattern),
                        StarredMessage.answer.ilike(search_pattern),
                        StarredMessage.notes.ilike(search_pattern),
                        ChatSession.title.ilike(search_pattern)
                    )
                )
            )
            .order_by(StarredMessage.created_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        rows = result.all()
        
        # Reuse the same formatting logic as get_starred_messages
        starred_list = []
        for starred, message, session in rows:
            starred_item = {
                "id": str(starred.id),
                "message_id": str(message.id),
                "session_id": str(session.id),
                "session_title": session.title,
                "question": starred.question,
                "answer": starred.answer,
                "notes": starred.notes,
                "tags": starred.tags if starred.tags else [],
                "starred_at": starred.created_at.isoformat(),
                "updated_at": starred.updated_at.isoformat()
            }
            
            starred_list.append(starred_item)
        
        return starred_list


# Global starred service instance
starred_service = StarredService()

