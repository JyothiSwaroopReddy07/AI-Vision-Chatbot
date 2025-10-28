"""MSigDB API endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.msigdb_service import msigdb_service


router = APIRouter()


class GeneSetSearchRequest(BaseModel):
    """Request model for gene set search"""
    query: str
    species: str = "auto"  # auto, human, mouse, both
    search_type: str = "exact"  # exact, fuzzy, both
    collections: List[str] | None = None  # List of collection codes or ["all"]


class GeneSetResult(BaseModel):
    """Gene set result model"""
    gene_set_id: str
    gene_set_name: str
    collection: str
    sub_collection: str | None
    description: str | None
    species: str
    gene_set_size: int
    overlap_count: int
    overlap_percentage: float
    p_value: float
    adjusted_p_value: float
    odds_ratio: float
    matched_genes: List[str]
    msigdb_url: str | None
    external_url: str | None
    rank: int
    match_type: str | None = "exact"


class GeneSetSearchResponse(BaseModel):
    """Response model for gene set search"""
    query_id: str
    query: str
    genes: List[str]
    species: str
    search_type: str
    collections: List[str]
    num_results: int
    results: List[GeneSetResult]


class GeneSetDetailsResponse(BaseModel):
    """Detailed gene set information"""
    standard_name: str
    systematic_name: str | None
    collection_name: str
    sub_collection_name: str | None
    description_brief: str | None
    description_full: str | None
    external_details_url: str | None
    pmid: str | None
    all_genes: List[str]
    gene_count: int
    species: str


class CollectionInfo(BaseModel):
    """MSigDB collection information"""
    code: str
    name: str
    description: str


class SearchHistoryItem(BaseModel):
    """Search history item"""
    id: str
    query: str
    genes: List[str]
    species: str
    search_type: str
    num_results: int
    created_at: str


@router.post("/search", response_model=GeneSetSearchResponse)
async def search_gene_sets(
    request: GeneSetSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search MSigDB for gene sets matching the query
    
    Args:
        request: Search parameters
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Matching gene sets with statistics
    """
    try:
        results = await msigdb_service.search_gene_sets(
            db=db,
            user=current_user,
            query=request.query,
            species=request.species,
            search_type=request.search_type,
            collections=request.collections
        )
        
        # Convert to response model
        gene_set_results = [
            GeneSetResult(**r) for r in results["results"]
        ]
        
        return GeneSetSearchResponse(
            query_id=results["query_id"],
            query=results["query"],
            genes=results["genes"],
            species=results["species"],
            search_type=results["search_type"],
            collections=results["collections"],
            num_results=results["num_results"],
            results=gene_set_results
        )
    
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching gene sets: {str(e)}"
        )


@router.get("/gene-set/{gene_set_name}", response_model=GeneSetDetailsResponse)
async def get_gene_set_details(
    gene_set_name: str,
    species: str = "human",
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed information for a specific gene set
    
    Args:
        gene_set_name: Gene set standard name
        species: 'human' or 'mouse'
        current_user: Authenticated user
        
    Returns:
        Detailed gene set information
    """
    try:
        details = msigdb_service.get_gene_set_details(gene_set_name, species)
        
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gene set {gene_set_name} not found"
            )
        
        return GeneSetDetailsResponse(**details)
    
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving gene set: {str(e)}"
        )


@router.get("/collections", response_model=List[CollectionInfo])
async def get_collections(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available MSigDB collections
    
    Args:
        current_user: Authenticated user
        
    Returns:
        List of collections
    """
    try:
        collections = msigdb_service.get_collections()
        return [CollectionInfo(**c) for c in collections]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving collections: {str(e)}"
        )


@router.get("/history", response_model=List[SearchHistoryItem])
async def get_search_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's MSigDB search history
    
    Args:
        limit: Maximum number of results
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of previous searches
    """
    try:
        history = await msigdb_service.get_user_history(
            db=db,
            user_id=str(current_user.id),
            limit=limit
        )
        
        return [SearchHistoryItem(**h) for h in history]
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving history: {str(e)}"
        )

