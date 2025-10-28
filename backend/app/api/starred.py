"""Starred message endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.starred_service import starred_service


router = APIRouter()


class StarMessageRequest(BaseModel):
    message_id: str
    notes: Optional[str] = None
    tags: Optional[str] = None


class UpdateStarredRequest(BaseModel):
    notes: Optional[str] = None
    tags: Optional[str] = None


class StarredMessageResponse(BaseModel):
    id: str
    message_id: str
    session_id: str
    session_title: str
    question: Optional[str]
    answer: str
    notes: Optional[str]
    tags: List[str]
    starred_at: str
    updated_at: str
    message_created_at: Optional[str] = None


class StarStatusResponse(BaseModel):
    is_starred: bool
    starred_count: int


@router.post("/star", status_code=status.HTTP_201_CREATED)
async def star_message(
    request: StarMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Star a message"""
    try:
        message_uuid = UUID(request.message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message ID"
        )
    
    try:
        starred = await starred_service.star_message(
            db=db,
            user_id=current_user.id,
            message_id=message_uuid,
            notes=request.notes,
            tags=request.tags
        )
        
        if not starred:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or does not belong to user"
            )
        
        return {
            "status": "success",
            "starred_id": str(starred.id),
            "message": "Message starred successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error starring message: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to star message: {str(e)}"
        )


@router.delete("/star/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unstar_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unstar a message"""
    try:
        message_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message ID"
        )
    
    success = await starred_service.unstar_message(
        db=db,
        user_id=current_user.id,
        message_id=message_uuid
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Starred message not found"
        )


@router.get("/star/{message_id}/status", response_model=StarStatusResponse)
async def get_star_status(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if a message is starred and get total starred count"""
    try:
        message_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid message ID"
        )
    
    is_starred = await starred_service.is_message_starred(
        db=db,
        user_id=current_user.id,
        message_id=message_uuid
    )
    
    count = await starred_service.get_starred_count(
        db=db,
        user_id=current_user.id
    )
    
    return StarStatusResponse(
        is_starred=is_starred,
        starred_count=count
    )


@router.get("/starred", response_model=List[StarredMessageResponse])
async def get_starred_messages(
    tag: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all starred messages for the current user"""
    starred_messages = await starred_service.get_starred_messages(
        db=db,
        user_id=current_user.id,
        tag=tag,
        limit=limit,
        offset=offset
    )
    
    return [StarredMessageResponse(**msg) for msg in starred_messages]


@router.put("/starred/{starred_id}", response_model=dict)
async def update_starred_message(
    starred_id: str,
    request: UpdateStarredRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update notes or tags for a starred message"""
    try:
        starred_uuid = UUID(starred_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid starred ID"
        )
    
    starred = await starred_service.update_starred_message(
        db=db,
        starred_id=starred_uuid,
        user_id=current_user.id,
        notes=request.notes,
        tags=request.tags
    )
    
    if not starred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Starred message not found"
        )
    
    return {
        "status": "success",
        "message": "Starred message updated successfully"
    }


@router.get("/starred/search", response_model=List[StarredMessageResponse])
async def search_starred_messages(
    query: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search starred messages by content, notes, or tags"""
    if not query or len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters"
        )
    
    results = await starred_service.search_starred_messages(
        db=db,
        user_id=current_user.id,
        search_query=query.strip(),
        limit=limit
    )
    
    return [StarredMessageResponse(**msg) for msg in results]


@router.get("/starred/count")
async def get_starred_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get total count of starred messages"""
    count = await starred_service.get_starred_count(
        db=db,
        user_id=current_user.id
    )
    
    return {"count": count}

