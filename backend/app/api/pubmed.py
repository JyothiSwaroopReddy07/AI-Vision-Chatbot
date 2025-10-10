"""PubMed indexing endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_admin_user
from app.models.user import User
from app.services.pubmed_service import pubmed_service
from app.rag.vector_store import vector_store_manager


router = APIRouter()


class IndexingRequest(BaseModel):
    search_terms: List[str]
    max_results: int = 10000
    date_range: str | None = None


class IndexingResponse(BaseModel):
    status: str
    message: str
    job_id: str | None = None


class IndexingStatsResponse(BaseModel):
    total_articles: int
    indexed_articles: int
    collections: List[dict]


@router.post("/index", response_model=IndexingResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_indexing(
    request: IndexingRequest,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger PubMed indexing job (Admin only)
    
    This endpoint starts an asynchronous job to search and index PubMed articles.
    """
    try:
        # In production, this should be a Celery task
        # For now, run synchronously (this will block)
        result = await pubmed_service.run_indexing_job(
            db=db,
            search_terms=request.search_terms,
            max_results=request.max_results,
            date_range=request.date_range
        )
        
        return IndexingResponse(
            status="completed",
            message=f"Indexed {result['articles_indexed']} articles out of {result['total_found']} found",
            job_id=None
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats", response_model=IndexingStatsResponse)
async def get_indexing_stats(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get PubMed indexing statistics (Admin only)
    """
    from sqlalchemy import select, func
    from app.models.pubmed import PubMedArticle
    
    # Get total articles
    result = await db.execute(select(func.count(PubMedArticle.id)))
    total_articles = result.scalar()
    
    # Get indexed articles
    result = await db.execute(
        select(func.count(PubMedArticle.id))
        .where(PubMedArticle.embedding_status == "completed")
    )
    indexed_articles = result.scalar()
    
    # Get collection stats
    collections = []
    for collection_name in ["pubmed_abstracts", "pubmed_fulltext"]:
        try:
            stats = vector_store_manager.get_collection_stats(collection_name)
            collections.append(stats)
        except:
            pass
    
    return IndexingStatsResponse(
        total_articles=total_articles or 0,
        indexed_articles=indexed_articles or 0,
        collections=collections
    )


@router.post("/reindex/{pmid}", status_code=status.HTTP_200_OK)
async def reindex_article(
    pmid: str,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reindex a specific PubMed article (Admin only)
    """
    from sqlalchemy import select
    from app.models.pubmed import PubMedArticle
    
    # Get article
    result = await db.execute(
        select(PubMedArticle).where(PubMedArticle.pmid == pmid)
    )
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    
    # Reindex
    await pubmed_service.index_articles([article])
    
    return {"status": "reindexed", "pmid": pmid}

