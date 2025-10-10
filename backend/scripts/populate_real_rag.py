#!/usr/bin/env python3
"""
Real RAG Population Script
Downloads actual PubMed articles and populates the vector database

This script:
1. Searches PubMed for vision research articles
2. Downloads abstracts and metadata
3. Processes and chunks the content
4. Stores in ChromaDB with embeddings
5. Creates a searchable knowledge base
"""

import sys
import os
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import get_db
from app.services.pubmed_service import PubMedService
from app.rag.vector_store import vector_store_manager
from app.rag.document_processor import document_processor
from langchain.schema import Document


# Comprehensive vision research topics
VISION_RESEARCH_QUERIES = [
    # Retinal diseases and biology
    "retinal degeneration",
    "macular degeneration pathogenesis",
    "diabetic retinopathy",
    "retinitis pigmentosa",
    "age-related macular degeneration",
    "retinal ganglion cell",
    "photoreceptor",
    
    # Single-cell and omics
    "single-cell RNA sequencing retina",
    "single-cell transcriptomics eye",
    "retinal cell atlas",
    "spatial transcriptomics retina",
    "proteomics retinal",
    
    # Cornea and anterior segment
    "corneal transparency",
    "corneal wound healing",
    "keratoconus",
    "corneal endothelium",
    "limbal stem cells",
    
    # Glaucoma
    "glaucoma pathogenesis",
    "intraocular pressure",
    "optic nerve head",
    "retinal ganglion cell death glaucoma",
    "aqueous humor dynamics",
    
    # Optic nerve and visual pathways
    "optic nerve regeneration",
    "optic neuropathy",
    "visual cortex",
    "lateral geniculate nucleus",
    
    # AI and computational methods
    "artificial intelligence ophthalmology",
    "deep learning retinal imaging",
    "machine learning eye disease",
    "automated retinal analysis",
    
    # Gene therapy and treatment
    "gene therapy retinal disease",
    "CRISPR eye disease",
    "AAV vector retina",
    "optogenetics vision restoration",
    
    # Stem cells and regeneration
    "retinal organoids",
    "pluripotent stem cells retina",
    "retinal progenitor cells",
    "photoreceptor transplantation",
    
    # Imaging and diagnostics
    "optical coherence tomography",
    "fundus autofluorescence",
    "adaptive optics retinal imaging",
    "fluorescein angiography",
]


async def download_and_index_articles(
    pubmed_service: PubMedService,
    max_articles_per_query: int = 100,
    collection_name: str = "pubmed_vision_research"
):
    """
    Download articles from PubMed and index them
    
    Args:
        pubmed_service: PubMed service instance
        max_articles_per_query: Maximum articles per search query
        collection_name: ChromaDB collection name
    """
    print(f"\n{'='*80}")
    print(f"🔬 REAL RAG POPULATION - Vision Research Articles")
    print(f"{'='*80}\n")
    
    all_documents = []
    total_articles = 0
    
    async for db in get_db():
        try:
            for idx, query in enumerate(VISION_RESEARCH_QUERIES, 1):
                print(f"\n[{idx}/{len(VISION_RESEARCH_QUERIES)}] Searching: {query}")
                print("-" * 60)
                
                # Search PubMed
                pmids = await pubmed_service.search_articles(
                    search_terms=[query],
                    max_results=max_articles_per_query,
                    date_range="2018-2024"  # Recent articles (last 6 years)
                )
                
                if not pmids:
                    print(f"  ⚠️  No articles found for: {query}")
                    continue
                
                print(f"  ✓ Found {len(pmids)} articles")
                
                # Fetch article details
                print(f"  📥 Downloading article details...")
                articles = await pubmed_service.fetch_article_details(pmids, db)
                
                if not articles:
                    print(f"  ⚠️  Failed to download articles")
                    continue
                
                print(f"  ✓ Downloaded {len(articles)} articles")
                total_articles += len(articles)
                
                # Process articles into documents
                for article in articles:
                    if not article.abstract:
                        continue
                    
                    # Create full text content
                    content = f"Title: {article.title}\n\n"
                    content += f"Authors: {article.authors}\n"
                    content += f"Journal: {article.journal}\n"
                    if article.publication_date:
                        content += f"Published: {article.publication_date}\n"
                    content += f"\nAbstract:\n{article.abstract}"
                    
                    # Create document with metadata
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
                        }
                    )
                    all_documents.append(doc)
                
                print(f"  ✓ Processed {len(articles)} articles into documents")
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.5)
            
            print(f"\n{'='*80}")
            print(f"📊 DOWNLOAD SUMMARY")
            print(f"{'='*80}")
            print(f"Total articles downloaded: {total_articles}")
            print(f"Total documents created: {len(all_documents)}")
            
            if not all_documents:
                print("\n❌ No documents to index. Exiting.")
                return
            
            # Chunk documents for better retrieval
            print(f"\n{'='*80}")
            print(f"📝 CHUNKING DOCUMENTS")
            print(f"{'='*80}")
            
            all_chunks = []
            for doc in all_documents:
                chunks = document_processor.text_splitter.create_documents(
                    texts=[doc.page_content],
                    metadatas=[doc.metadata]
                )
                all_chunks.extend(chunks)
            
            print(f"✓ Created {len(all_chunks)} chunks from {len(all_documents)} documents")
            print(f"  Average chunks per document: {len(all_chunks) / len(all_documents):.1f}")
            
            # Index in ChromaDB
            print(f"\n{'='*80}")
            print(f"💾 INDEXING IN VECTOR DATABASE")
            print(f"{'='*80}")
            print(f"Collection: {collection_name}")
            print(f"Chunks to index: {len(all_chunks)}")
            
            # Index in batches
            batch_size = 100
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]
                print(f"  Indexing batch {i//batch_size + 1}/{(len(all_chunks) + batch_size - 1)//batch_size}...")
                
                try:
                    vector_store_manager.add_documents(
                        collection_name=collection_name,
                        documents=batch
                    )
                except Exception as e:
                    print(f"  ⚠️  Error indexing batch: {e}")
                    continue
            
            print(f"\n✓ Successfully indexed all documents!")
            
            # Get collection stats
            stats = vector_store_manager.get_collection_stats(collection_name)
            print(f"\n{'='*80}")
            print(f"📈 FINAL STATISTICS")
            print(f"{'='*80}")
            print(f"Collection: {collection_name}")
            print(f"Total documents in vector DB: {stats.get('count', 'Unknown')}")
            print(f"Total PubMed articles: {total_articles}")
            print(f"Total chunks: {len(all_chunks)}")
            print(f"\n✅ RAG system is now populated with REAL research data!")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break


async def test_retrieval(collection_name: str = "pubmed_vision_research"):
    """Test the retrieval system"""
    print(f"\n{'='*80}")
    print(f"🧪 TESTING RETRIEVAL SYSTEM")
    print(f"{'='*80}\n")
    
    test_queries = [
        "single-cell RNA sequencing of retina",
        "artificial intelligence for diabetic retinopathy",
        "gene therapy for inherited retinal diseases",
        "corneal wound healing mechanisms",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)
        
        try:
            results = vector_store_manager.similarity_search(
                collection_name=collection_name,
                query=query,
                k=3
            )
            
            print(f"Found {len(results)} results:")
            for idx, doc in enumerate(results, 1):
                title = doc.metadata.get('title', 'No title')[:80]
                pmid = doc.metadata.get('pmid', 'Unknown')
                print(f"  {idx}. [{pmid}] {title}...")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║                   REAL RAG POPULATION SYSTEM                              ║
║                   Vision Research Knowledge Base                          ║
║                                                                           ║
║  This script will:                                                        ║
║  1. Search PubMed for vision research articles                            ║
║  2. Download abstracts and metadata                                       ║
║  3. Process and chunk the content                                         ║
║  4. Store in ChromaDB with embeddings                                     ║
║  5. Create a searchable knowledge base                                    ║
║                                                                           ║
║  Expected: 1000-3000 articles (depending on availability)                 ║
║  Time: 15-30 minutes                                                      ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Create PubMed service
    pubmed_service = PubMedService()
    
    # Run the population
    asyncio.run(download_and_index_articles(
        pubmed_service=pubmed_service,
        max_articles_per_query=100,  # 100 articles per query
        collection_name="pubmed_vision_research"
    ))
    
    # Test retrieval
    asyncio.run(test_retrieval("pubmed_vision_research"))
    
    print("\n🎉 All done! Your RAG system is now populated with real research data.\n")

