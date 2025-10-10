"""Pathway analysis tasks"""

from app.celery_app import celery_app
from app.services.pathway_service import pathway_service
from app.core.database import SessionLocal


@celery_app.task(name="process_pathway_analysis")
def process_pathway_analysis(job_id: str):
    """
    Celery task to process pathway analysis
    
    Args:
        job_id: Pathway job ID
        
    Returns:
        Job results
    """
    db = SessionLocal()
    
    try:
        # Process pathway job
        job = pathway_service.process_pathway_job(db, job_id)
        
        return {
            "job_id": str(job.id),
            "status": job.status,
            "completed": job.status == "completed"
        }
    
    finally:
        db.close()

