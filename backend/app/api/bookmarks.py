"""Bookmark endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.bookmark_service import bookmark_service


router = APIRouter()


class CreateFolderRequest(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class UpdateFolderRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class AddChatRequest(BaseModel):
    session_id: str
    notes: Optional[str] = None


class FolderResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    color: str
    icon: str
    created_at: str
    updated_at: str
    bookmark_count: Optional[int] = None


class ChatInFolderResponse(BaseModel):
    id: str  # Bookmark ID
    session_id: str  # Chat session ID
    session_title: str  # Chat title
    notes: Optional[str]  # Bookmark notes
    created_at: str  # When bookmarked
    updated_at: str
    is_archived: bool


@router.post("/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    request: CreateFolderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new bookmark folder"""
    folder = await bookmark_service.create_folder(
        db=db,
        user=current_user,
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon
    )
    
    return FolderResponse(
        id=str(folder.id),
        name=folder.name,
        description=folder.description,
        color=folder.color,
        icon=folder.icon,
        created_at=folder.created_at.isoformat(),
        updated_at=folder.updated_at.isoformat(),
        bookmark_count=0
    )


@router.get("/folders", response_model=List[FolderResponse])
async def get_folders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all bookmark folders for the current user"""
    folders = await bookmark_service.get_user_folders(
        db=db,
        user_id=current_user.id,
        include_bookmark_count=True
    )
    
    return [FolderResponse(**folder) for folder in folders]


@router.get("/folders/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific bookmark folder"""
    try:
        folder_uuid = UUID(folder_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder ID"
        )
    
    folder = await bookmark_service.get_folder(
        db=db,
        folder_id=folder_uuid,
        user_id=current_user.id
    )
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    return FolderResponse(
        id=str(folder.id),
        name=folder.name,
        description=folder.description,
        color=folder.color,
        icon=folder.icon,
        created_at=folder.created_at.isoformat(),
        updated_at=folder.updated_at.isoformat(),
        bookmark_count=len(folder.bookmarks) if folder.bookmarks else 0
    )


@router.put("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    request: UpdateFolderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a bookmark folder"""
    try:
        folder_uuid = UUID(folder_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder ID"
        )
    
    folder = await bookmark_service.update_folder(
        db=db,
        folder_id=folder_uuid,
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        color=request.color,
        icon=request.icon
    )
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )
    
    return FolderResponse(
        id=str(folder.id),
        name=folder.name,
        description=folder.description,
        color=folder.color,
        icon=folder.icon,
        created_at=folder.created_at.isoformat(),
        updated_at=folder.updated_at.isoformat()
    )


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a bookmark folder"""
    try:
        folder_uuid = UUID(folder_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder ID"
        )
    
    success = await bookmark_service.delete_folder(
        db=db,
        folder_id=folder_uuid,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found"
        )


@router.post("/folders/{folder_id}/chats", status_code=status.HTTP_201_CREATED)
async def add_chat_to_folder(
    folder_id: str,
    request: AddChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a chat session to a bookmark folder"""
    try:
        folder_uuid = UUID(folder_id)
        session_uuid = UUID(request.session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder or session ID"
        )
    
    bookmark = await bookmark_service.add_chat_to_folder(
        db=db,
        folder_id=folder_uuid,
        session_id=session_uuid,
        user_id=current_user.id,
        notes=request.notes
    )
    
    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder or session not found"
        )
    
    return {"status": "success", "bookmark_id": str(bookmark.id)}


@router.delete("/folders/{folder_id}/chats/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_chat_from_folder(
    folder_id: str,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a chat session from a bookmark folder"""
    try:
        folder_uuid = UUID(folder_id)
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder or session ID"
        )
    
    success = await bookmark_service.remove_chat_from_folder(
        db=db,
        folder_id=folder_uuid,
        session_id=session_uuid,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found"
        )


@router.get("/folders/{folder_id}/chats", response_model=List[ChatInFolderResponse])
async def get_folder_chats(
    folder_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all chat sessions in a bookmark folder"""
    try:
        folder_uuid = UUID(folder_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid folder ID"
        )
    
    chats = await bookmark_service.get_folder_chats(
        db=db,
        folder_id=folder_uuid,
        user_id=current_user.id,
        limit=limit,
        offset=offset
    )
    
    return [ChatInFolderResponse(**chat) for chat in chats]


@router.get("/sessions/{session_id}/folders")
async def get_session_folders(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all folders that contain a specific session"""
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID"
        )
    
    folders = await bookmark_service.get_chat_folders(
        db=db,
        session_id=session_uuid,
        user_id=current_user.id
    )
    
    return [
        {
            "id": str(folder.id),
            "name": folder.name,
            "color": folder.color,
            "icon": folder.icon
        }
        for folder in folders
    ]

