"""Pathway analysis endpoints"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.pathway_service import pathway_service


router = APIRouter()


class PathwayAnalysisRequest(BaseModel):
    genes: List[str]
    organism: str = "human"
    databases: List[str] | None = None
    p_value_threshold: float | None = None
    correction_method: str | None = None
    session_id: str | None = None


class PathwayAnalysisResponse(BaseModel):
    job_id: str
    status: str
    estimated_time: str = "2-5 minutes"


class PathwayResult(BaseModel):
    pathway_id: str
    pathway_name: str
    database: str
    p_value: float
    adjusted_p_value: float
    odds_ratio: float
    combined_score: float
    overlap: str
    genes: List[str]


class PathwayResultsResponse(BaseModel):
    job_id: str
    status: str
    results: Dict[str, Any] | None = None
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


class JobListResponse(BaseModel):
    id: str
    gene_count: int
    status: str
    created_at: str
    completed_at: str | None = None


@router.post("/analyze", response_model=PathwayAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_pathway(
    request: PathwayAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze gene set for pathway enrichment"""
    try:
        # Validate gene list
        if not request.genes:
            raise ValueError("Gene list cannot be empty")
        
        # Create pathway job
        job = await pathway_service.create_pathway_job(
            db=db,
            user=current_user,
            gene_list=request.genes,
            parameters={
                "organism": request.organism,
                "databases": request.databases,
                "p_value_threshold": request.p_value_threshold,
                "correction_method": request.correction_method
            },
            session_id=request.session_id
        )
        
        # Process job (in production, this should be async with Celery)
        # For now, process synchronously
        await pathway_service.process_pathway_job(db, str(job.id))
        
        return PathwayAnalysisResponse(
            job_id=str(job.id),
            status="processing"
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


@router.get("/results/{job_id}", response_model=PathwayResultsResponse)
async def get_pathway_results(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pathway analysis results"""
    job = await pathway_service.get_job_status(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this job"
        )
    
    return PathwayResultsResponse(
        job_id=str(job.id),
        status=job.status,
        results=job.results,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        completed_at=job.completed_at.isoformat() if job.completed_at else None
    )


@router.get("/export/{job_id}")
async def export_pathway_results(
    job_id: str,
    format: str = "json",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export pathway analysis results"""
    job = await pathway_service.get_job_status(db, job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this job"
        )
    
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job not completed yet"
        )
    
    # Return results based on format
    if format == "json":
        from fastapi.responses import JSONResponse
        return JSONResponse(content=job.results)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported export format"
        )


@router.get("/jobs", response_model=List[JobListResponse])
async def get_user_jobs(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's pathway analysis jobs"""
    jobs = await pathway_service.get_user_jobs(
        db=db,
        user_id=str(current_user.id),
        limit=limit
    )
    
    return [
        JobListResponse(
            id=str(job.id),
            gene_count=len(job.gene_list),
            status=job.status,
            created_at=job.created_at.isoformat(),
            completed_at=job.completed_at.isoformat() if job.completed_at else None
        )
        for job in jobs
    ]

