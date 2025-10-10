"""File upload endpoints"""

from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.file_service import file_service


router = APIRouter()


class FileResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    processing_status: str
    created_at: str


class ProcessingStatusResponse(BaseModel):
    file_id: str
    status: str
    message: str | None = None


@router.post("/file", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload a file for processing"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload file
        uploaded_file = await file_service.upload_file(
            db=db,
            user=current_user,
            filename=file.filename,
            file_content=file_content,
            file_type=file.content_type
        )
        
        # Process file asynchronously (in background)
        # For now, process synchronously
        await file_service.process_file(db, str(uploaded_file.id))
        
        return FileResponse(
            id=str(uploaded_file.id),
            filename=uploaded_file.filename,
            file_type=uploaded_file.file_type,
            file_size=uploaded_file.file_size,
            processing_status=uploaded_file.processing_status,
            created_at=uploaded_file.created_at.isoformat()
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/image", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload an image for OCR processing"""
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Upload file
        uploaded_file = await file_service.upload_file(
            db=db,
            user=current_user,
            filename=file.filename,
            file_content=file_content,
            file_type="image"
        )
        
        # Process file (OCR)
        await file_service.process_file(db, str(uploaded_file.id))
        
        return FileResponse(
            id=str(uploaded_file.id),
            filename=uploaded_file.filename,
            file_type=uploaded_file.file_type,
            file_size=uploaded_file.file_size,
            processing_status=uploaded_file.processing_status,
            created_at=uploaded_file.created_at.isoformat()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status/{file_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get file processing status"""
    from sqlalchemy import select
    from app.models.file import UploadedFile
    
    result = await db.execute(
        select(UploadedFile).where(
            UploadedFile.id == file_id,
            UploadedFile.user_id == current_user.id
        )
    )
    uploaded_file = result.scalar_one_or_none()
    
    if not uploaded_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    return ProcessingStatusResponse(
        file_id=str(uploaded_file.id),
        status=uploaded_file.processing_status,
        message=uploaded_file.file_metadata.get("error") if uploaded_file.file_metadata else None
    )


@router.get("/files", response_model=List[FileResponse])
async def get_user_files(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's uploaded files"""
    files = await file_service.get_user_files(
        db=db,
        user_id=str(current_user.id),
        limit=limit
    )
    
    return [
        FileResponse(
            id=str(f.id),
            filename=f.filename,
            file_type=f.file_type,
            file_size=f.file_size,
            processing_status=f.processing_status,
            created_at=f.created_at.isoformat()
        )
        for f in files
    ]


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an uploaded file"""
    await file_service.delete_file(
        db=db,
        file_id=file_id,
        user_id=str(current_user.id)
    )

