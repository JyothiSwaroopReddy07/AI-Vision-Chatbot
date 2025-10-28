"""Chat endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect as sa_inspect
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.chat_service import chat_service


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    collection_names: List[str] | None = None
    retrieval_k: int | None = None


class Citation(BaseModel):
    source_type: str | None
    source_id: str | None
    title: str | None
    authors: str | None
    journal: str | None
    url: str | None
    excerpt: str | None
    relevance_score: float | None


class SpellCorrection(BaseModel):
    original: str
    corrected: str
    type: str


class ChatResponse(BaseModel):
    session_id: str
    message_id: str
    response: str
    citations: List[Citation]
    source_documents: int
    spell_corrections: List[SpellCorrection] | None = None
    original_query: str | None = None


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    citations: List[Citation] = []


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message and get AI response"""
    try:
        result = await chat_service.process_chat_query(
            db=db,
            user=current_user,
            session_id=request.session_id,
            message=request.message,
            collection_names=request.collection_names,
            retrieval_k=request.retrieval_k
        )
        
        return ChatResponse(
            session_id=result["session_id"],
            message_id=result["message_id"],
            response=result["response"],
            citations=[Citation(**c) for c in result.get("citations", [])],
            source_documents=result.get("source_documents", 0),
            spell_corrections=[SpellCorrection(**c) for c in result.get("spell_corrections", [])] if result.get("spell_corrections") else None,
            original_query=result.get("original_query")
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's chat sessions with optional filtering
    
    Args:
        include_archived: Include archived sessions
        limit: Maximum number of sessions to return
        offset: Number of sessions to skip (for pagination)
        search: Search query for title or content
        start_date: Filter sessions created after this date (ISO format)
        end_date: Filter sessions created before this date (ISO format)
    """
    sessions = await chat_service.get_user_sessions(
        db=db,
        user_id=str(current_user.id),
        include_archived=include_archived,
        limit=limit,
        offset=offset,
        search_query=search,
        start_date=start_date,
        end_date=end_date
    )
    
    return [
        SessionResponse(
            id=str(session.id),
            title=session.title,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
            message_count=len(session.messages) if hasattr(session, 'messages') and session.messages else 0
        )
        for session in sessions
    ]


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a single chat session by ID"""
    from uuid import UUID
    from sqlalchemy import select
    from app.models.chat import ChatSession
    
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.id == session_uuid, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return SessionResponse(
        id=str(session.id),
        title=session.title,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        message_count=0  # We don't need to load messages here
    )


@router.get("/history/{session_id}", response_model=List[MessageResponse])
async def get_chat_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat history for a session"""
    session = await chat_service.get_session(
        db=db,
        session_id=session_id,
        user_id=str(current_user.id)
    )
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    messages = []
    for message in session.messages:
        citations = []
        
        # Check if citations relationship is loaded to avoid lazy loading
        inspector = sa_inspect(message)
        if 'citations' in inspector.unloaded:
            # Citations not loaded, skip them
            message_citations = []
        else:
            # Citations are loaded, safe to access
            message_citations = message.citations
            
        for citation in message_citations:
            citations.append(Citation(
                source_type=citation.source_type,
                source_id=citation.source_id,
                title=citation.title,
                authors=citation.authors,
                journal=citation.journal,
                url=citation.url,
                excerpt=citation.excerpt,
                relevance_score=citation.relevance_score
            ))
        
        messages.append(MessageResponse(
            id=str(message.id),
            role=message.role,
            content=message.content,
            created_at=message.created_at.isoformat(),
            citations=citations
        ))
    
    return messages


@router.delete("/history/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a chat session"""
    await chat_service.delete_session(
        db=db,
        session_id=session_id,
        user_id=str(current_user.id)
    )


@router.post("/sessions/{session_id}/archive", status_code=status.HTTP_200_OK)
async def archive_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Archive a chat session"""
    await chat_service.archive_session(
        db=db,
        session_id=session_id,
        user_id=str(current_user.id)
    )
    
    return {"status": "archived"}

