#!/usr/bin/env python3
"""
CONCURRENT RAG POPULATION SYSTEM WITH FULL-TEXT PDF EXTRACTION
================================================================

This script downloads ALL available vision research articles from PubMed:
- Uses 5 PubMed API keys concurrently (50 requests/second total)
- Extracts full-text PDFs from PubMed Central (PMC) when available
- Downloads abstracts for all articles
- Parallel query processing with asyncio
- Handles rate limiting with exponential backoff
- Saves progress to resume interrupted runs
- Indexes full text + abstracts in ChromaDB

Expected: 10,000+ articles with 2,000+ full-text PDFs in ~1 hour

Author: Full-Stack AI Engineer
"""

import sys
import os
import time
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from tqdm import tqdm
import threading
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import get_db
from app.rag.vector_store import vector_store_manager
from app.rag.document_processor import document_processor
from langchain.schema import Document
from langchain_community.vectorstores.utils import filter_complex_metadata
from Bio import Entrez
import PyPDF2
import io


# Comprehensive vision research search terms
COMPREHENSIVE_SEARCH_TERMS = [
    # Retinal diseases
    "retinal degeneration", "age related macular degeneration", "diabetic retinopathy",
    "retinitis pigmentosa", "macular edema", "retinal dystrophy",
    "choroidal neovascularization", "geographic atrophy", "central serous chorioretinopathy",
    "retinal detachment", "epiretinal membrane", "macular hole",
    
    # Inherited retinal diseases
    "leber congenital amaurosis", "stargardt disease", "best disease",
    "choroideremia", "x-linked retinoschisis", "cone-rod dystrophy",
    "retinopathy of prematurity", "coats disease",

    # Glaucoma
    "glaucoma", "primary open angle glaucoma", "angle closure glaucoma",
    "normal tension glaucoma", "congenital glaucoma", "neovascular glaucoma",
    "retinal ganglion cells", "optic nerve head",
    
    # Cornea
    "keratoconus", "corneal dystrophy", "fuchs endothelial corneal dystrophy",
    "corneal transplant", "bacterial keratitis", "fungal keratitis",
    "dry eye", "keratoconjunctivitis sicca", "meibomian gland dysfunction",
    
    # Cataract
    "cataract", "phacoemulsification", "intraocular lens",
    "posterior capsule opacification",
    
    # Neuro-ophthalmology  
    "optic neuritis", "ischemic optic neuropathy", "papilledema",
    "leber hereditary optic neuropathy", "idiopathic intracranial hypertension",
    
    # Imaging
    "optical coherence tomography", "oct angiography", "fundus autofluorescence",
    "fluorescein angiography", "adaptive optics",
    
    # Uveitis
    "uveitis", "retinal inflammation", "anterior uveitis", "posterior uveitis",
    "behcet uveitis", "sarcoid uveitis",

    # Vascular
    "retinal vascular disease", "retinal artery occlusion", "retinal vein occlusion",
    
    # Oncology
    "uveal melanoma", "choroidal melanoma", "retinoblastoma",
    "ocular lymphoma", "choroidal nevus",
    
    # Therapy
    "anti-vegf therapy", "ranibizumab", "aflibercept", "bevacizumab", "faricimab",
    "photodynamic therapy", "pars plana vitrectomy",
    "complement inhibition amd", "retinal prosthesis",
    
    # Public health
    "low vision rehabilitation", "vision screening", "blindness epidemiology",
    "visual impairment prevalence", "amblyopia", "strabismus",
]


class RateLimiter:
    """Rate limiter for API requests - 10 req/sec per API key"""
    
    def __init__(self, requests_per_second: int = 10):
        self.delay = 1.0 / requests_per_second
        self.last_request = 0
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Wait if needed to respect rate limit"""
        async with self.lock:
            now = time.time()
            time_since_last = now - self.last_request
            if time_since_last < self.delay:
                await asyncio.sleep(self.delay - time_since_last)
            self.last_request = time.time()


class ConcurrentRAGPopulator:
    """Concurrent RAG population with full-text PDF extraction"""
    
    def __init__(
        self,
        api_keys: List[str],
        emails: List[str],
        progress_file: str = "/data/rag_progress.json",
        pdf_dir: str = "/data/pubmed_pdfs",
        max_articles_per_query: int = 500,
        collection_name: str = "pubmed_vision_research",
        max_concurrent_queries: int = 5
    ):
        self.api_keys = api_keys
        self.emails = emails
        self.num_workers = len(api_keys)
        self.progress_file = progress_file
        self.pdf_dir = Path(pdf_dir)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.max_articles_per_query = max_articles_per_query
        self.collection_name = collection_name
        self.max_concurrent_queries = max_concurrent_queries
        
        # Rate limiters (10 req/sec each)
        self.rate_limiters = [RateLimiter(10) for _ in api_keys]
        
        # Configure Entrez with first key/email
        Entrez.email = emails[0] if emails else settings.PUBMED_EMAIL
        Entrez.api_key = api_keys[0] if api_keys else None
        
        self.progress = self._load_progress()
        self.progress_lock = threading.Lock()
        
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
        with self.progress_lock:
            os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    async def search_pubmed_robust(
        self,
        query: str,
        max_results: int,
        api_key: str,
        email: str,
        rate_limiter: RateLimiter,
        retries: int = 5
    ) -> List[str]:
        """Search PubMed with retry logic"""
        for attempt in range(retries):
            try:
                await rate_limiter.acquire()
                Entrez.api_key = api_key
                Entrez.email = email
                
                handle = Entrez.esearch(
                    db="pubmed",
                    term=query,
                    retmax=max_results,
                    sort="relevance"
                )
                record = Entrez.read(handle)
                handle.close()
                
                return record.get("IdList", [])
            
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep((2 ** attempt) * 0.5)
                else:
                    print(f"    ⚠️  Failed to search: {e}")
                    return []
        return []
    
    async def fetch_article_metadata(
        self,
        pmid: str,
        api_key: str,
        email: str,
        rate_limiter: RateLimiter
    ) -> Optional[Dict]:
        """
        Fetch article metadata including PMC ID for PDF access
        
        Returns dict with: pmid, pmc_id, title, abstract, authors, journal, doi, pub_date
        """
        try:
            await rate_limiter.acquire()
            Entrez.api_key = api_key
            Entrez.email = email
            
            # Fetch detailed article data
            handle = Entrez.efetch(
                db="pubmed",
                id=pmid,
                rettype="xml",
                retmode="xml"
            )
            records = Entrez.read(handle)
            handle.close()
            
            if not records or "PubmedArticle" not in records:
                return None
            
            record = records["PubmedArticle"][0]
            medline = record["MedlineCitation"]
            article_data = medline["Article"]
            
            # Extract PMC ID from ArticleIdList
            pmc_id = None
            if "PubmedData" in record and "ArticleIdList" in record["PubmedData"]:
                for article_id in record["PubmedData"]["ArticleIdList"]:
                    if article_id.attributes.get("IdType") == "pmc":
                        pmc_id = str(article_id).replace("PMC", "")  # Get number only
                        break
            
            # Extract DOI
            doi = None
            if "ELocationID" in article_data:
                for eloc in article_data["ELocationID"]:
                    if eloc.attributes.get("EIdType") == "doi":
                        doi = str(eloc)
                        break
            
            # Extract title
            title = str(article_data.get("ArticleTitle", ""))
            
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
                if year:
                    pub_date = str(year)
            
            return {
                "pmid": pmid,
                "pmc_id": pmc_id,
                "title": title,
                "abstract": abstract,
                "authors": authors_str,
                "journal": journal,
                "doi": doi,
                "publication_date": pub_date
            }
        
        except Exception as e:
            print(f"Error fetching metadata for PMID {pmid}: {e}")
            return None
    
    async def download_pmc_pdf(
        self,
        pmc_id: str,
        pmid: str
    ) -> Optional[str]:
        """
        Download and extract text from PMC PDF
        
        Args:
            pmc_id: PMC ID (number only, e.g., "5967598")
            pmid: PubMed ID for filename
            
        Returns:
            Extracted text or None
        """
        try:
            # Construct PMC PDF URL
            pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/pdf/"
            pdf_path = self.pdf_dir / f"{pmid}_PMC{pmc_id}.pdf"
            
            # Download PDF with timeout
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(pdf_url) as response:
                    if response.status == 200:
                        pdf_content = await response.read()
                        
                        # Save PDF
                        pdf_path.write_bytes(pdf_content)
                        
                        # Extract text
                        try:
                            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
                            text = ""
                            for page in pdf_reader.pages:
                                page_text = page.extract_text()
                                if page_text:
                                    text += page_text + "\n"
                                        
                                if text.strip():
                                            # Log extraction statistics
                                    page_count = len(pdf_reader.pages)
                                    char_count = len(text)
                                    print(f"  📄 Extracted {page_count} pages, {char_count:,} characters from PMC{pmc_id}")
                            return text
                        except Exception as e:
                            print(f"  ⚠️  PDF extraction error for PMC{pmc_id}: {e}")
                            return None
                    else:
                        return None
        
        except asyncio.TimeoutError:
            print(f"  ⚠️  Timeout downloading PMC{pmc_id}")
            return None
        except Exception as e:
            print(f"  ⚠️  Error downloading PMC{pmc_id}: {e}")
            return None
    
    async def process_query_concurrent(
        self,
        query: str,
        query_idx: int,
        total_queries: int,
        api_key_idx: int,
        db: Any
    ):
        """Process a single search query with assigned API key"""
        
        api_key = self.api_keys[api_key_idx]
        email = self.emails[api_key_idx]
        rate_limiter = self.rate_limiters[api_key_idx]
        
        # Check if already completed
        if query in self.progress["completed_queries"]:
            print(f"[Worker {api_key_idx+1}] [Q{query_idx}/{total_queries}] ✓ Already completed: {query}")
            return
        
        print(f"\n[Worker {api_key_idx+1}] [Q{query_idx}/{total_queries}] 🔍 {query}")
        print("=" * 70)
        
        # Search PubMed
        print(f"  📡 Searching PubMed...")
        pmids = await self.search_pubmed_robust(query, self.max_articles_per_query, api_key, email, rate_limiter)
        
        if not pmids:
            print(f"  ⚠️  No results found")
            with self.progress_lock:
                self.progress["completed_queries"].append(query)
            self._save_progress()
            return
        
        print(f"  ✓ Found {len(pmids)} articles")
        
        # Filter already downloaded
        with self.progress_lock:
            new_pmids = [p for p in pmids if p not in self.progress["downloaded_pmids"]]
        
        print(f"  ℹ️  {len(new_pmids)} new articles to download")
        
        # Download articles with metadata and PDFs
        documents = []
        
        print(f"  ⬇️  Downloading with Worker {api_key_idx+1}...")
        
        for i, pmid in enumerate(new_pmids):
            try:
                # Fetch metadata
                metadata = await self.fetch_article_metadata(pmid, api_key, email, rate_limiter)
                
                if not metadata:
                    with self.progress_lock:
                        self.progress["failed_pmids"].append(pmid)
                    self.stats["errors"] += 1
                    continue
                
                # Try to download PDF if PMC ID exists
                pdf_text = None
                if metadata.get("pmc_id"):
                    pdf_text = await self.download_pmc_pdf(metadata["pmc_id"], pmid)
                    if pdf_text:
                        self.stats["pdfs_downloaded"] += 1
                
                # Create document content
                content = f"Title: {metadata['title']}\n\n"
                content += f"Authors: {metadata['authors']}\n"
                content += f"Journal: {metadata['journal']}\n"
                if metadata['publication_date']:
                    content += f"Published: {metadata['publication_date']}\n"
                content += f"PMID: {pmid}\n"
                if metadata['doi']:
                    content += f"DOI: {metadata['doi']}\n"
                if metadata.get('pmc_id'):
                    content += f"PMC ID: PMC{metadata['pmc_id']}\n"
                content += f"\nAbstract:\n{metadata['abstract']}\n"
                
                # Add full text if PDF was extracted
                if pdf_text:
                    content += f"\n\n{'='*70}\nFULL TEXT (EXTRACTED FROM PDF)\n{'='*70}\n\n{pdf_text}"
                
                # Build metadata without None values
                doc_metadata = {
                            "source": "pubmed",
                    "pmid": pmid,
                    "title": metadata['title'] or "",
                    "authors": metadata['authors'] or "",
                    "journal": metadata['journal'] or "",
                            "query": query,
                    "has_full_text": bool(pdf_text)
                }
                
                if metadata.get('pmc_id'):
                    doc_metadata["pmc_id"] = f"PMC{metadata['pmc_id']}"
                if metadata['publication_date']:
                    doc_metadata["publication_date"] = metadata['publication_date']
                if metadata['doi']:
                    doc_metadata["doi"] = metadata['doi']
                
                doc = Document(page_content=content, metadata=doc_metadata)
                documents.append(doc)
                    
                with self.progress_lock:
                    self.progress["downloaded_pmids"].append(pmid)
                    self.stats["articles_downloaded"] += 1
                
                # Save progress periodically
                if (i + 1) % 50 == 0:
                    self._save_progress()
                    print(f"  Progress: {i+1}/{len(new_pmids)} articles processed")
            
            except Exception as e:
                print(f"  ⚠️  Error processing PMID {pmid}: {e}")
                with self.progress_lock:
                    self.progress["failed_pmids"].append(pmid)
                self.stats["errors"] += 1
        
        print(f"  ✓ Downloaded {len(documents)} articles ({self.stats['pdfs_downloaded']} with PDFs)")
        
        # Chunk and index
        if documents:
            print(f"  📝 Chunking documents...")
            all_chunks = []
            for doc in documents:
                chunks = document_processor.text_splitter.create_documents(
                    texts=[doc.page_content],
                    metadatas=[doc.metadata]
                )
                all_chunks.extend(chunks)
            
            print(f"  ✓ Created {len(all_chunks)} chunks")
            
            print(f"  💾 Indexing in ChromaDB...")
            batch_size = 100
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]
                filtered_batch = filter_complex_metadata(batch)
                
                try:
                    vector_store_manager.add_documents(
                        collection_name=self.collection_name,
                        documents=filtered_batch
                    )
                    
                    for doc in batch:
                        pmid = doc.metadata.get("pmid")
                        if pmid:
                            with self.progress_lock:
                                if pmid not in self.progress["indexed_pmids"]:
                                    self.progress["indexed_pmids"].append(pmid)
                    
                    self.stats["chunks_indexed"] += len(batch)
                except Exception as e:
                    print(f"    ⚠️  Error indexing batch: {e}")
            
            print(f"  ✅ Indexed {len(all_chunks)} chunks")
        
        # Mark query as completed
        with self.progress_lock:
            self.progress["completed_queries"].append(query)
            self.stats["total_queries"] += 1
            self._save_progress()
        
        # Print stats
        with self.progress_lock:
            completed = len(self.progress['completed_queries'])
            downloaded = len(self.progress['downloaded_pmids'])
            indexed = len(self.progress['indexed_pmids'])
        
        print(f"\n  📊 Progress: {completed}/{len(COMPREHENSIVE_SEARCH_TERMS)} queries | " +
              f"{downloaded} articles | {self.stats['pdfs_downloaded']} PDFs | {indexed} indexed")
    
    async def populate_all_concurrent(self):
        """Main function to populate ALL articles with concurrent workers"""
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║    CONCURRENT RAG POPULATION WITH FULL-TEXT PDF EXTRACTION        ║
║         Comprehensive Vision Research Knowledge Base              ║
║                                                                   ║
║  Features:                                                        ║
║  ✓ {len(self.api_keys)} PubMed API keys working in parallel                       ║
║  ✓ {len(self.api_keys) * 10} requests/second total capacity                          ║
║  ✓ Full-text PDF extraction from PMC (open access)                ║
║  ✓ Downloads ALL available PubMed articles                        ║
║  ✓ Handles rate limiting automatically                            ║
║  ✓ Resumes from interruptions                                     ║
║  ✓ Saves progress continuously                                    ║
║                                                                   ║
║  Expected: 10,000+ articles with 2,000+ full-text PDFs            ║
║  Time: ~1 hour (5x faster with {len(self.api_keys)} workers!)                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
        """)
        
        print(f"📍 Progress file: {self.progress_file}")
        print(f"📁 PDF directory: {self.pdf_dir}")
        print(f"🗄️  Collection: {self.collection_name}")
        print(f"⚡ Rate limit: 10 req/sec per worker ({len(self.api_keys) * 10} req/sec total)")
        print(f"👷 Workers: {len(self.api_keys)}")
        print(f"📚 Total queries: {len(COMPREHENSIVE_SEARCH_TERMS)}")
        
        with self.progress_lock:
            completed = len(self.progress["completed_queries"])
            downloaded = len(self.progress["downloaded_pmids"])
            indexed = len(self.progress["indexed_pmids"])
        
        print(f"✓ Already completed: {completed} queries")
        print(f"✓ Already downloaded: {downloaded} articles")
        print(f"✓ Already indexed: {indexed} PMIDs")
        print()
        
        # Get remaining queries
        remaining_queries = [
            (idx + 1, q) for idx, q in enumerate(COMPREHENSIVE_SEARCH_TERMS)
            if q not in self.progress["completed_queries"]
        ]
        
        if not remaining_queries:
            print("✅ All queries already completed!")
            return
        
        print(f"🚀 Processing {len(remaining_queries)} remaining queries with {len(self.api_keys)} workers...\n")
        
        # Create tasks with round-robin distribution
        tasks = []
        async with get_db() as db:
            for i, (query_idx, query) in enumerate(remaining_queries):
                api_key_idx = i % len(self.api_keys)
                task = self.process_query_concurrent(query, query_idx, len(COMPREHENSIVE_SEARCH_TERMS), api_key_idx, db)
                tasks.append(task)
            
            # Run with limited concurrency
            semaphore = asyncio.Semaphore(self.max_concurrent_queries)
            
            async def bounded_task(task):
                async with semaphore:
                    return await task
            
            bounded_tasks = [bounded_task(task) for task in tasks]
            await asyncio.gather(*bounded_tasks, return_exceptions=True)
        
        print("\n" + "="*70)
        print("🎉 POPULATION COMPLETE!")
        print("="*70)
        print(f"✅ Total queries processed: {self.stats['total_queries']}")
        print(f"✅ Total articles downloaded: {self.stats['articles_downloaded']}")
        print(f"✅ Total PDFs extracted: {self.stats['pdfs_downloaded']}")
        print(f"✅ Total chunks indexed: {self.stats['chunks_indexed']}")
        print(f"⚠️  Total errors: {self.stats['errors']}")
        
        duration = (datetime.now() - datetime.fromisoformat(self.stats["start_time"])).total_seconds()
        print(f"⏱️  Time taken: {duration/3600:.2f} hours")
        print()


async def main():
    """Main entry point"""
    
    # Load API keys and emails from environment
    API_KEYS = [
        os.getenv("PUBMED_API_KEY_1", ""),
        os.getenv("PUBMED_API_KEY_2", ""),
        os.getenv("PUBMED_API_KEY_3", ""),
        os.getenv("PUBMED_API_KEY_4", ""),
        os.getenv("PUBMED_API_KEY_5", "")
    ]
    
    EMAILS = [
        os.getenv("PUBMED_EMAIL_1", ""),
        os.getenv("PUBMED_EMAIL_2", ""),
        os.getenv("PUBMED_EMAIL_3", ""),
        os.getenv("PUBMED_EMAIL_4", ""),
        os.getenv("PUBMED_EMAIL_5", "")
    ]
    
    # Filter out empty keys and corresponding emails
    key_email_pairs = [(k, e) for k, e in zip(API_KEYS, EMAILS) if k and e]
    
    if not key_email_pairs:
        print("⚠️  No API keys/emails found! Set PUBMED_API_KEY_1-5 and PUBMED_EMAIL_1-5")
        if settings.PUBMED_API_KEY and settings.PUBMED_EMAIL:
            API_KEYS = [settings.PUBMED_API_KEY]
            EMAILS = [settings.PUBMED_EMAIL]
        else:
            print("❌ No API keys/emails available. Exiting.")
            return
    else:
        API_KEYS = [pair[0] for pair in key_email_pairs]
        EMAILS = [pair[1] for pair in key_email_pairs]
    
    print(f"✓ Loaded {len(API_KEYS)} API key(s) with corresponding emails")
    
    populator = ConcurrentRAGPopulator(
        api_keys=API_KEYS,
        emails=EMAILS,
        max_concurrent_queries=len(API_KEYS)
    )
    
    await populator.populate_all_concurrent()


if __name__ == "__main__":
    asyncio.run(main())
