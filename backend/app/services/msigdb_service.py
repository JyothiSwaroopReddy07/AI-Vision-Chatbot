"""MSigDB service for gene set enrichment and pattern matching"""

import re
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime
from scipy.stats import hypergeom
from statsmodels.stats.multitest import multipletests
from rapidfuzz import fuzz, process
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.msigdb import MsigDBQuery, MsigDBResult
from app.models.user import User

logger = logging.getLogger(__name__)


class MSigDBService:
    """Service for MSigDB gene set enrichment analysis"""
    
    # MSigDB collection information
    COLLECTIONS = {
        "H": {"name": "Hallmark", "description": "Hallmark gene sets"},
        "C1": {"name": "Positional", "description": "Positional gene sets"},
        "C2": {"name": "Curated", "description": "Curated gene sets (CP, CGP)"},
        "C3": {"name": "Motif", "description": "Regulatory target gene sets"},
        "C4": {"name": "Computational", "description": "Computational gene sets"},
        "C5": {"name": "GO", "description": "Gene Ontology gene sets"},
        "C6": {"name": "Oncogenic", "description": "Oncogenic signatures"},
        "C7": {"name": "Immunologic", "description": "Immunologic signatures"},
        "C8": {"name": "Cell Type", "description": "Cell type signatures"},
    }
    
    def __init__(self):
        """Initialize MSigDB service"""
        self.human_db_path = settings.MSIGDB_HUMAN_DB_PATH
        self.mouse_db_path = settings.MSIGDB_MOUSE_DB_PATH
        
    def _get_db_connection(self, species: str) -> sqlite3.Connection:
        """
        Get database connection for specified species
        
        Args:
            species: 'human' or 'mouse'
            
        Returns:
            SQLite connection
        """
        db_path = self.human_db_path if species == "human" else self.mouse_db_path
        
        if not Path(db_path).exists():
            raise FileNotFoundError(
                f"MSigDB database not found at {db_path}. "
                f"Please download the MSigDB SQLite database for {species}."
            )
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def parse_gene_query(self, query: str) -> List[str]:
        """
        Parse gene query string into list of gene symbols
        
        Handles:
        - Comma-separated: "TP53, BRCA1, EGFR"
        - Space-separated: "TP53 BRCA1 EGFR"
        - Newline-separated
        - Mixed separators
        
        Args:
            query: Gene query string
            
        Returns:
            List of cleaned gene symbols
        """
        # Replace various separators with commas
        query = re.sub(r'[,;\s\n\t]+', ',', query)
        
        # Split and clean
        genes = [gene.strip().upper() for gene in query.split(',') if gene.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_genes = []
        for gene in genes:
            if gene not in seen:
                seen.add(gene)
                unique_genes.append(gene)
        
        return unique_genes
    
    def detect_species(self, genes: List[str]) -> str:
        """
        Auto-detect species from gene naming patterns
        
        Human genes: Usually all uppercase (TP53, BRCA1)
        Mouse genes: Usually first letter uppercase (Tp53, Brca1)
        
        Args:
            genes: List of gene symbols
            
        Returns:
            'human', 'mouse', or 'both' if unclear
        """
        if not genes:
            return 'both'
        
        uppercase_count = sum(1 for gene in genes if gene.isupper() and len(gene) > 1)
        mixed_case_count = sum(1 for gene in genes if gene[0].isupper() and not gene.isupper() and len(gene) > 1)
        
        # If majority are all uppercase, likely human
        if uppercase_count > len(genes) * 0.6:
            return 'human'
        
        # If majority are mixed case, likely mouse
        if mixed_case_count > len(genes) * 0.6:
            return 'mouse'
        
        # Unclear - search both
        return 'both'
    
    def find_exact_matches(
        self,
        genes: List[str],
        species: str,
        collections: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find gene sets with exact gene symbol matches
        
        Args:
            genes: List of gene symbols
            species: 'human' or 'mouse'
            collections: List of collection codes to search (e.g., ['C2', 'H'])
            
        Returns:
            List of matching gene sets with statistics
        """
        conn = self._get_db_connection(species)
        cursor = conn.cursor()
        
        try:
            # Build query based on MSigDB schema
            # Typical schema has: gene_set, gene_set_gene_symbol tables
            placeholders = ','.join(['?' for _ in genes])
            
            query = f"""
            SELECT 
                gs.standard_name as gene_set_id,
                gs.standard_name as gene_set_name,
                gs.collection_name as collection,
                gsd.description_brief as description,
                gsd.external_details_URL as external_url,
                COUNT(DISTINCT ge.symbol) as overlap_count,
                (SELECT COUNT(*) FROM gene_set_gene_symbol WHERE gene_set_id = gs.id) as gene_set_size
            FROM gene_set gs
            LEFT JOIN gene_set_details gsd ON gs.id = gsd.gene_set_id
            JOIN gene_set_gene_symbol gsgs ON gs.id = gsgs.gene_set_id
            JOIN gene_symbol ge ON gsgs.gene_symbol_id = ge.id
            WHERE ge.symbol IN ({placeholders})
            """
            
            params = list(genes)
            
            # Filter by collections if specified
            if collections and collections != ['all']:
                collection_placeholders = ','.join(['?' for _ in collections])
                query += f" AND gs.collection_name IN ({collection_placeholders})"
                params.extend(collections)
            
            query += """
            GROUP BY gs.id, gs.standard_name, gs.collection_name, 
                     gsd.description_brief, gsd.external_details_URL
            HAVING overlap_count > 0
            ORDER BY overlap_count DESC, gene_set_size ASC
            LIMIT 1000
            """
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            gene_sets = []
            for row in results:
                gene_set = dict(row)
                
                # Get matched genes for this gene set
                matched_genes_query = """
                SELECT ge.symbol
                FROM gene_set_gene_symbol gsgs
                JOIN gene_symbol ge ON gsgs.gene_symbol_id = ge.id
                WHERE gsgs.gene_set_id = (SELECT id FROM gene_set WHERE standard_name = ?)
                AND ge.symbol IN ({})
                """.format(placeholders)
                
                cursor.execute(matched_genes_query, [gene_set['gene_set_name']] + genes)
                matched_genes = [r[0] for r in cursor.fetchall()]
                
                gene_set['matched_genes'] = matched_genes
                gene_set['sub_collection'] = None  # Not in 2025.1 schema
                gene_set['overlap_percentage'] = (gene_set['overlap_count'] / len(genes)) * 100
                gene_set['species'] = species
                
                gene_sets.append(gene_set)
            
            return gene_sets
            
        finally:
            conn.close()
    
    def find_fuzzy_matches(
        self,
        genes: List[str],
        species: str,
        similarity_threshold: int = 80
    ) -> Dict[str, List[str]]:
        """
        Find fuzzy matches for gene symbols
        
        Args:
            genes: List of gene symbols
            species: 'human' or 'mouse'
            similarity_threshold: Minimum similarity score (0-100)
            
        Returns:
            Dictionary mapping input gene to list of similar genes
        """
        conn = self._get_db_connection(species)
        cursor = conn.cursor()
        
        try:
            # Get all unique gene symbols from database
            cursor.execute("SELECT DISTINCT symbol FROM gene_symbol")
            all_genes = [row[0] for row in cursor.fetchall()]
            
            fuzzy_matches = {}
            
            for gene in genes:
                # Use rapidfuzz for fuzzy matching
                matches = process.extract(
                    gene,
                    all_genes,
                    scorer=fuzz.ratio,
                    score_cutoff=similarity_threshold,
                    limit=5
                )
                
                if matches:
                    fuzzy_matches[gene] = [match[0] for match in matches]
            
            return fuzzy_matches
            
        finally:
            conn.close()
    
    def calculate_enrichment_statistics(
        self,
        overlap_count: int,
        gene_set_size: int,
        query_size: int,
        total_genes: int = 20000  # Approximate total genes in genome
    ) -> Tuple[float, float]:
        """
        Calculate hypergeometric p-value for enrichment
        
        Args:
            overlap_count: Number of genes in both query and gene set
            gene_set_size: Size of the gene set
            query_size: Number of genes in query
            total_genes: Total number of genes in genome
            
        Returns:
            Tuple of (p_value, odds_ratio)
        """
        # Hypergeometric test
        # p-value = probability of observing >= overlap_count by chance
        try:
            p_value = hypergeom.sf(overlap_count - 1, total_genes, gene_set_size, query_size)
            # Check for inf/nan
            if p_value == float('inf') or p_value != p_value or p_value < 0:
                p_value = 1.0  # Default to no significance
        except:
            p_value = 1.0
        
        # Odds ratio
        if gene_set_size < total_genes and query_size < total_genes:
            a = overlap_count
            b = query_size - overlap_count
            c = gene_set_size - overlap_count
            d = total_genes - gene_set_size - b
            
            if b > 0 and c > 0 and d > 0:
                odds_ratio = (a * d) / (b * c)
            else:
                # Return None instead of inf for JSON compliance
                odds_ratio = None
        else:
            odds_ratio = 1.0
        
        # Handle potential inf/nan values for JSON compliance
        if odds_ratio is not None and (odds_ratio == float('inf') or odds_ratio != odds_ratio):
            odds_ratio = None
        
        return float(p_value), odds_ratio
    
    def adjust_p_values(
        self,
        p_values: List[float],
        method: str = 'fdr_bh'
    ) -> List[float]:
        """
        Adjust p-values for multiple testing
        
        Args:
            p_values: List of p-values
            method: Correction method ('bonferroni', 'fdr_bh', etc.)
            
        Returns:
            List of adjusted p-values
        """
        if not p_values:
            return []
        
        try:
            _, adjusted, _, _ = multipletests(p_values, method=method)
            return adjusted.tolist()
        except Exception as e:
            logger.error(f"Error adjusting p-values: {e}")
            return p_values
    
    def get_gene_set_details(
        self,
        gene_set_name: str,
        species: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get full details for a specific gene set
        
        Args:
            gene_set_name: Gene set standard name
            species: 'human' or 'mouse'
            
        Returns:
            Gene set details including all genes
        """
        conn = self._get_db_connection(species)
        cursor = conn.cursor()
        
        try:
            # Get gene set info
            cursor.execute("""
                SELECT 
                    gs.standard_name,
                    gs.collection_name,
                    gsd.systematic_name,
                    gsd.description_brief,
                    gsd.description_full,
                    gsd.external_details_URL
                FROM gene_set gs
                LEFT JOIN gene_set_details gsd ON gs.id = gsd.gene_set_id
                WHERE gs.standard_name = ?
            """, [gene_set_name])
            
            row = cursor.fetchone()
            if not row:
                return None
            
            gene_set = dict(row)
            
            # Get all genes in the set
            cursor.execute("""
                SELECT ge.symbol
                FROM gene_set_gene_symbol gsgs
                JOIN gene_symbol ge ON gsgs.gene_symbol_id = ge.id
                WHERE gsgs.gene_set_id = (SELECT id FROM gene_set WHERE standard_name = ?)
                ORDER BY ge.symbol
            """, [gene_set_name])
            
            genes = [row[0] for row in cursor.fetchall()]
            gene_set['all_genes'] = genes
            gene_set['gene_count'] = len(genes)
            gene_set['species'] = species
            
            return gene_set
            
        finally:
            conn.close()
    
    async def search_gene_sets(
        self,
        db: AsyncSession,
        user: User,
        query: str,
        species: str = "auto",
        search_type: str = "exact",
        collections: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Main search function for gene sets
        
        Args:
            db: Database session
            user: Current user
            query: Gene query string
            species: 'auto', 'human', 'mouse', or 'both'
            search_type: 'exact', 'fuzzy', or 'both'
            collections: List of collection codes or ['all']
            
        Returns:
            Search results with gene sets and statistics
        """
        # Parse gene query
        genes = self.parse_gene_query(query)
        
        if not genes:
            return {
                "query": query,
                "genes": [],
                "species": species,
                "results": [],
                "message": "No valid genes found in query"
            }
        
        # Auto-detect species if needed
        if species == "auto":
            species = self.detect_species(genes)
        
        # Determine which species to search
        species_to_search = []
        if species in ["human", "both"]:
            species_to_search.append("human")
        if species in ["mouse", "both"]:
            species_to_search.append("mouse")
        
        all_results = []
        
        # Search each species
        for sp in species_to_search:
            try:
                # Exact matching
                if search_type in ["exact", "both"]:
                    exact_results = self.find_exact_matches(genes, sp, collections)
                    all_results.extend(exact_results)
                
                # Fuzzy matching
                if search_type in ["fuzzy", "both"]:
                    fuzzy_map = self.find_fuzzy_matches(genes, sp)
                    
                    # Get additional genes from fuzzy matches
                    fuzzy_genes = set()
                    for matches in fuzzy_map.values():
                        fuzzy_genes.update(matches)
                    
                    if fuzzy_genes:
                        fuzzy_results = self.find_exact_matches(
                            list(fuzzy_genes),
                            sp,
                            collections
                        )
                        
                        # Mark as fuzzy match
                        for result in fuzzy_results:
                            result['match_type'] = 'fuzzy'
                        
                        all_results.extend(fuzzy_results)
            
            except FileNotFoundError as e:
                logger.warning(f"Database not found for {sp}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error searching {sp} database: {e}")
                continue
        
        # Calculate enrichment statistics
        for result in all_results:
            p_value, odds_ratio = self.calculate_enrichment_statistics(
                overlap_count=result['overlap_count'],
                gene_set_size=result['gene_set_size'],
                query_size=len(genes)
            )
            result['p_value'] = p_value
            result['odds_ratio'] = odds_ratio
        
        # Adjust p-values
        if all_results:
            p_values = [r['p_value'] for r in all_results]
            adjusted_p_values = self.adjust_p_values(p_values, settings.MSIGDB_FDR_METHOD)
            
            for i, result in enumerate(all_results):
                result['adjusted_p_value'] = adjusted_p_values[i]
        
        # Rank by overlap count and p-value
        all_results.sort(key=lambda x: (-x['overlap_count'], x['p_value']))
        
        for i, result in enumerate(all_results):
            result['rank'] = i + 1
        
        # Store query in database
        msigdb_query = MsigDBQuery(
            user_id=user.id,
            query_text=query,
            genes_list=genes,
            species=species,
            search_type=search_type,
            collections=collections,
            num_results=len(all_results)
        )
        db.add(msigdb_query)
        await db.flush()
        
        # Store results
        for result in all_results[:100]:  # Limit stored results
            # Fetch all genes in this gene set
            gene_set_details = self.get_gene_set_details(
                gene_set_name=result['gene_set_name'],
                species=result['species']
            )
            all_genes_list = gene_set_details.get('all_genes', []) if gene_set_details else []
            
            msigdb_result = MsigDBResult(
                query_id=msigdb_query.id,
                gene_set_id=result['gene_set_id'],
                gene_set_name=result['gene_set_name'],
                collection=result['collection'],
                sub_collection=result.get('sub_collection'),
                description=result.get('description'),
                species=result['species'],
                gene_set_size=result['gene_set_size'],
                overlap_count=result['overlap_count'],
                overlap_percentage=result['overlap_percentage'],
                p_value=result['p_value'],
                adjusted_p_value=result['adjusted_p_value'],
                odds_ratio=result['odds_ratio'],
                matched_genes=result['matched_genes'],
                all_genes=all_genes_list,  # Store all genes in the gene set
                msigdb_url=f"https://www.gsea-msigdb.org/gsea/msigdb/cards/{result['gene_set_name']}",
                external_url=result.get('external_url'),
                rank=result['rank']
            )
            db.add(msigdb_result)
        
        await db.commit()
        
        return {
            "query_id": str(msigdb_query.id),
            "query": query,
            "genes": genes,
            "species": species,
            "search_type": search_type,
            "collections": collections or ["all"],
            "num_results": len(all_results),
            "results": all_results
        }
    
    async def get_user_history(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get user's MSigDB search history
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of results
            
        Returns:
            List of previous searches
        """
        result = await db.execute(
            select(MsigDBQuery)
            .where(MsigDBQuery.user_id == user_id)
            .order_by(MsigDBQuery.created_at.desc())
            .limit(limit)
        )
        queries = result.scalars().all()
        
        return [
            {
                "id": str(q.id),
                "query": q.query_text,
                "genes": q.genes_list,
                "species": q.species,
                "search_type": q.search_type,
                "num_results": q.num_results,
                "created_at": q.created_at.isoformat()
            }
            for q in queries
        ]
    
    def get_collections(self) -> List[Dict[str, str]]:
        """
        Get list of available MSigDB collections
        
        Returns:
            List of collections with metadata
        """
        return [
            {
                "code": code,
                "name": info["name"],
                "description": info["description"]
            }
            for code, info in self.COLLECTIONS.items()
        ]


# Global MSigDB service instance
msigdb_service = MSigDBService()

