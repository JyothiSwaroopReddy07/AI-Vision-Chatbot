"""PubMed indexing tasks"""

from app.celery_app import celery_app
from app.services.pubmed_service import pubmed_service
from app.core.database import SessionLocal


@celery_app.task(name="index_pubmed_articles")
def index_pubmed_articles(search_terms, max_results=10000, date_range=None):
    """
    Celery task to index PubMed articles
    
    Args:
        search_terms: List of search terms
        max_results: Maximum number of results
        date_range: Optional date range
        
    Returns:
        Job statistics
    """
    db = SessionLocal()
    
    try:
        # Run indexing job
        result = pubmed_service.run_indexing_job(
            db=db,
            search_terms=search_terms,
            max_results=max_results,
            date_range=date_range
        )
        
        return result
    
    finally:
        db.close()

