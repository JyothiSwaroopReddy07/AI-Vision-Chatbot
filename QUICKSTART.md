# Quick Start Guide - Vision ChatBot Agent

Get up and running in 10 minutes!

## Prerequisites

- Docker & Docker Compose installed
- 16GB RAM minimum (256GB recommended for production)
- 50GB free disk space (7TB recommended for production)

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/vision-chatbot-agent.git
cd vision-chatbot-agent
```

### Step 2: Configure Environment

```bash
cp .env.example .env
nano .env
```

**Minimum required changes:**

```bash
# Generate secrets (run these commands)
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Add to .env
SECRET_KEY=<your-generated-secret>
JWT_SECRET_KEY=<your-generated-jwt-secret>

# If using OpenAI (recommended for best experience)
OPENAI_API_KEY=sk-your-api-key-here

# Update email for PubMed
PUBMED_EMAIL=your@email.com
```

### Step 3: Start Services

```bash
# Build and start all services
docker-compose up -d

# Watch logs (optional)
docker-compose logs -f
```

**Services will start:**
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- ChromaDB: http://localhost:8001
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

### Step 4: Initialize Database

```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Verify database is ready
docker-compose exec backend python -c "from app.core.database import sync_engine; print('Database ready!')"
```

## First Use

### 1. Access the Application

Open your browser: **http://localhost:3000**

### 2. Create Account

Click "Register" and create your account:
- Email: your@email.com
- Username: researcher
- Password: (choose a strong password)
- Full Name: Dr. Your Name (optional)

### 3. Start Chatting

Try these example questions:
- "What are the genetic factors of age-related macular degeneration?"
- "Explain the role of complement pathway in AMD"
- "What genes are involved in retinal degeneration?"

### 4. Upload Files

Click the 📎 icon to upload:
- PDF research papers
- Text files
- Images (OCR will extract text)

### 5. Analyze Gene Sets

Ask pathway analysis questions:
- "Analyze these genes: CFH, ARMS2, C3, C2"
- The system will automatically detect gene lists and offer pathway analysis

## Index PubMed Articles (Admin)

To populate the knowledge base with PubMed articles:

### Option 1: Using API (After Creating Admin User)

```bash
# First, create admin user
docker-compose exec backend python scripts/create_admin.py

# Then trigger indexing
curl -X POST http://localhost:8000/api/v1/pubmed/index \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "search_terms": ["macular degeneration", "retina genetics", "glaucoma"],
    "max_results": 1000,
    "date_range": "2020-2024"
  }'
```

### Option 2: Using Python Script

```bash
docker-compose exec backend python -c "
import asyncio
from app.core.database import SessionLocal
from app.services.pubmed_service import pubmed_service

async def index():
    db = SessionLocal()
    try:
        result = await pubmed_service.run_indexing_job(
            db=db,
            search_terms=[
                'age-related macular degeneration',
                'glaucoma genetics',
                'retina genomics'
            ],
            max_results=1000,
            date_range='2020-2024'
        )
        print(f'Indexed {result[\"articles_indexed\"]} articles')
    finally:
        db.close()

asyncio.run(index())
"
```

**Note:** Indexing may take 15-30 minutes for 1000 articles.

## Verify Installation

### Check All Services

```bash
# Service status
docker-compose ps

# Should show all services as "Up"
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# ChromaDB health
curl http://localhost:8001/api/v1/heartbeat

# Frontend (open in browser)
open http://localhost:3000
```

### View Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs frontend

# Follow logs in real-time
docker-compose logs -f backend
```

## Common Issues

### Issue: Port Already in Use

```bash
# Change ports in docker-compose.yml
# Example: Change frontend port from 3000 to 3001
services:
  frontend:
    ports:
      - "3001:3000"  # Changed from 3000:3000
```

### Issue: Out of Memory

```bash
# Reduce batch sizes in .env
EMBEDDING_BATCH_SIZE=16
PUBMED_BATCH_SIZE=25

# Restart services
docker-compose restart backend
```

### Issue: ChromaDB Connection Error

```bash
# Restart ChromaDB
docker-compose restart chromadb

# Wait 10 seconds and try again
sleep 10
```

### Issue: Database Migration Fails

```bash
# Reset database (WARNING: Deletes all data)
docker-compose down -v
docker-compose up -d
docker-compose exec backend alembic upgrade head
```

## Next Steps

### 1. Configure Settings

- Access user preferences in the UI
- Adjust LLM temperature and token limits
- Configure retrieval settings

### 2. Index More Literature

- Index specific research areas
- Add custom search terms
- Schedule periodic re-indexing

### 3. Upload Your Research

- Upload your lab's papers
- Upload protocols and notes
- Build your private knowledge base

### 4. Explore Pathway Analysis

- Analyze RNA-seq results
- Compare gene sets
- Export results for publications

### 5. Set Up Production

- Configure SSL certificates
- Set up regular backups
- Configure monitoring alerts
- See DEPLOYMENT.md for details

## Using the Chat Interface

### Basic Chat

```
You: What causes AMD?
AI: Age-related macular degeneration (AMD) has multiple causes...
    [Sources: 3 citations shown]
```

### With File Upload

1. Click 📎 to upload PDF
2. Wait for processing
3. Ask questions about the content
```
You: Summarize the methods section of the uploaded paper
```

### Gene Set Analysis

```
You: Analyze pathway enrichment for: CFH, ARMS2, C3, C2, CFI
AI: I'll analyze these genes for pathway enrichment...
    [Shows pathway analysis results]
```

## Tips for Best Results

### 1. Ask Specific Questions

✅ Good: "What is the role of CFH in AMD pathogenesis?"
❌ Vague: "Tell me about eyes"

### 2. Provide Context

✅ Good: "In retinal pigment epithelium cells, how does oxidative stress affect..."
❌ Vague: "What does stress do?"

### 3. Use Gene Symbols

✅ Good: "CFH, ARMS2, C3"
❌ Confusing: "complement factor H gene"

### 4. Upload Relevant Files

- Upload papers before asking about them
- Use clear filenames
- One topic per conversation for best context

## Getting Help

### Check Documentation

- README.md - Overview and features
- ARCHITECTURE.md - System design
- DEPLOYMENT.md - Production deployment

### API Documentation

Visit http://localhost:8000/docs for interactive API documentation

### View Logs

```bash
# Real-time logs
docker-compose logs -f

# Specific service logs
docker-compose logs backend
docker-compose logs celery_worker
```

### Community Support

- GitHub Issues: Report bugs or request features
- Discussions: Ask questions and share ideas
- Email: support@visionchatbot.com

## Development Mode

### Run Backend with Hot Reload

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Frontend with Hot Reload

```bash
cd frontend
npm install
npm run dev
```

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (deletes data)
docker-compose down -v

# Stop specific service
docker-compose stop backend
```

## Updating

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d

# Run new migrations
docker-compose exec backend alembic upgrade head
```

---

## 🎉 You're Ready!

Your Vision ChatBot Agent is now running. Start exploring vision research with AI assistance!

**Access:** http://localhost:3000

**Need help?** Check DEPLOYMENT.md for detailed configuration options.

