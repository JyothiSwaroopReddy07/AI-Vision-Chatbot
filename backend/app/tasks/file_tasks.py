"""File processing tasks"""

from app.celery_app import celery_app
from app.services.file_service import file_service
from app.core.database import SessionLocal


@celery_app.task(name="process_uploaded_file")
def process_uploaded_file(file_id: str):
    """
    Celery task to process uploaded file
    
    Args:
        file_id: Uploaded file ID
        
    Returns:
        Processing result
    """
    db = SessionLocal()
    
    try:
        # Process file
        uploaded_file = file_service.process_file(db, file_id)
        
        return {
            "file_id": str(uploaded_file.id),
            "status": uploaded_file.processing_status,
            "completed": uploaded_file.processing_status == "completed"
        }
    
    finally:
        db.close()

