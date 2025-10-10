"""Pathway analysis service for gene set enrichment"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import gseapy as gp
import pandas as pd
import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.pathway import PathwayJob
from app.models.user import User


class PathwayService:
    """Service for gene set enrichment and pathway analysis"""
    
    def __init__(self):
        self.pathway_databases = settings.PATHWAY_DATABASES
        self.p_value_threshold = settings.PATHWAY_P_VALUE_THRESHOLD
        self.fdr_method = settings.PATHWAY_FDR_METHOD
    
    async def create_pathway_job(
        self,
        db: AsyncSession,
        user: User,
        gene_list: List[str],
        parameters: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> PathwayJob:
        """
        Create a new pathway analysis job
        
        Args:
            db: Database session
            user: User object
            gene_list: List of gene symbols
            parameters: Optional analysis parameters
            session_id: Optional chat session ID
            
        Returns:
            PathwayJob object
        """
        job = PathwayJob(
            user_id=user.id,
            session_id=session_id,
            gene_list=gene_list,
            parameters=parameters or {},
            status="pending"
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        return job
    
    async def run_enrichment_analysis(
        self,
        gene_list: List[str],
        organism: str = "human",
        databases: Optional[List[str]] = None,
        p_value_threshold: Optional[float] = None,
        fdr_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run gene set enrichment analysis
        
        Args:
            gene_list: List of gene symbols
            organism: Organism name (human, mouse, etc.)
            databases: List of pathway databases to use
            p_value_threshold: P-value threshold for significance
            fdr_method: FDR correction method
            
        Returns:
            Dictionary with enrichment results
        """
        databases = databases or self.pathway_databases
        p_value_threshold = p_value_threshold or self.p_value_threshold
        fdr_method = fdr_method or self.fdr_method
        
        all_results = {}
        
        for database in databases:
            try:
                # Run enrichment analysis
                enr = gp.enrichr(
                    gene_list=gene_list,
                    gene_sets=database,
                    organism=organism.capitalize(),
                    outdir=None,  # Don't save to file
                    cutoff=p_value_threshold
                )
                
                # Get results dataframe
                results_df = enr.results
                
                # Filter significant results
                significant = results_df[
                    results_df['Adjusted P-value'] < p_value_threshold
                ].copy()
                
                # Sort by adjusted p-value
                significant = significant.sort_values('Adjusted P-value')
                
                # Convert to dictionary format
                pathways = []
                for _, row in significant.iterrows():
                    pathway = {
                        "pathway_id": row.get("Term", ""),
                        "pathway_name": row.get("Term", ""),
                        "database": database,
                        "p_value": float(row.get("P-value", 1.0)),
                        "adjusted_p_value": float(row.get("Adjusted P-value", 1.0)),
                        "odds_ratio": float(row.get("Odds Ratio", 0.0)),
                        "combined_score": float(row.get("Combined Score", 0.0)),
                        "overlap": row.get("Overlap", ""),
                        "genes": row.get("Genes", "").split(";") if row.get("Genes") else []
                    }
                    pathways.append(pathway)
                
                all_results[database] = {
                    "total_pathways": len(results_df),
                    "significant_pathways": len(pathways),
                    "pathways": pathways[:50]  # Top 50 pathways
                }
            
            except Exception as e:
                print(f"Error analyzing {database}: {e}")
                all_results[database] = {
                    "error": str(e),
                    "total_pathways": 0,
                    "significant_pathways": 0,
                    "pathways": []
                }
        
        return all_results
    
    async def process_pathway_job(
        self,
        db: AsyncSession,
        job_id: str
    ) -> PathwayJob:
        """
        Process a pathway analysis job
        
        Args:
            db: Database session
            job_id: Job ID
            
        Returns:
            Updated PathwayJob object
        """
        # Get job
        result = await db.execute(
            select(PathwayJob).where(PathwayJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Update status
        job.status = "processing"
        await db.commit()
        
        try:
            # Extract parameters
            parameters = job.parameters or {}
            organism = parameters.get("organism", "human")
            databases = parameters.get("databases", self.pathway_databases)
            p_value_threshold = parameters.get("p_value_threshold", self.p_value_threshold)
            
            # Run enrichment analysis
            results = await self.run_enrichment_analysis(
                gene_list=job.gene_list,
                organism=organism,
                databases=databases,
                p_value_threshold=p_value_threshold
            )
            
            # Generate network graph
            network_graph = self._generate_network_graph(results, job.gene_list)
            
            # Combine results
            job.results = {
                "enrichment": results,
                "network": network_graph,
                "summary": self._generate_summary(results)
            }
            job.status = "completed"
            job.completed_at = datetime.utcnow()
        
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
        
        await db.commit()
        await db.refresh(job)
        
        return job
    
    def _generate_network_graph(
        self,
        results: Dict[str, Any],
        gene_list: List[str]
    ) -> Dict[str, Any]:
        """
        Generate network graph from enrichment results
        
        Args:
            results: Enrichment results
            gene_list: Input gene list
            
        Returns:
            Network graph data
        """
        # Create network graph
        G = nx.Graph()
        
        # Add gene nodes
        for gene in gene_list:
            G.add_node(gene, node_type="gene")
        
        # Add pathway nodes and edges
        pathway_count = 0
        for database, db_results in results.items():
            pathways = db_results.get("pathways", [])
            
            for pathway in pathways[:20]:  # Top 20 pathways per database
                pathway_id = f"pathway_{pathway_count}"
                pathway_name = pathway["pathway_name"]
                
                G.add_node(
                    pathway_id,
                    node_type="pathway",
                    name=pathway_name,
                    database=database,
                    p_value=pathway["adjusted_p_value"]
                )
                
                # Add edges between genes and pathways
                for gene in pathway["genes"]:
                    if gene in gene_list:
                        G.add_edge(gene, pathway_id)
                
                pathway_count += 1
        
        # Convert to serializable format
        nodes = []
        for node, data in G.nodes(data=True):
            nodes.append({
                "id": node,
                "type": data.get("node_type", "unknown"),
                "name": data.get("name", node),
                "database": data.get("database"),
                "p_value": data.get("p_value")
            })
        
        edges = []
        for source, target in G.edges():
            edges.append({
                "source": source,
                "target": target
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "gene_nodes": sum(1 for n in nodes if n["type"] == "gene"),
                "pathway_nodes": sum(1 for n in nodes if n["type"] == "pathway")
            }
        }
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary statistics from results
        
        Args:
            results: Enrichment results
            
        Returns:
            Summary statistics
        """
        total_pathways = 0
        significant_pathways = 0
        top_pathways = []
        
        for database, db_results in results.items():
            if "error" not in db_results:
                total_pathways += db_results.get("total_pathways", 0)
                significant_pathways += db_results.get("significant_pathways", 0)
                
                # Get top pathway from each database
                pathways = db_results.get("pathways", [])
                if pathways:
                    top_pathways.append({
                        "database": database,
                        "pathway": pathways[0]["pathway_name"],
                        "p_value": pathways[0]["adjusted_p_value"],
                        "genes": len(pathways[0]["genes"])
                    })
        
        return {
            "total_pathways_tested": total_pathways,
            "significant_pathways_found": significant_pathways,
            "databases_analyzed": len(results),
            "top_pathways_by_database": top_pathways
        }
    
    async def get_job_status(
        self,
        db: AsyncSession,
        job_id: str
    ) -> Optional[PathwayJob]:
        """
        Get pathway job status
        
        Args:
            db: Database session
            job_id: Job ID
            
        Returns:
            PathwayJob object or None
        """
        result = await db.execute(
            select(PathwayJob).where(PathwayJob.id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_jobs(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 10
    ) -> List[PathwayJob]:
        """
        Get user's pathway jobs
        
        Args:
            db: Database session
            user_id: User ID
            limit: Number of jobs to return
            
        Returns:
            List of PathwayJob objects
        """
        result = await db.execute(
            select(PathwayJob)
            .where(PathwayJob.user_id == user_id)
            .order_by(PathwayJob.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()


# Global pathway service instance
pathway_service = PathwayService()

