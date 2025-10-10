"""File service for handling file uploads and processing"""

import os
import uuid
import hashlib
from typing import Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.file import UploadedFile
from app.rag.document_processor import document_processor
from app.rag.vector_store import vector_store_manager
from app.core.config import settings


class FileService:
    """Service for file upload and processing"""
    
    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_file(
        self,
        db: AsyncSession,
        user: User,
        filename: str,
        file_content: bytes,
        file_type: Optional[str] = None
    ) -> UploadedFile:
        """
        Upload a file
        
        Args:
            db: Database session
            user: User object
            filename: Original filename
            file_content: File content as bytes
            file_type: Optional file type
            
        Returns:
            UploadedFile object
        """
        # Validate file extension
        file_ext = Path(filename).suffix.lower().replace(".", "")
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(f"File type .{file_ext} not allowed")
        
        # Validate file size
        file_size = len(file_content)
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise ValueError(f"File size {file_size} exceeds maximum {settings.MAX_UPLOAD_SIZE}")
        
        # Generate unique filename
        file_hash = hashlib.sha256(file_content).hexdigest()[:16]
        unique_filename = f"{user.id}_{file_hash}_{filename}"
        file_path = self.upload_dir / unique_filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create database record
        uploaded_file = UploadedFile(
            user_id=user.id,
            filename=filename,
            file_path=str(file_path),
            file_type=file_type or file_ext,
            file_size=file_size,
            processing_status="pending"
        )
        
        db.add(uploaded_file)
        await db.commit()
        await db.refresh(uploaded_file)
        
        return uploaded_file
    
    async def process_file(
        self,
        db: AsyncSession,
        file_id: str
    ) -> UploadedFile:
        """
        Process an uploaded file
        
        Args:
            db: Database session
            file_id: File ID
            
        Returns:
            Updated UploadedFile object
        """
        # Get file
        result = await db.execute(
            select(UploadedFile).where(UploadedFile.id == file_id)
        )
        uploaded_file = result.scalar_one_or_none()
        
        if not uploaded_file:
            raise ValueError(f"File {file_id} not found")
        
        # Update status
        uploaded_file.processing_status = "processing"
        await db.commit()
        
        try:
            # Process file based on type
            metadata = {
                "user_id": str(uploaded_file.user_id),
                "filename": uploaded_file.filename,
                "file_type": uploaded_file.file_type,
                "upload_date": str(uploaded_file.created_at)
            }
            
            documents = document_processor.process_file(
                file_path=uploaded_file.file_path,
                metadata=metadata
            )
            
            # Extract full text for storage
            extracted_text = "\n\n".join([doc.page_content for doc in documents])
            uploaded_file.extracted_text = extracted_text[:50000]  # Store first 50k chars
            
            # Index in vector store
            collection_name = f"user_{uploaded_file.user_id}_uploads"
            vector_store_manager.add_documents(
                collection_name=collection_name,
                documents=documents,
                ids=[f"{file_id}_{i}" for i in range(len(documents))]
            )
            
            # Update status
            uploaded_file.processing_status = "completed"
            uploaded_file.file_metadata = {
                "chunks": len(documents),
                "indexed_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            uploaded_file.processing_status = "failed"
            uploaded_file.file_metadata = {"error": str(e)}
        
        await db.commit()
        await db.refresh(uploaded_file)
        
        return uploaded_file
    
    async def get_user_files(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50
    ) -> list[UploadedFile]:
        """
        Get user's uploaded files
        
        Args:
            db: Database session
            user_id: User ID
            limit: Number of files to return
            
        Returns:
            List of UploadedFile objects
        """
        result = await db.execute(
            select(UploadedFile)
            .where(UploadedFile.user_id == user_id)
            .order_by(UploadedFile.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def delete_file(
        self,
        db: AsyncSession,
        file_id: str,
        user_id: str
    ):
        """
        Delete an uploaded file
        
        Args:
            db: Database session
            file_id: File ID
            user_id: User ID
        """
        result = await db.execute(
            select(UploadedFile).where(
                UploadedFile.id == file_id,
                UploadedFile.user_id == user_id
            )
        )
        uploaded_file = result.scalar_one_or_none()
        
        if uploaded_file:
            # Delete physical file
            try:
                os.remove(uploaded_file.file_path)
            except:
                pass
            
            # Delete from database
            await db.delete(uploaded_file)
            await db.commit()


# Import datetime for metadata
from datetime import datetime

# Global file service instance
file_service = FileService()

