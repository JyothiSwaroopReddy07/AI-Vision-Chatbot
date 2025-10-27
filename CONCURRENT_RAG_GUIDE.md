# Concurrent RAG Population Guide

## 🚀 5x Faster RAG Population with Multiple API Keys

This system uses **5 PubMed API keys concurrently** to populate your RAG database **5x faster**.

---

## 📊 Performance Comparison

| Configuration | Requests/Second | Time for 10,000 articles |
|--------------|----------------|-------------------------|
| Single API Key | 3 req/sec | ~5-6 hours |
| 5 API Keys (Concurrent) | 50 req/sec | ~1 hour |

---

## 🔑 Step 1: Get Your API Keys

1. Go to https://www.ncbi.nlm.nih.gov/account/
2. Sign in or create an NCBI account
3. Navigate to "Settings" → "API Key Management"
4. Create 5 API keys
5. Copy each key

---

## ⚙️ Step 2: Configure API Keys

### Option A: Using the Setup Script (Recommended)

```bash
cd /Users/user/AI-Vision-Chatbot
./backend/scripts/setup_api_keys.sh
```

Enter your 5 API keys when prompted.

### Option B: Manual Configuration

Add to your `.env` file:

```bash
PUBMED_API_KEY_1=your_first_api_key_here
PUBMED_API_KEY_2=your_second_api_key_here
PUBMED_API_KEY_3=your_third_api_key_here
PUBMED_API_KEY_4=your_fourth_api_key_here
PUBMED_API_KEY_5=your_fifth_api_key_here
```

---

## 🏗️ Step 3: Rebuild Docker Containers

```bash
cd /Users/user/AI-Vision-Chatbot
docker-compose down
docker-compose up -d --build backend celery_worker
```

---

## 🚀 Step 4: Run Concurrent Population

```bash
# Run in foreground (see live progress)
docker-compose exec backend python scripts/production_rag_populator.py

# Run in background
nohup docker-compose exec -T backend python scripts/production_rag_populator.py > /tmp/rag_population.log 2>&1 &

# Monitor progress
tail -f /tmp/rag_population.log
```

---

## 📊 Monitor Progress

### Check Articles Downloaded

```bash
docker-compose exec -T backend python -c "
import json
p = json.load(open('/data/rag_progress.json'))
print(f'✓ Completed: {len(p[\"completed_queries\"])}/248 queries')
print(f'✓ Downloaded: {len(p[\"downloaded_pmids\"])} articles')
print(f'✓ Indexed: {len(p[\"indexed_pmids\"])} articles')
"
```

### Check ChromaDB Collection Size

```bash
docker-compose exec -T backend python -c "
from app.rag.vector_store import vector_store_manager
collection = vector_store_manager.get_collection('pubmed_vision_research')
print(f'📚 Total chunks indexed: {collection.count()}')
"
```

### View Worker Activity

```bash
# Watch the log file
tail -f /tmp/rag_population.log | grep "Worker"

# Check current processing
docker-compose logs --tail=50 backend | grep "🔍"
```

---

## 🎯 How It Works

### Architecture

```
┌─────────────────────────────────────────────────┐
│           Concurrent RAG Populator              │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │ ... │
│  │ API Key1 │  │ API Key2 │  │ API Key3 │     │
│  │ 10 req/s │  │ 10 req/s │  │ 10 req/s │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │            │
│       └─────────────┴─────────────┘            │
│                     │                          │
│              ┌──────▼───────┐                 │
│              │   PubMed     │                 │
│              │   Search     │                 │
│              └──────┬───────┘                 │
│                     │                          │
│              ┌──────▼───────┐                 │
│              │   Download   │                 │
│              │   Articles   │                 │
│              └──────┬───────┘                 │
│                     │                          │
│              ┌──────▼───────┐                 │
│              │    Chunk &   │                 │
│              │    Index     │                 │
│              └──────┬───────┘                 │
│                     │                          │
│              ┌──────▼───────┐                 │
│              │   ChromaDB   │                 │
│              └──────────────┘                 │
└─────────────────────────────────────────────────┘
```

### Features

1. **Round-Robin Distribution**: Queries are distributed evenly across workers
2. **Rate Limiting**: Each worker respects 10 req/sec limit per API key
3. **Concurrent Processing**: Multiple queries processed simultaneously
4. **Progress Tracking**: Shared progress file with thread-safe updates
5. **Fault Tolerance**: Automatic retries with exponential backoff
6. **Resume Capability**: Picks up where it left off after interruption

### Worker Distribution Example

```
Query 1  → Worker 1 (API Key 1)
Query 2  → Worker 2 (API Key 2)
Query 3  → Worker 3 (API Key 3)
Query 4  → Worker 4 (API Key 4)
Query 5  → Worker 5 (API Key 5)
Query 6  → Worker 1 (API Key 1)  ← Round-robin restart
Query 7  → Worker 2 (API Key 2)
...
```

---

## 📈 Expected Results

### With 5 API Keys

- **Total Capacity**: 50 requests/second
- **Queries**: 248 search terms
- **Articles per Query**: ~500 articles
- **Total Articles**: ~124,000 articles
- **Estimated Time**: ~60 minutes
- **PDFs Downloaded**: ~2,000+ full-text papers

### Progress Output

```
[Worker 1] [Q1/248] 🔍 retinal degeneration
======================================================================
  📡 Searching PubMed...
  ✓ Found 500 articles
  ℹ️  450 new articles to download
  ⬇️  Downloading with Worker 1...
  Progress: 50/450 articles processed
  Progress: 100/450 articles processed
  ...
  ✓ Downloaded 450 articles (12 with PDFs)
  📝 Chunking documents...
  ✓ Created 1,203 chunks
  💾 Indexing in ChromaDB...
  ✅ Indexed 1,203 chunks

  📊 Progress: 1/248 queries | 450 articles | 12 PDFs | 1203 indexed
```

---

## 🛠️ Troubleshooting

### Issue: "No API keys found"

**Solution**: Check your `.env` file has the keys:
```bash
grep "PUBMED_API_KEY" .env
```

### Issue: "HTTP Error 429: Too Many Requests"

**Solution**: This is normal. The system automatically retries with backoff.

### Issue: Slow progress

**Solution**: 
1. Check all 5 API keys are configured
2. Verify workers are running: `docker-compose logs backend | grep Worker`
3. Ensure good internet connection

### Issue: ChromaDB connection errors

**Solution**:
```bash
docker-compose restart chromadb
docker-compose restart backend
```

---

## 🎉 After Population Complete

### Verify Data

```bash
# Check total indexed chunks
docker-compose exec -T backend python -c "
from app.rag.vector_store import vector_store_manager
collection = vector_store_manager.get_collection('pubmed_vision_research')
print(f'Total chunks: {collection.count()}')
"

# Check progress file
docker-compose exec backend cat /data/rag_progress.json | jq
```

### Backup Your Data

```bash
cd /Users/user/AI-Vision-Chatbot
docker-compose exec -T backend tar czf /tmp/data_backup.tar.gz /data
docker cp vision_backend:/tmp/data_backup.tar.gz ./data_backup_complete.tar.gz
```

### Test RAG System

```bash
# Test a query
docker-compose exec -T backend python -c "
from app.rag.vector_store import vector_store_manager
results = vector_store_manager.search('age-related macular degeneration treatment', k=5)
for i, doc in enumerate(results, 1):
    print(f'{i}. {doc.metadata.get(\"title\", \"Untitled\")}')
"
```

---

## 💡 Pro Tips

1. **Run overnight**: Let it run for 1-2 hours uninterrupted
2. **Monitor disk space**: Ensure 5+ GB available
3. **Use tmux/screen**: Keep session alive if SSH
4. **Check logs**: `tail -f /tmp/rag_population.log` for real-time monitoring
5. **Resume anytime**: Safe to Ctrl+C and restart - progress is saved

---

## 📝 Rate Limit Compliance

This system is fully compliant with NCBI E-utilities guidelines:

- ✅ 10 requests/second per API key (enforced by rate limiter)
- ✅ Proper API key usage (each key tracked separately)
- ✅ Email configured in Entrez
- ✅ Exponential backoff on errors
- ✅ Respectful retry logic

**Reference**: https://www.ncbi.nlm.nih.gov/books/NBK25497/

---

## 🚀 Quick Start (TL;DR)

```bash
# 1. Add API keys to .env
cd /Users/user/AI-Vision-Chatbot
./backend/scripts/setup_api_keys.sh

# 2. Rebuild
docker-compose up -d --build backend

# 3. Run
docker-compose exec backend python scripts/production_rag_populator.py

# 4. Monitor
tail -f /tmp/rag_population.log
```

Done! Your RAG database will be populated 5x faster! 🎉

