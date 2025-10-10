"""PubMed service for article extraction and indexing"""

import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from Bio import Entrez
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.pubmed import PubMedArticle
from app.rag.document_processor import document_processor
from app.rag.vector_store import vector_store_manager


class PubMedService:
    """Service for PubMed article extraction and indexing"""
    
    def __init__(self):
        # Configure Entrez
        Entrez.email = settings.PUBMED_EMAIL
        if settings.PUBMED_API_KEY:
            Entrez.api_key = settings.PUBMED_API_KEY
    
    async def search_articles(
        self,
        search_terms: List[str],
        max_results: int = None,
        date_range: Optional[str] = None
    ) -> List[str]:
        """
        Search PubMed for articles
        
        Args:
            search_terms: List of search terms
            max_results: Maximum number of results
            date_range: Date range in format "YYYY-YYYY"
            
        Returns:
            List of PMIDs
        """
        max_results = max_results or settings.PUBMED_MAX_RESULTS
        
        # Build simple query - PubMed is picky about syntax
        if len(search_terms) == 1:
            query = search_terms[0]
        else:
            query = " OR ".join(search_terms)
        
        # Add date range if specified (correct PubMed format)
        if date_range and "-" in date_range:
            start_year, end_year = date_range.split("-")
            query += f" AND {start_year}:{end_year}[pdat]"
        
        try:
            print(f"PubMed query: {query}")
            print(f"Entrez email: {Entrez.email}")
            
            # Search PubMed
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=max_results,
                sort="relevance",
                usehistory="n"
            )
            record = Entrez.read(handle)
            handle.close()
            
            pmids = record["IdList"]
            print(f"Found {len(pmids)} PMIDs")
            return pmids
        
        except Exception as e:
            print(f"Error searching PubMed: {e}")
            print(f"Query was: {query}")
            import traceback
            traceback.print_exc()
            return []
    
    async def fetch_article_details(
        self,
        pmids: List[str],
        db: AsyncSession
    ) -> List[PubMedArticle]:
        """
        Fetch detailed information for articles
        
        Args:
            pmids: List of PubMed IDs
            db: Database session
            
        Returns:
            List of PubMedArticle objects
        """
        articles = []
        batch_size = settings.PUBMED_BATCH_SIZE
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            
            try:
                # Fetch article details
                handle = Entrez.efetch(
                    db="pubmed",
                    id=batch,
                    rettype="xml",
                    retmode="xml"
                )
                records = Entrez.read(handle)
                handle.close()
                
                # Process each article
                for record in records["PubmedArticle"]:
                    article = self._parse_article(record)
                    if article:
                        # Check if already exists
                        existing = await db.execute(
                            select(PubMedArticle).where(PubMedArticle.pmid == article.pmid)
                        )
                        if not existing.scalar_one_or_none():
                            db.add(article)
                            articles.append(article)
                
                await db.commit()
                
                # Rate limiting
                time.sleep(0.34)  # ~3 requests per second
            
            except Exception as e:
                print(f"Error fetching batch {i}-{i+batch_size}: {e}")
                continue
        
        return articles
    
    def _parse_article(self, record: Dict) -> Optional[PubMedArticle]:
        """
        Parse PubMed XML record into article object
        
        Args:
            record: PubMed XML record
            
        Returns:
            PubMedArticle object or None
        """
        try:
            medline_citation = record["MedlineCitation"]
            article_data = medline_citation["Article"]
            
            # Extract PMID
            pmid = str(medline_citation["PMID"])
            
            # Extract title
            title = article_data.get("ArticleTitle", "")
            
            # Extract abstract
            abstract = ""
            if "Abstract" in article_data:
                abstract_texts = article_data["Abstract"].get("AbstractText", [])
                if isinstance(abstract_texts, list):
                    abstract = " ".join([str(text) for text in abstract_texts])
                else:
                    abstract = str(abstract_texts)
            
            # Extract authors
            authors = []
            if "AuthorList" in article_data:
                for author in article_data["AuthorList"]:
                    if "LastName" in author and "ForeName" in author:
                        authors.append(f"{author['ForeName']} {author['LastName']}")
            authors_str = ", ".join(authors)
            
            # Extract journal
            journal = article_data.get("Journal", {}).get("Title", "")
            
            # Extract publication date
            pub_date = None
            if "Journal" in article_data:
                journal_issue = article_data["Journal"].get("JournalIssue", {})
                pub_date_data = journal_issue.get("PubDate", {})
                year = pub_date_data.get("Year")
                month = pub_date_data.get("Month", "01")
                day = pub_date_data.get("Day", "01")
                
                if year:
                    try:
                        # Convert month name to number if needed
                        month_map = {
                            "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                            "May": "05", "Jun": "06", "Jul": "07", "Aug": "08",
                            "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12"
                        }
                        if month in month_map:
                            month = month_map[month]
                        
                        pub_date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date()
                    except:
                        pub_date = None
            
            # Extract DOI
            doi = None
            if "ELocationID" in article_data:
                for eloc in article_data["ELocationID"]:
                    if eloc.attributes.get("EIdType") == "doi":
                        doi = str(eloc)
            
            # Create article object
            article = PubMedArticle(
                pmid=pmid,
                title=title,
                abstract=abstract,
                authors=authors_str,
                journal=journal,
                publication_date=pub_date,
                doi=doi,
                pdf_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            )
            
            return article
        
        except Exception as e:
            print(f"Error parsing article: {e}")
            return None
    
    async def index_articles(
        self,
        articles: List[PubMedArticle],
        collection_name: str = "pubmed_abstracts"
    ):
        """
        Index articles in vector store
        
        Args:
            articles: List of PubMedArticle objects
            collection_name: ChromaDB collection name
        """
        for article in articles:
            try:
                # Process article into documents
                documents = document_processor.process_pubmed_article(
                    pmid=article.pmid,
                    title=article.title,
                    abstract=article.abstract,
                    metadata={
                        "pmid": article.pmid,
                        "title": article.title,
                        "authors": article.authors,
                        "journal": article.journal,
                        "publication_date": str(article.publication_date) if article.publication_date else None,
                        "doi": article.doi,
                        "url": article.pdf_url
                    }
                )
                
                # Add to vector store
                vector_store_manager.add_documents(
                    collection_name=collection_name,
                    documents=documents,
                    ids=[f"{article.pmid}_{i}" for i in range(len(documents))]
                )
                
                print(f"Indexed article {article.pmid}")
            
            except Exception as e:
                print(f"Error indexing article {article.pmid}: {e}")
                continue
    
    async def run_indexing_job(
        self,
        db: AsyncSession,
        search_terms: List[str] = None,
        max_results: int = None,
        date_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete indexing job
        
        Args:
            db: Database session
            search_terms: List of search terms
            max_results: Maximum number of results
            date_range: Date range in format "YYYY-YYYY"
            
        Returns:
            Job statistics
        """
        # Default search terms for vision research
        if not search_terms:
            search_terms = [
                "age-related macular degeneration",
                "glaucoma genetics",
                "retina genomics",
                "diabetic retinopathy",
                "optic nerve",
                "retinal degeneration",
                "vision genetics",
                "eye disease",
                "photoreceptor",
                "retinal pigment epithelium"
            ]
        
        start_time = datetime.now()
        
        # Search for articles
        print(f"Searching PubMed with terms: {search_terms}")
        pmids = await self.search_articles(
            search_terms=search_terms,
            max_results=max_results,
            date_range=date_range
        )
        
        print(f"Found {len(pmids)} articles")
        
        # Fetch article details
        articles = await self.fetch_article_details(pmids, db)
        
        print(f"Fetched details for {len(articles)} articles")
        
        # Index articles
        await self.index_articles(articles)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            "total_found": len(pmids),
            "articles_indexed": len(articles),
            "duration_seconds": duration,
            "search_terms": search_terms,
            "timestamp": end_time.isoformat()
        }


# Global PubMed service instance
pubmed_service = PubMedService()

