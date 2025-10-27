# RAG Population Scripts

## 📁 Files in This Directory

### `production_rag_populator.py` ⭐
**Main concurrent RAG population script with full-text PDF extraction**

**Features:**
- ✅ Uses 5 PubMed API keys concurrently (50 req/sec total)
- ✅ Extracts full-text PDFs from PubMed Central (PMC)
- ✅ Downloads abstracts for all articles
- ✅ Indexes both abstracts and full text in ChromaDB
- ✅ Automatic progress saving and resume capability
- ✅ Handles rate limiting and retries

**PDF Extraction:**
- Fetches PMC ID from article metadata
- Constructs URL: `https://pmc.ncbi.nlm.nih.gov/articles/PMC{ID}/pdf/`
- Downloads only open-access PDFs (respects access restrictions)
- Extracts **complete full text** from ALL pages using PyPDF2
- No character limits - entire PDF content is indexed
- LangChain text splitter automatically chunks into optimal embedding sizes

**Usage:**
```bash
# Configure API keys first
./setup_api_keys.sh

# Run the populator
docker-compose exec backend python scripts/production_rag_populator.py
```

**Expected Results:**
- ~10,000+ articles with abstracts
- ~2,000+ articles with full-text PDFs
- ~1 hour completion time with 5 API keys

---

### `setup_api_keys.sh`
**Interactive script to configure multiple PubMed API keys**

Sets up environment variables:
- `PUBMED_API_KEY_1` through `PUBMED_API_KEY_5`

**Usage:**
```bash
./setup_api_keys.sh
```

---

## 🚀 Quick Start

### 1. Get API Keys
- Visit: https://www.ncbi.nlm.nih.gov/account/
- Create 5 API keys
- Each key allows 10 requests/second

### 2. Configure Keys
```bash
cd /Users/user/AI-Vision-Chatbot/backend/scripts
./setup_api_keys.sh
```

### 3. Rebuild Docker
```bash
cd /Users/user/AI-Vision-Chatbot
docker-compose up -d --build backend celery_worker
```

### 4. Run Population
```bash
# Foreground (see progress)
docker-compose exec backend python scripts/production_rag_populator.py

# Background
nohup docker-compose exec -T backend python scripts/production_rag_populator.py > /tmp/rag_population.log 2>&1 &

# Monitor
tail -f /tmp/rag_population.log
```

---

## 📊 How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Query Distribution                         │
│   Query 1 → Worker 1 (API Key 1, 10 req/sec)              │
│   Query 2 → Worker 2 (API Key 2, 10 req/sec)              │
│   Query 3 → Worker 3 (API Key 3, 10 req/sec)              │
│   Query 4 → Worker 4 (API Key 4, 10 req/sec)              │
│   Query 5 → Worker 5 (API Key 5, 10 req/sec)              │
│   Query 6 → Worker 1 (round-robin continues...)           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              For Each Article (Parallel):                   │
│                                                             │
│  1. Search PubMed → Get PMIDs                              │
│  2. Fetch Metadata → Extract PMC ID, DOI, title, etc.     │
│  3. Download PDF (if PMC ID exists):                        │
│     URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC{ID}/pdf/│
│  4. Extract Full Text from PDF (PyPDF2)                    │
│  5. Combine: Abstract + Full Text                          │
│  6. Chunk Content (LangChain)                              │
│  7. Index in ChromaDB (with embeddings)                    │
└─────────────────────────────────────────────────────────────┘
```

### PDF Extraction Flow

```python
# 1. Fetch article metadata
metadata = await fetch_article_metadata(pmid)
# Returns: {pmid, pmc_id, title, abstract, authors, ...}

# 2. If PMC ID exists, download PDF
if metadata['pmc_id']:
    pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/pdf/"
    pdf_text = await download_pmc_pdf(pmc_id, pmid)

# 3. Create document with full text
content = f"{title}\n{abstract}\n\nFull Text:\n{pdf_text}"

# 4. Index in ChromaDB
chunks = chunk_document(content)
index_in_chromadb(chunks)
```

---

## 📈 Performance

### Single API Key
- 10 requests/second
- ~5-6 hours for 10,000 articles

### 5 API Keys (Concurrent)
- 50 requests/second
- ~1 hour for 10,000 articles
- **5x faster!** 🚀

---

## 🔍 PDF Extraction Details

### PMC PDF URL Format
According to [PMC documentation](https://pmc.ncbi.nlm.nih.gov/), the PDF URL format is:
```
https://pmc.ncbi.nlm.nih.gov/articles/PMC{ID}/pdf/
```

Example:
- PMC ID: 5967598
- URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC5967598/pdf/

### Open Access Only
- Only downloads PDFs for open-access articles
- Respects access restrictions
- Falls back to abstract-only for restricted articles

### Text Extraction
- Uses PyPDF2 for PDF text extraction
- **Extracts ALL pages completely** - no character limits
- Preserves structure and formatting
- LangChain's RecursiveCharacterTextSplitter automatically breaks documents into chunks:
  - Chunk size: 1,000 characters
  - Chunk overlap: 200 characters
  - Smart splitting at sentence/paragraph boundaries
- Embedding model processes each chunk independently
- Large PDFs (50+ pages) may generate 100+ chunks - this is normal and optimal for search

---

## 📁 Data Storage

### Progress File
Location: `/data/rag_progress.json`

```json
{
  "completed_queries": ["retinal degeneration", "diabetic retinopathy"],
  "downloaded_pmids": ["12345", "67890"],
  "indexed_pmids": ["12345", "67890"],
  "failed_pmids": ["11111"]
}
```

### PDF Files
Location: `/data/pubmed_pdfs/`

Format: `{PMID}_PMC{PMC_ID}.pdf`

Example: `39688851_PMC5967598.pdf`

### ChromaDB Collection
Name: `pubmed_vision_research`

Metadata per chunk:
```python
{
    "source": "pubmed",
    "pmid": "39688851",
    "pmc_id": "PMC5967598",
    "title": "Article Title",
    "authors": "Author 1, Author 2",
    "journal": "Journal Name",
    "doi": "10.1234/journal.56789",
    "publication_date": "2024",
    "query": "retinal degeneration",
    "has_full_text": true  # Indicates PDF was extracted
}
```

---

## 🛠️ Troubleshooting

### No PDFs Downloaded
**Issue:** Articles downloaded but no PDFs

**Solution:** Check if articles have PMC IDs:
```bash
docker-compose exec backend python -c "
import json
p = json.load(open('/data/rag_progress.json'))
print(f'Total articles: {len(p[\"downloaded_pmids\"])}')
# Check logs for PMC ID mentions
"
```

Most articles (~80%) don't have open-access PDFs. This is normal.

### Rate Limiting Errors
**Issue:** HTTP 429 errors

**Solution:** The script automatically retries. This is normal behavior.

### PDF Extraction Failures
**Issue:** Some PDFs fail to extract

**Solution:** 
- Some PDFs are scanned images (no extractable text)
- Some PDFs have complex formatting
- Falls back to abstract-only indexing

---

## 📝 Rate Limit Compliance

Fully compliant with NCBI guidelines:
- ✅ 10 req/sec per API key maximum
- ✅ Proper API key authentication
- ✅ Email configured
- ✅ Exponential backoff on errors
- ✅ Respectful retry logic

Reference: https://www.ncbi.nlm.nih.gov/books/NBK25497/

---

## 💡 Pro Tips

1. **Monitor Progress:**
   ```bash
   watch -n 5 'docker-compose exec -T backend python -c "import json; p=json.load(open(\"/data/rag_progress.json\")); print(f\"Queries: {len(p[\\\"completed_queries\\\"])}/~100\\nArticles: {len(p[\\\"downloaded_pmids\\\"])}\\nIndexed: {len(p[\\\"indexed_pmids\\\"])}\")"'
   ```

2. **Check PDF Success Rate:**
   ```bash
   docker-compose exec backend bash -c "ls -1 /data/pubmed_pdfs/ | wc -l"
   ```

3. **View Latest Articles:**
   ```bash
   docker-compose exec backend python -c "
   from app.rag.vector_store import vector_store_manager
   results = vector_store_manager.search('retinal degeneration', k=3)
   for i, doc in enumerate(results, 1):
       print(f'{i}. {doc.metadata.get(\"title\", \"Untitled\")}')
       print(f'   Full text: {doc.metadata.get(\"has_full_text\", False)}')
   "
   ```

4. **Resume After Interruption:**
   - Just rerun the script
   - It automatically picks up where it left off
   - Progress is saved every 50 articles

---

## 🎯 Expected Results

### After Full Run (~1 hour with 5 API keys)

**Articles:**
- ~10,000+ total articles indexed
- ~2,000+ with full-text PDFs (~20%)
- ~8,000+ with abstracts only (~80%)

**ChromaDB:**
- ~50,000+ chunks total
- Average 5 chunks per article
- Full-text articles: 10-20 chunks
- Abstract-only: 1-3 chunks

**Storage:**
- PDFs: ~2-5 GB
- ChromaDB: ~500 MB - 1 GB
- Progress file: <1 MB

---

For detailed guide, see `CONCURRENT_RAG_GUIDE.md` in project root.

