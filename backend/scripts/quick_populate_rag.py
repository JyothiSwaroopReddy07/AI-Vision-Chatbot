#!/usr/bin/env python3
"""
Quick RAG Population - Download 50-100 real articles for immediate testing
"""

import sys
import os
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import get_db
from app.services.pubmed_service import PubMedService
from app.rag.vector_store import vector_store_manager
from app.rag.document_processor import document_processor
from langchain.schema import Document


# Quick set of high-impact queries
QUICK_QUERIES = [
    "retinal degeneration",
    "diabetic retinopathy",
    "age-related macular degeneration",
    "glaucoma pathogenesis",
    "single-cell transcriptomics retina",
    "gene therapy retinal disease",
    "artificial intelligence ophthalmology",
    "retinal organoids",
]


async def quick_populate():
    """Quickly populate RAG with 50-100 articles"""
    print("🚀 QUICK RAG POPULATION - Downloading ~50-100 real articles")
    print("=" * 70)
    
    pubmed_service = PubMedService()
    all_documents = []
    total_articles = 0
    
    async for db in get_db():
        try:
            for idx, query in enumerate(QUICK_QUERIES, 1):
                print(f"\n[{idx}/{len(QUICK_QUERIES)}] {query}")
                
                # Search - limit to 10 per query for speed
                pmids = await pubmed_service.search_articles(
                    search_terms=[query],
                    max_results=10,
                    date_range=None  # No date filter for simpler queries
                )
                
                if not pmids:
                    print(f"  ⚠️  No results")
                    continue
                
                print(f"  ✓ Found {len(pmids)} PMIDs")
                
                # Fetch articles
                articles = await pubmed_service.fetch_article_details(pmids, db)
                print(f"  ✓ Downloaded {len(articles)} articles")
                total_articles += len(articles)
                
                # Process into documents
                for article in articles:
                    if not article.abstract:
                        continue
                    
                    content = f"Title: {article.title}\n\n"
                    content += f"Authors: {article.authors}\n"
                    content += f"Journal: {article.journal}\n"
                    if article.publication_date:
                        content += f"Published: {article.publication_date}\n"
                    content += f"\nAbstract:\n{article.abstract}"
                    
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
                
                await asyncio.sleep(0.5)
            
            print(f"\n{'='*70}")
            print(f"📊 Downloaded {total_articles} articles")
            print(f"📄 Created {len(all_documents)} documents")
            
            # Chunk documents
            print(f"\n📝 Chunking...")
            all_chunks = []
            for doc in all_documents:
                chunks = document_processor.text_splitter.create_documents(
                    texts=[doc.page_content],
                    metadatas=[doc.metadata]
                )
                all_chunks.extend(chunks)
            
            print(f"✓ Created {len(all_chunks)} chunks")
            
            # Index in ChromaDB
            print(f"\n💾 Indexing in ChromaDB...")
            collection_name = "pubmed_vision_research"
            
            batch_size = 50
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]
                print(f"  Batch {i//batch_size + 1}/{(len(all_chunks) + batch_size - 1)//batch_size}")
                
                try:
                    vector_store_manager.add_documents(
                        collection_name=collection_name,
                        documents=batch
                    )
                except Exception as e:
                    print(f"  ⚠️  Error: {e}")
            
            print(f"\n✅ SUCCESS!")
            print(f"{'='*70}")
            print(f"Articles: {total_articles}")
            print(f"Chunks indexed: {len(all_chunks)}")
            print(f"Collection: {collection_name}")
            
            # Test retrieval
            print(f"\n🧪 Testing retrieval...")
            results = vector_store_manager.similarity_search(
                collection_name=collection_name,
                query="diabetic retinopathy treatment",
                k=3
            )
            print(f"✓ Retrieved {len(results)} results")
            for idx, doc in enumerate(results, 1):
                title = doc.metadata.get('title', 'No title')[:60]
                pmid = doc.metadata.get('pmid', 'Unknown')
                print(f"  {idx}. [{pmid}] {title}...")
            
            print(f"\n🎉 RAG is ready with REAL data!\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break


if __name__ == "__main__":
    asyncio.run(quick_populate())

