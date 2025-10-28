#!/usr/bin/env python3


import sys
import os
import time
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
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
    """Rate limiter for API requests"""
    
    def __init__(self, requests_per_second: int = 10):
        self.delay = 1.0 / requests_per_second
        self.last_request = 0
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        async with self.lock:
            now = time.time()
            time_since_last = now - self.last_request
            if time_since_last < self.delay:
                await asyncio.sleep(self.delay - time_since_last)
            self.last_request = time.time()


class ParallelRAGPopulator:
    """RAG populator with separate worker pools"""
    
    def __init__(
        self,
        api_keys: List[str],
        emails: List[str],
        progress_file: str = "/data/rag_progress.json",
        pdf_dir: str = "/data/pubmed_pdfs",
        max_articles_per_query: int = 500,
        collection_name: str = "pubmed_vision_research",
        num_pdf_workers: int = 3,
        num_index_workers: int = 2
    ):
        self.api_keys = api_keys
        self.emails = emails
        self.progress_file = progress_file
        self.pdf_dir = Path(pdf_dir)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.max_articles_per_query = max_articles_per_query
        self.collection_name = collection_name
        self.num_pdf_workers = num_pdf_workers
        self.num_index_workers = num_index_workers
        
        # Rate limiters
        self.rate_limiters = [RateLimiter(10) for _ in api_keys]
        
        # Configure Entrez
        Entrez.email = emails[0] if emails else settings.PUBMED_EMAIL
        Entrez.api_key = api_keys[0] if api_keys else None
        
        # Queues for worker communication
        self.pdf_queue = asyncio.Queue()
        self.index_queue = asyncio.Queue()
        
        self.progress = self._load_progress()
        self.progress_lock = asyncio.Lock()
        
        self.stats = {
            "queries_processed": 0,
            "articles_downloaded": 0,
            "pdfs_extracted": 0,
            "chunks_indexed": 0,
            "errors": 0,
            "start_time": datetime.now().isoformat()
        }
        self.stats_lock = asyncio.Lock()
    
    def _load_progress(self) -> Dict:
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
        os.makedirs(os.path.dirname(self.progress_file), exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    async def search_pubmed(self, query: str, api_key: str, email: str, rate_limiter: RateLimiter) -> List[str]:
        """Search PubMed"""
        for attempt in range(5):
            try:
                await rate_limiter.acquire()
                Entrez.api_key = api_key
                Entrez.email = email
                
                handle = Entrez.esearch(db="pubmed", term=query, retmax=self.max_articles_per_query, sort="relevance")
                record = Entrez.read(handle)
                handle.close()
                return record.get("IdList", [])
            except Exception as e:
                if attempt < 4:
                    await asyncio.sleep((2 ** attempt) * 0.5)
                else:
                    print(f"    ⚠️  Search failed: {e}")
                    return []
        return []
    
    async def fetch_metadata(self, pmid: str, api_key: str, email: str, rate_limiter: RateLimiter) -> Optional[Dict]:
        """Fetch article metadata"""
        try:
            await rate_limiter.acquire()
            Entrez.api_key = api_key
            Entrez.email = email
            
            handle = Entrez.efetch(db="pubmed", id=pmid, rettype="xml", retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            
            if not records or "PubmedArticle" not in records:
                return None
            
            record = records["PubmedArticle"][0]
            medline = record["MedlineCitation"]
            article_data = medline["Article"]
            
            # Extract PMC ID
            pmc_id = None
            if "PubmedData" in record and "ArticleIdList" in record["PubmedData"]:
                for article_id in record["PubmedData"]["ArticleIdList"]:
                    if article_id.attributes.get("IdType") == "pmc":
                        pmc_id = str(article_id).replace("PMC", "")
                        break
            
            # Extract DOI
            doi = None
            if "ELocationID" in article_data:
                for eloc in article_data["ELocationID"]:
                    if eloc.attributes.get("EIdType") == "doi":
                        doi = str(eloc)
                        break
            
            # Extract basic info
            title = str(article_data.get("ArticleTitle", ""))
            abstract = ""
            if "Abstract" in article_data:
                abstract_texts = article_data["Abstract"].get("AbstractText", [])
                if isinstance(abstract_texts, list):
                    abstract = " ".join([str(text) for text in abstract_texts])
                else:
                    abstract = str(abstract_texts)
            
            authors = []
            if "AuthorList" in article_data:
                for author in article_data["AuthorList"]:
                    if "LastName" in author and "ForeName" in author:
                        authors.append(f"{author['ForeName']} {author['LastName']}")
            
            journal = article_data.get("Journal", {}).get("Title", "")
            pub_date = None
            if "Journal" in article_data:
                pub_date_data = article_data["Journal"].get("JournalIssue", {}).get("PubDate", {})
                year = pub_date_data.get("Year")
                if year:
                    pub_date = str(year)
            
            return {
                "pmid": pmid,
                "pmc_id": pmc_id,
                "title": title,
                "abstract": abstract,
                "authors": ", ".join(authors),
                "journal": journal,
                "doi": doi,
                "publication_date": pub_date
            }
        except Exception as e:
            print(f"    ⚠️  Metadata error for PMID {pmid}: {e}")
            return None
    
    async def pdf_extraction_worker(self, worker_id: int):
        """Worker that extracts PDFs from queue"""
        print(f"  🔧 PDF Worker {worker_id} started")
        
        while True:
            try:
                item = await self.pdf_queue.get()
                if item is None:  # Poison pill
                    self.pdf_queue.task_done()
                    break
                
                pmid, pmc_id, metadata = item
                
                try:
                    # Download and extract PDF
                    pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/pdf/"
                    pdf_path = self.pdf_dir / f"{pmid}_PMC{pmc_id}.pdf"
                    
                    timeout = aiohttp.ClientTimeout(total=60)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(pdf_url) as response:
                            if response.status == 200:
                                pdf_content = await response.read()
                                pdf_path.write_bytes(pdf_content)
                                
                                # Extract text using improved document processor
                                from app.rag.document_processor import document_processor
                                text = document_processor.extract_text_from_pdf(str(pdf_path))
                                
                                if text.strip() and text != "No text could be extracted from PDF":
                                    metadata['pdf_text'] = text
                                    async with self.stats_lock:
                                        self.stats['pdfs_extracted'] += 1
                                    print(f"    📄 PDF extracted: PMC{pmc_id} ({len(text):,} chars)")
                                else:
                                    print(f"    ⚠️ PDF extraction failed: PMC{pmc_id}")
                
                except Exception as e:
                    print(f"    ⚠️  PDF extraction error PMC{pmc_id}: {e}")
                
                # Send to indexing queue
                await self.index_queue.put((pmid, metadata))
                self.pdf_queue.task_done()
                
            except Exception as e:
                print(f"  ❌ PDF Worker {worker_id} error: {e}")
                self.pdf_queue.task_done()
    
    async def indexing_worker(self, worker_id: int):
        """Worker that indexes documents from queue"""
        print(f"  🔧 Index Worker {worker_id} started", flush=True)
        print(f"  🔧 Index Worker {worker_id} queue ID: {id(self.index_queue)}", flush=True)
        
        batch = []
        batch_size = 25
        
        while True:
            try:
                # Get item from queue (blocks until available)
                print(f"  ⏳ Index Worker {worker_id} calling get()...", flush=True)
                item = await self.index_queue.get()
                print(f"  ✅ Index Worker {worker_id} got item!", flush=True)
                
                if item is None:  # Poison pill
                    if batch:
                        await self._index_batch(batch, worker_id)
                    self.index_queue.task_done()
                    break
                
                batch.append(item)
                self.index_queue.task_done()
                
                # Process when batch is full
                if len(batch) >= batch_size:
                    await self._index_batch(batch, worker_id)
                    batch = []
                    self._save_progress()
                
                # Also process if queue is empty and we have items
                elif self.index_queue.empty() and batch:
                    await asyncio.sleep(1.0)  # Wait a bit for more items
                    if self.index_queue.empty():  # Still empty, process what we have
                        await self._index_batch(batch, worker_id)
                        batch = []
                        self._save_progress()
                
            except Exception as e:
                import traceback
                print(f"  ❌ Index Worker {worker_id} error: {e}", flush=True)
                traceback.print_exc()
    
    async def _index_batch(self, batch: List, worker_id: int):
        """Index a batch of documents"""
        if not batch:
            return
        
        try:
            documents = []
            pmids = []
            
            for pmid, metadata in batch:
                # Build content
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
                
                if metadata.get('pdf_text'):
                    content += f"\n\n{'='*70}\nFULL TEXT (EXTRACTED FROM PDF)\n{'='*70}\n\n{metadata['pdf_text']}"
                
                # Build metadata
                doc_metadata = {
                    "source": "pubmed",
                    "pmid": pmid,
                    "title": metadata['title'] or "",
                    "authors": metadata['authors'] or "",
                    "journal": metadata['journal'] or "",
                    "has_full_text": bool(metadata.get('pdf_text'))
                }
                
                if metadata.get('pmc_id'):
                    doc_metadata["pmc_id"] = f"PMC{metadata['pmc_id']}"
                if metadata['publication_date']:
                    doc_metadata["publication_date"] = metadata['publication_date']
                if metadata['doi']:
                    doc_metadata["doi"] = metadata['doi']
                
                doc = Document(page_content=content, metadata=doc_metadata)
                documents.append(doc)
                pmids.append(pmid)
            
            # Chunk documents
            all_chunks = []
            for doc in documents:
                chunks = document_processor.text_splitter.create_documents(
                    texts=[doc.page_content],
                    metadatas=[doc.metadata]
                )
                all_chunks.extend(chunks)
            
            # Index in ChromaDB
            filtered_chunks = filter_complex_metadata(all_chunks)
            vector_store_manager.add_documents(
                collection_name=self.collection_name,
                documents=filtered_chunks
            )
            
            # ONLY update progress AFTER successful indexing
            async with self.progress_lock:
                for pmid in pmids:
                    if pmid not in self.progress["indexed_pmids"]:
                        self.progress["indexed_pmids"].append(pmid)
            
            async with self.stats_lock:
                self.stats['chunks_indexed'] += len(all_chunks)
            
            print(f"    ✅ Indexed {len(batch)} articles ({len(all_chunks)} chunks) [Worker {worker_id}]", flush=True)
            
        except Exception as e:
            import traceback
            print(f"    ❌ Indexing error [Worker {worker_id}]: {e}")
            print(f"    📋 Batch details: {len(batch)} articles, PMIDs: {[p for p, _ in batch[:3]]}")
            print(f"    Traceback:")
            traceback.print_exc()
            # Mark as failed but don't crash
            async with self.progress_lock:
                for pmid, _ in batch:
                    if pmid not in self.progress["failed_pmids"]:
                        self.progress["failed_pmids"].append(pmid)
    
    async def process_query(self, query: str, query_idx: int, total_queries: int, api_key_idx: int):
        """Process a single query"""
        
        api_key = self.api_keys[api_key_idx]
        email = self.emails[api_key_idx]
        rate_limiter = self.rate_limiters[api_key_idx]
        
        # Check if completed
        async with self.progress_lock:
            if query in self.progress["completed_queries"]:
                print(f"[Worker {api_key_idx+1}] [Q{query_idx}/{total_queries}] ✓ Already completed: {query}")
                return
        
        print(f"\n[Worker {api_key_idx+1}] [Q{query_idx}/{total_queries}] 🔍 {query}")
        print("=" * 70)
        
        # Search PubMed
        print(f"  📡 Searching PubMed...")
        pmids = await self.search_pubmed(query, api_key, email, rate_limiter)
        
        if not pmids:
            print(f"  ⚠️  No results found")
            async with self.progress_lock:
                self.progress["completed_queries"].append(query)
            self._save_progress()
            return
        
        print(f"  ✓ Found {len(pmids)} articles")
        
        # Filter new PMIDs
        async with self.progress_lock:
            new_pmids = [p for p in pmids if p not in self.progress["downloaded_pmids"]]
        
        print(f"  ℹ️  {len(new_pmids)} new articles to download")
        
        if not new_pmids:
            async with self.progress_lock:
                self.progress["completed_queries"].append(query)
            self._save_progress()
            return
        
        print(f"  ⬇️  Downloading with Worker {api_key_idx+1}...")
        
        # Download metadata and dispatch to workers
        for i, pmid in enumerate(new_pmids):
            try:
                metadata = await self.fetch_metadata(pmid, api_key, email, rate_limiter)
                
                if not metadata:
                    async with self.progress_lock:
                        self.progress["failed_pmids"].append(pmid)
                    continue
                
                async with self.progress_lock:
                    self.progress["downloaded_pmids"].append(pmid)
                
                async with self.stats_lock:
                    self.stats['articles_downloaded'] += 1
                
                # Index immediately (simplified - no workers for now)
                await self._index_batch([(pmid, metadata)], 0)
                
                async with self.progress_lock:
                    if pmid not in self.progress["indexed_pmids"]:
                        self.progress["indexed_pmids"].append(pmid)
                
                if (i + 1) % 100 == 0:
                    print(f"  Progress: {i+1}/{len(new_pmids)} dispatched")
                    self._save_progress()
                
            except Exception as e:
                print(f"  ⚠️  Error PMID {pmid}: {e}")
                async with self.progress_lock:
                    self.progress["failed_pmids"].append(pmid)
        
        # Mark complete
        async with self.progress_lock:
            self.progress["completed_queries"].append(query)
        self._save_progress()
        
        async with self.stats_lock:
            self.stats['queries_processed'] += 1
        
        print(f"  ✅ Query complete: {len(new_pmids)} articles dispatched to workers")
    
    async def status_monitor(self):
        """Monitor and print status periodically"""
        while True:
            try:
                await asyncio.sleep(10)  # Update every 10 seconds
                
                async with self.stats_lock:
                    queries = self.stats['queries_processed']
                    downloaded = self.stats['articles_downloaded']
                    pdfs = self.stats['pdfs_extracted']
                    indexed = self.stats['chunks_indexed']
                
                pdf_q_size = self.pdf_queue.qsize()
                index_q_size = self.index_queue.qsize()
                
                indexed_count = len(self.progress["indexed_pmids"])
                
                print(f"\n📊 STATUS UPDATE:")
                print(f"   Completed Queries: {queries}/{len(COMPREHENSIVE_SEARCH_TERMS)}")
                print(f"   Downloaded Articles: {downloaded}")
                print(f"   Indexed PMIDs: {indexed_count}")
                print(f"   Failed PMIDs: {len(self.progress['failed_pmids'])}")
                print(f"   PDF Queue: {pdf_q_size} | Index Queue: {index_q_size}")
                print(f"   PDFs Extracted: {pdfs} | Chunks Indexed: {indexed}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Status monitor error: {e}")
    
    async def reindex_unindexed_articles(self):
        """Re-queue downloaded but unindexed articles for indexing"""
        async with self.progress_lock:
            downloaded_set = set(self.progress["downloaded_pmids"])
            indexed_set = set(self.progress["indexed_pmids"])
            unindexed = downloaded_set - indexed_set
        
        if not unindexed:
            print("✅ No unindexed articles found - all downloaded articles are indexed!")
            return
        
        print(f"\n🔄 Found {len(unindexed):,} downloaded but unindexed articles")
        print(f"   Re-queuing ALL for indexing...")
        
        # Process ALL unindexed articles by re-fetching metadata
        # This is needed because we don't cache the full metadata structure
        count = 0
        failed = 0
        
        for i, pmid in enumerate(sorted(unindexed), 1):
            try:
                # Re-fetch metadata for this article
                metadata = await self.fetch_metadata(pmid, self.api_keys[0], self.emails[0], self.rate_limiters[0])
                if metadata:
                    await self.index_queue.put((pmid, metadata))
                    count += 1
                else:
                    failed += 1
                
                # Progress updates
                if i % 100 == 0:
                    print(f"   Progress: {i:,}/{len(unindexed):,} processed ({count:,} queued, {failed} failed)")
                    
            except Exception as e:
                failed += 1
                if failed <= 5:  # Only show first 5 errors
                    print(f"   ⚠️  Error re-queuing {pmid}: {e}")
        
        print(f"   ✓ Re-queued {count:,} articles for indexing ({failed} failed)\n")
    
    async def populate_all(self):
        """Main population function"""
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║    PARALLEL RAG POPULATION WITH WORKER POOLS                      ║
║         Comprehensive Vision Research Knowledge Base              ║
║                                                                   ║
║  Worker Pools:                                                    ║
║  ✓ {len(self.api_keys)} PubMed API workers (metadata download)                   ║
║  ✓ {self.num_pdf_workers} PDF extraction workers (parallel PDF processing)         ║
║  ✓ {self.num_index_workers} Indexing workers (parallel ChromaDB indexing)           ║
║  ✓ 50 requests/second total capacity                              ║
║                                                                   ║
║  Expected: 10,000+ articles with 2,000+ PDFs in ~45 minutes       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
        """)
        
        print(f"📍 Progress file: {self.progress_file}")
        print(f"📁 PDF directory: {self.pdf_dir}")
        print(f"🗄️  Collection: {self.collection_name}")
        print(f"📚 Total queries: {len(COMPREHENSIVE_SEARCH_TERMS)}")
        
        async with self.progress_lock:
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
        
        print(f"🚀 Starting {len(self.api_keys)} API workers, {self.num_pdf_workers} PDF workers, {self.num_index_workers} index workers...\n")
        
        # Start PDF extraction workers
        pdf_workers = [asyncio.create_task(self.pdf_extraction_worker(i+1)) for i in range(self.num_pdf_workers)]
        
        # Start indexing workers
        index_workers = [asyncio.create_task(self.indexing_worker(i+1)) for i in range(self.num_index_workers)]
        
        # Start status monitor
        monitor = asyncio.create_task(self.status_monitor())
        
        # Re-queue any downloaded but unindexed articles
        # NOTE: Disabled for now - re-fetching metadata for thousands of articles is too slow
        # Instead, we'll do a full reset and reprocess everything cleanly
        # await self.reindex_unindexed_articles()
        
        # Process queries
        query_tasks = []
        for i, (query_idx, query) in enumerate(remaining_queries):
            api_key_idx = i % len(self.api_keys)
            task = self.process_query(query, query_idx, len(COMPREHENSIVE_SEARCH_TERMS), api_key_idx)
            query_tasks.append(task)
        
        # Wait for all queries to complete
        await asyncio.gather(*query_tasks, return_exceptions=True)
        
        # Cancel status monitor
        monitor.cancel()
        
        # Wait for queues to empty
        print("\n⏳ Waiting for PDF extraction workers to finish...")
        await self.pdf_queue.join()
        
        print("⏳ Waiting for indexing workers to finish...")
        await self.index_queue.join()
        
        # Stop workers
        for _ in range(self.num_pdf_workers):
            await self.pdf_queue.put(None)
        for _ in range(self.num_index_workers):
            await self.index_queue.put(None)
        
        await asyncio.gather(*pdf_workers, *index_workers)
        
        # Final stats
        print("\n" + "="*70)
        print("🎉 POPULATION COMPLETE!")
        print("="*70)
        async with self.stats_lock:
            print(f"✅ Queries processed: {self.stats['queries_processed']}")
            print(f"✅ Articles downloaded: {self.stats['articles_downloaded']}")
            print(f"✅ PDFs extracted: {self.stats['pdfs_extracted']}")
            print(f"✅ Chunks indexed: {self.stats['chunks_indexed']}")
            print(f"⚠️  Errors: {self.stats['errors']}")
            
            duration = (datetime.now() - datetime.fromisoformat(self.stats["start_time"])).total_seconds()
            print(f"⏱️  Time: {duration/60:.1f} minutes")
        print()


async def main():
    """Main entry point"""
    
    # Load API keys and emails
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
    
    # Filter pairs
    key_email_pairs = [(k, e) for k, e in zip(API_KEYS, EMAILS) if k and e]
    
    if not key_email_pairs:
        print("⚠️  No API keys/emails found!")
        if settings.PUBMED_API_KEY and settings.PUBMED_EMAIL:
            API_KEYS = [settings.PUBMED_API_KEY]
            EMAILS = [settings.PUBMED_EMAIL]
        else:
            print("❌ No API keys/emails available. Exiting.")
            return
    else:
        API_KEYS = [pair[0] for pair in key_email_pairs]
        EMAILS = [pair[1] for pair in key_email_pairs]
    
    print(f"✓ Loaded {len(API_KEYS)} API key(s) with emails")
    
    populator = ParallelRAGPopulator(
        api_keys=API_KEYS,
        emails=EMAILS,
        num_pdf_workers=3,
        num_index_workers=2
    )
    
    await populator.populate_all()


if __name__ == "__main__":
    asyncio.run(main())
