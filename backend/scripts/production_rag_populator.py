#!/usr/bin/env python3
"""
PRODUCTION-GRADE RAG POPULATION SYSTEM
=======================================

This script downloads ALL available vision research articles from PubMed:
- Searches PubMed comprehensively
- Downloads abstracts AND PDFs
- Handles rate limiting with exponential backoff
- Implements retry logic for failures
- Saves progress to resume interrupted runs
- Processes and chunks all content
- Indexes in ChromaDB with embeddings
- Expected: 10,000+ articles

Author: Full-Stack AI Engineer
"""

import sys
import os
import time
import json
import asyncio
import hashlib
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import get_db
from app.services.pubmed_service import PubMedService
from app.rag.vector_store import vector_store_manager
from app.rag.document_processor import document_processor
from langchain.schema import Document
from Bio import Entrez
import PyPDF2
import io


# Configure Entrez
Entrez.email = settings.PUBMED_EMAIL
if settings.PUBMED_API_KEY:
    Entrez.api_key = settings.PUBMED_API_KEY


# Comprehensive vision research search terms
COMPREHENSIVE_SEARCH_TERMS = [
    # Retinal diseases (most important)
    "retinal degeneration",
    "age related macular degeneration",
    "diabetic retinopathy",
    "retinitis pigmentosa",
    "macular edema",
    "retinal dystrophy",
    "choroidal neovascularization",
    "geographic atrophy",
    
    # Glaucoma
    "glaucoma",
    "primary open angle glaucoma",
    "normal tension glaucoma",
    "angle closure glaucoma",
    "optic nerve head cupping",
    
    # Retinal cell biology
    "retinal ganglion cell",
    "photoreceptor",
    "rod photoreceptor",
    "cone photoreceptor",
    "retinal pigment epithelium",
    "muller cell",
    "amacrine cell",
    "bipolar cell",
    "horizontal cell",
    
    # Single-cell and omics
    "single cell RNA seq retina",
    "single cell transcriptomics eye",
    "spatial transcriptomics retina",
    "retinal cell atlas",
    "retinal proteomics",
    "retinal metabolomics",
    
    # Cornea
    "corneal disease",
    "keratoconus",
    "corneal dystrophy",
    "corneal endothelium",
    "corneal epithelium",
    "limbal stem cell",
    
    # Optic nerve
    "optic neuropathy",
    "optic nerve regeneration",
    "optic neuritis",
    "anterior ischemic optic neuropathy",
    
    # Visual system
    "visual cortex plasticity",
    "visual pathway",
    "lateral geniculate nucleus",
    
    # AI and computational
    "deep learning ophthalmology",
    "machine learning retinal imaging",
    "artificial intelligence diabetic retinopathy",
    "automated fundus analysis",
    "OCT segmentation deep learning",
    
    # Gene therapy
    "gene therapy inherited retinal disease",
    "AAV retina",
    "CRISPR eye disease",
    "gene editing retina",
    "optogenetics vision restoration",
    
    # Stem cells and regeneration
    "retinal organoid",
    "iPSC retina",
    "retinal progenitor cell",
    "photoreceptor transplantation",
    "retinal regeneration",
    
    # Imaging modalities
    "optical coherence tomography",
    "OCT angiography",
    "fundus autofluorescence",
    "adaptive optics retinal imaging",
    "scanning laser ophthalmoscopy",
    
    # Drug delivery
    "intravitreal injection",
    "sustained release eye",
    "ocular drug delivery",
    "nanoparticle retina",
    
    # Inflammation and immunity
    "uveitis",
    "retinal inflammation",
    "microglia retina",
    "immune privilege eye",
    
    # Vascular
    "retinal vascular disease",
    "branch retinal vein occlusion",
    "central retinal artery occlusion",
    "retinal angiogenesis",
]


class ProductionRAGPopulator:
    """Production-grade RAG population system"""
    
    def __init__(
        self,
        progress_file: str = "/data/rag_progress.json",
        pdf_dir: str = "/data/pubmed_pdfs",
        max_articles_per_query: int = 500,
        rate_limit_delay: float = 0.34,  # ~3 requests/sec
        collection_name: str = "pubmed_vision_research"
    ):
        self.progress_file = progress_file
        self.pdf_dir = Path(pdf_dir)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.max_articles_per_query = max_articles_per_query
        self.rate_limit_delay = rate_limit_delay
        self.collection_name = collection_name
        
        self.progress = self._load_progress()
        self.pubmed_service = PubMedService()
        
        self.stats = {
            "total_queries": 0,
            "articles_downloaded": 0,
            "pdfs_downloaded": 0,
            "chunks_indexed": 0,
            "errors": 0,
            "start_time": datetime.now().isoformat()
        }
    
    def _load_progress(self) -> Dict:
        """Load progress from file"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            "completed_queries": [],
            "downloaded_pmids": [],
            "indexed_pmids": [],
            "failed_pmids": []
        }
    
    def _save_progress(self):
        """Save progress to file"""
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    async def search_pubmed_robust(
        self,
        query: str,
        max_results: int,
        retries: int = 5
    ) -> List[str]:
        """
        Search PubMed with retry logic and exponential backoff
        """
        for attempt in range(retries):
            try:
                # Simple query format that PubMed accepts
                handle = Entrez.esearch(
                    db="pubmed",
                    term=query,
                    retmax=max_results,
                    sort="relevance"
                )
                record = Entrez.read(handle)
                handle.close()
                
                pmids = record["IdList"]
                return pmids
            
            except Exception as e:
                wait_time = (2 ** attempt) * self.rate_limit_delay
                print(f"  ⚠️  Attempt {attempt+1}/{retries} failed: {e}")
                
                if attempt < retries - 1:
                    print(f"  ⏳ Waiting {wait_time:.1f}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"  ❌ All attempts failed for query: {query}")
                    return []
        
        return []
    
    async def fetch_article_with_pdf(
        self,
        pmid: str,
        db: Any
    ) -> Optional[Dict]:
        """
        Fetch article details and try to download PDF
        """
        try:
            # Fetch article metadata
            handle = Entrez.efetch(
                db="pubmed",
                id=pmid,
                rettype="xml",
                retmode="xml"
            )
            records = Entrez.read(handle)
            handle.close()
            
            if not records.get("PubmedArticle"):
                return None
            
            record = records["PubmedArticle"][0]
            article_data = self.pubmed_service._parse_article(record)
            
            if not article_data:
                return None
            
            # Try to download PDF
            pdf_path = None
            pdf_text = None
            
            # Method 1: Try PMC (PubMed Central)
            try:
                pmc_id = self._get_pmc_id(pmid)
                if pmc_id:
                    pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"
                    pdf_path = self.pdf_dir / f"{pmid}.pdf"
                    
                    if self._download_pdf(pdf_url, pdf_path):
                        pdf_text = self._extract_text_from_pdf(pdf_path)
                        self.stats["pdfs_downloaded"] += 1
            except:
                pass
            
            # Method 2: Try DOI-based download
            if not pdf_text and article_data.doi:
                try:
                    pdf_url = f"https://doi.org/{article_data.doi}"
                    pdf_path = self.pdf_dir / f"{pmid}.pdf"
                    
                    if self._download_pdf(pdf_url, pdf_path):
                        pdf_text = self._extract_text_from_pdf(pdf_path)
                        self.stats["pdfs_downloaded"] += 1
                except:
                    pass
            
            return {
                "article": article_data,
                "pdf_text": pdf_text,
                "pdf_path": str(pdf_path) if pdf_path else None
            }
        
        except Exception as e:
            print(f"  ❌ Error fetching PMID {pmid}: {e}")
            return None
    
    def _get_pmc_id(self, pmid: str) -> Optional[str]:
        """Get PMC ID from PMID"""
        try:
            handle = Entrez.elink(
                dbfrom="pubmed",
                db="pmc",
                id=pmid
            )
            record = Entrez.read(handle)
            handle.close()
            
            if record[0]["LinkSetDb"]:
                pmc_id = record[0]["LinkSetDb"][0]["Link"][0]["Id"]
                return f"PMC{pmc_id}"
        except:
            pass
        
        return None
    
    def _download_pdf(self, url: str, save_path: Path) -> bool:
        """Download PDF from URL"""
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 200 and response.headers.get('content-type', '').startswith('application/pdf'):
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return True
        except:
            pass
        
        return False
    
    def _extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """Extract text from PDF"""
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except:
            return None
    
    async def process_query(
        self,
        query: str,
        query_idx: int,
        total_queries: int,
        db: Any
    ):
        """Process a single search query"""
        
        # Check if already completed
        if query in self.progress["completed_queries"]:
            print(f"[{query_idx}/{total_queries}] ✓ Already completed: {query}")
            return
        
        print(f"\n[{query_idx}/{total_queries}] 🔍 {query}")
        print("=" * 70)
        
        # Search PubMed
        print(f"  📡 Searching PubMed...")
        pmids = await self.search_pubmed_robust(query, self.max_articles_per_query)
        
        if not pmids:
            print(f"  ⚠️  No results found")
            self.progress["completed_queries"].append(query)
            self._save_progress()
            return
        
        print(f"  ✓ Found {len(pmids)} articles")
        
        # Filter already downloaded
        new_pmids = [p for p in pmids if p not in self.progress["downloaded_pmids"]]
        print(f"  ℹ️  {len(new_pmids)} new articles to download")
        
        # Download articles with progress bar
        documents = []
        with tqdm(total=len(new_pmids), desc="  Downloading", unit="article") as pbar:
            for pmid in new_pmids:
                # Rate limiting
                await asyncio.sleep(self.rate_limit_delay)
                
                result = await self.fetch_article_with_pdf(pmid, db)
                
                if result:
                    article = result["article"]
                    pdf_text = result["pdf_text"]
                    
                    # Create document from abstract
                    content = f"Title: {article.title}\n\n"
                    content += f"Authors: {article.authors}\n"
                    content += f"Journal: {article.journal}\n"
                    if article.publication_date:
                        content += f"Published: {article.publication_date}\n"
                    content += f"PMID: {article.pmid}\n"
                    if article.doi:
                        content += f"DOI: {article.doi}\n"
                    content += f"\nAbstract:\n{article.abstract}\n"
                    
                    # Add full text if PDF was downloaded
                    if pdf_text:
                        content += f"\n\nFull Text:\n{pdf_text[:50000]}"  # Limit to 50k chars
                    
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": "pubmed",
                            "pmid": article.pmid,
                            "title": article.title,
                            "authors": article.authors,
                            "journal": article.journal,
                            "publication_date": str(article.publication_date) if article.publication_date else None,
                            "doi": article.doi,
                            "url": article.pdf_url,
                            "query": query,
                            "has_full_text": pdf_text is not None
                        }
                    )
                    documents.append(doc)
                    
                    self.progress["downloaded_pmids"].append(pmid)
                    self.stats["articles_downloaded"] += 1
                else:
                    self.progress["failed_pmids"].append(pmid)
                    self.stats["errors"] += 1
                
                pbar.update(1)
                
                # Save progress every 50 articles
                if len(documents) % 50 == 0:
                    self._save_progress()
        
        print(f"  ✓ Downloaded {len(documents)} articles ({self.stats['pdfs_downloaded']} with PDFs)")
        
        # Chunk and index
        if documents:
            print(f"  📝 Chunking documents...")
            all_chunks = []
            for doc in tqdm(documents, desc="  Chunking", unit="doc"):
                chunks = document_processor.text_splitter.create_documents(
                    texts=[doc.page_content],
                    metadatas=[doc.metadata]
                )
                all_chunks.extend(chunks)
            
            print(f"  ✓ Created {len(all_chunks)} chunks")
            
            print(f"  💾 Indexing in ChromaDB...")
            batch_size = 100
            for i in tqdm(range(0, len(all_chunks), batch_size), desc="  Indexing", unit="batch"):
                batch = all_chunks[i:i + batch_size]
                
                try:
                    vector_store_manager.add_documents(
                        collection_name=self.collection_name,
                        documents=batch
                    )
                    
                    # Mark PMIDs as indexed
                    for doc in batch:
                        pmid = doc.metadata.get("pmid")
                        if pmid and pmid not in self.progress["indexed_pmids"]:
                            self.progress["indexed_pmids"].append(pmid)
                    
                    self.stats["chunks_indexed"] += len(batch)
                
                except Exception as e:
                    print(f"    ⚠️  Error indexing batch: {e}")
            
            print(f"  ✅ Indexed {len(all_chunks)} chunks")
        
        # Mark query as completed
        self.progress["completed_queries"].append(query)
        self.stats["total_queries"] += 1
        self._save_progress()
        
        # Print current stats
        print(f"\n  📊 Progress: {len(self.progress['completed_queries'])}/{len(COMPREHENSIVE_SEARCH_TERMS)} queries | " +
              f"{self.stats['articles_downloaded']} articles | " +
              f"{self.stats['pdfs_downloaded']} PDFs | " +
              f"{self.stats['chunks_indexed']} chunks")
    
    async def populate_all(self):
        """Main function to populate ALL articles"""
        
        print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║         PRODUCTION RAG POPULATION SYSTEM                          ║
║         Comprehensive Vision Research Knowledge Base              ║
║                                                                   ║
║  Features:                                                        ║
║  ✓ Downloads ALL available PubMed articles                        ║
║  ✓ Extracts PDFs when available                                   ║
║  ✓ Handles rate limiting automatically                            ║
║  ✓ Resumes from interruptions                                     ║
║  ✓ Saves progress continuously                                    ║
║                                                                   ║
║  Expected: 10,000+ articles with 2,000+ PDFs                      ║
║  Time: 3-6 hours                                                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
        """)
        
        print(f"📍 Progress file: {self.progress_file}")
        print(f"📁 PDF directory: {self.pdf_dir}")
        print(f"🗄️  Collection: {self.collection_name}")
        print(f"⚡ Rate limit: {self.rate_limit_delay}s between requests")
        print(f"📚 Total queries: {len(COMPREHENSIVE_SEARCH_TERMS)}")
        print(f"✓ Already completed: {len(self.progress['completed_queries'])} queries")
        print(f"✓ Already downloaded: {len(self.progress['downloaded_pmids'])} articles")
        print(f"✓ Already indexed: {len(self.progress['indexed_pmids'])} PMIDs")
        print()
        
        async for db in get_db():
            try:
                total_queries = len(COMPREHENSIVE_SEARCH_TERMS)
                
                for idx, query in enumerate(COMPREHENSIVE_SEARCH_TERMS, 1):
                    try:
                        await self.process_query(query, idx, total_queries, db)
                    except Exception as e:
                        print(f"  ❌ Error processing query '{query}': {e}")
                        continue
                
                # Final summary
                print(f"\n{'='*70}")
                print(f"🎉 POPULATION COMPLETE!")
                print(f"{'='*70}")
                print(f"Total queries processed: {self.stats['total_queries']}")
                print(f"Articles downloaded: {self.stats['articles_downloaded']}")
                print(f"PDFs downloaded: {self.stats['pdfs_downloaded']}")
                print(f"Chunks indexed: {self.stats['chunks_indexed']}")
                print(f"Errors: {self.stats['errors']}")
                print(f"Duration: {datetime.now().isoformat()}")
                print(f"\n✅ Your RAG system is now populated with REAL research data!")
                print(f"{'='*70}\n")
                
            except Exception as e:
                print(f"\n❌ Fatal error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                break


if __name__ == "__main__":
    populator = ProductionRAGPopulator(
        progress_file="/data/rag_progress.json",
        pdf_dir="/data/pubmed_pdfs",
        max_articles_per_query=500,  # 500 per query
        rate_limit_delay=0.34,  # ~3 requests/sec
        collection_name="pubmed_vision_research"
    )
    
    asyncio.run(populator.populate_all())

