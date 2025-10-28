"""Bookmark service for managing bookmark folders and chat bookmarks"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.user import User
from app.models.bookmark import BookmarkFolder, ChatBookmark
from app.models.chat import ChatSession


class BookmarkService:
    """Service for bookmark folder and chat bookmark management"""
    
    async def create_folder(
        self,
        db: AsyncSession,
        user: User,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None
    ) -> BookmarkFolder:
        """
        Create a new bookmark folder
        
        Args:
            db: Database session
            user: User object
            name: Folder name
            description: Optional description
            color: Optional color code
            icon: Optional icon name
            
        Returns:
            BookmarkFolder object
        """
        folder = BookmarkFolder(
            user_id=user.id,
            name=name,
            description=description,
            color=color or "#6366f1",
            icon=icon or "folder"
        )
        
        db.add(folder)
        await db.commit()
        await db.refresh(folder)
        
        return folder
    
    async def get_user_folders(
        self,
        db: AsyncSession,
        user_id: UUID,
        include_bookmark_count: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all bookmark folders for a user
        
        Args:
            db: Database session
            user_id: User ID
            include_bookmark_count: Include count of bookmarks in each folder
            
        Returns:
            List of folder dictionaries with metadata
        """
        query = select(BookmarkFolder).where(BookmarkFolder.user_id == user_id)
        
        if include_bookmark_count:
            query = query.options(selectinload(BookmarkFolder.bookmarks))
        
        query = query.order_by(BookmarkFolder.created_at.desc())
        
        result = await db.execute(query)
        folders = result.scalars().all()
        
        folder_list = []
        for folder in folders:
            folder_dict = {
                "id": str(folder.id),
                "name": folder.name,
                "description": folder.description,
                "color": folder.color,
                "icon": folder.icon,
                "created_at": folder.created_at.isoformat(),
                "updated_at": folder.updated_at.isoformat(),
            }
            
            if include_bookmark_count:
                folder_dict["bookmark_count"] = len(folder.bookmarks)
            
            folder_list.append(folder_dict)
        
        return folder_list
    
    async def get_folder(
        self,
        db: AsyncSession,
        folder_id: UUID,
        user_id: UUID
    ) -> Optional[BookmarkFolder]:
        """
        Get a specific bookmark folder
        
        Args:
            db: Database session
            folder_id: Folder ID
            user_id: User ID (for security check)
            
        Returns:
            BookmarkFolder object or None
        """
        result = await db.execute(
            select(BookmarkFolder)
            .where(
                and_(
                    BookmarkFolder.id == folder_id,
                    BookmarkFolder.user_id == user_id
                )
            )
            .options(selectinload(BookmarkFolder.bookmarks))
        )
        return result.scalar_one_or_none()
    
    async def update_folder(
        self,
        db: AsyncSession,
        folder_id: UUID,
        user_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None
    ) -> Optional[BookmarkFolder]:
        """
        Update a bookmark folder
        
        Args:
            db: Database session
            folder_id: Folder ID
            user_id: User ID (for security check)
            name: Optional new name
            description: Optional new description
            color: Optional new color
            icon: Optional new icon
            
        Returns:
            Updated BookmarkFolder or None
        """
        folder = await self.get_folder(db, folder_id, user_id)
        if not folder:
            return None
        
        if name is not None:
            folder.name = name
        if description is not None:
            folder.description = description
        if color is not None:
            folder.color = color
        if icon is not None:
            folder.icon = icon
        
        folder.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(folder)
        
        return folder
    
    async def delete_folder(
        self,
        db: AsyncSession,
        folder_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete a bookmark folder
        
        Args:
            db: Database session
            folder_id: Folder ID
            user_id: User ID (for security check)
            
        Returns:
            True if deleted, False if not found
        """
        folder = await self.get_folder(db, folder_id, user_id)
        if not folder:
            return False
        
        await db.delete(folder)
        await db.commit()
        
        return True
    
    async def add_chat_to_folder(
        self,
        db: AsyncSession,
        folder_id: UUID,
        session_id: UUID,
        user_id: UUID,
        notes: Optional[str] = None
    ) -> Optional[ChatBookmark]:
        """
        Add a chat session to a bookmark folder
        
        Args:
            db: Database session
            folder_id: Folder ID
            session_id: Chat session ID
            user_id: User ID (for security check)
            notes: Optional notes
            
        Returns:
            ChatBookmark object or None
        """
        # Verify folder belongs to user
        folder = await self.get_folder(db, folder_id, user_id)
        if not folder:
            return None
        
        # Verify session belongs to user
        session_result = await db.execute(
            select(ChatSession).where(
                and_(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                )
            )
        )
        session = session_result.scalar_one_or_none()
        if not session:
            return None
        
        # Check if already bookmarked in this folder
        existing_result = await db.execute(
            select(ChatBookmark).where(
                and_(
                    ChatBookmark.folder_id == folder_id,
                    ChatBookmark.session_id == session_id
                )
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            return existing
        
        # Create bookmark
        bookmark = ChatBookmark(
            folder_id=folder_id,
            session_id=session_id,
            notes=notes
        )
        
        db.add(bookmark)
        
        # Update folder timestamp
        folder.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(bookmark)
        
        return bookmark
    
    async def remove_chat_from_folder(
        self,
        db: AsyncSession,
        folder_id: UUID,
        session_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Remove a chat session from a bookmark folder
        
        Args:
            db: Database session
            folder_id: Folder ID
            session_id: Chat session ID
            user_id: User ID (for security check)
            
        Returns:
            True if removed, False if not found
        """
        # Verify folder belongs to user
        folder = await self.get_folder(db, folder_id, user_id)
        if not folder:
            return False
        
        # Find and delete bookmark
        result = await db.execute(
            select(ChatBookmark).where(
                and_(
                    ChatBookmark.folder_id == folder_id,
                    ChatBookmark.session_id == session_id
                )
            )
        )
        bookmark = result.scalar_one_or_none()
        
        if not bookmark:
            return False
        
        await db.delete(bookmark)
        
        # Update folder timestamp
        folder.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return True
    
    async def get_folder_chats(
        self,
        db: AsyncSession,
        folder_id: UUID,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all chat sessions in a bookmark folder
        
        Args:
            db: Database session
            folder_id: Folder ID
            user_id: User ID (for security check)
            limit: Number of chats to return
            offset: Offset for pagination
            
        Returns:
            List of chat session dictionaries
        """
        # Verify folder belongs to user
        folder = await self.get_folder(db, folder_id, user_id)
        if not folder:
            return []
        
        # Get bookmarked sessions
        result = await db.execute(
            select(ChatBookmark, ChatSession)
            .join(ChatSession, ChatBookmark.session_id == ChatSession.id)
            .where(ChatBookmark.folder_id == folder_id)
            .order_by(ChatBookmark.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        bookmarks = result.all()
        
        chat_list = []
        for bookmark, session in bookmarks:
            chat_list.append({
                "id": str(bookmark.id),  # Bookmark ID (for removing from folder)
                "session_id": str(session.id),  # Session ID (for opening the chat)
                "session_title": session.title,
                "notes": bookmark.notes,
                "created_at": bookmark.created_at.isoformat(),  # When it was bookmarked
                "updated_at": session.updated_at.isoformat(),  # Session's last update
                "is_archived": session.is_archived
            })
        
        return chat_list
    
    async def get_chat_folders(
        self,
        db: AsyncSession,
        session_id: UUID,
        user_id: UUID
    ) -> List[BookmarkFolder]:
        """
        Get all folders that contain a specific chat session
        
        Args:
            db: Database session
            session_id: Chat session ID
            user_id: User ID (for security check)
            
        Returns:
            List of BookmarkFolder objects
        """
        result = await db.execute(
            select(BookmarkFolder)
            .join(ChatBookmark, BookmarkFolder.id == ChatBookmark.folder_id)
            .where(
                and_(
                    ChatBookmark.session_id == session_id,
                    BookmarkFolder.user_id == user_id
                )
            )
            .order_by(BookmarkFolder.name)
        )
        
        return result.scalars().all()


# Global bookmark service instance
bookmark_service = BookmarkService()

