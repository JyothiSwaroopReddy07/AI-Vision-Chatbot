# Quick Start - Deploy in 5 Minutes

## TL;DR - Copy & Paste These Commands

```bash
# 1. SSH to server
ssh -p 22000 cvemired-admin@eye.som.uci.edu
# Password: bwnxQznp2Dh6

# 2. Clone repo
cd ~
git clone https://github.com/JyothiSwaroopReddy07/AI-Vision-Chatbot.git
cd AI-Vision-Chatbot

# 3. Create .env file
cp deploy/env.production.example .env

# 4. Edit .env - SET THESE THREE REQUIRED VALUES:
nano .env
# - SECRET_KEY=<generate with: openssl rand -hex 32>
# - JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
# - HUGGINGFACE_TOKEN=<get from https://huggingface.co/settings/tokens>
# Save and exit: Ctrl+X, Y, Enter

# 5. Deploy
chmod +x deploy/quick_deploy.sh
./deploy/quick_deploy.sh

# 6. Wait 10-15 minutes for model download

# 7. Access application
# Frontend: http://eye.som.uci.edu:3000
# Backend: http://eye.som.uci.edu:8000/docs
```

## What You Get

- ✅ **Local LLM**: Phi-2 (2.7B parameters) - no OpenAI API needed
- ✅ **RAG Pipeline**: ChromaDB vector database for PubMed articles
- ✅ **Full Stack**: Backend API + Frontend UI + Database
- ✅ **Monitoring**: Grafana + Prometheus dashboards
- ✅ **Background Tasks**: Celery workers for async processing

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://eye.som.uci.edu:3000 | Register new account |
| Backend API | http://eye.som.uci.edu:8000 | - |
| API Docs | http://eye.som.uci.edu:8000/docs | - |
| Grafana | http://eye.som.uci.edu:3001 | admin / admin |
| Prometheus | http://eye.som.uci.edu:9090 | - |

## Common Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check status
docker-compose -f docker-compose.prod.yml ps

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Stop services
docker-compose -f docker-compose.prod.yml down

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### LLM is slow (>10 seconds per response)
- **Cause**: Using CPU instead of GPU
- **Solution**: Normal for CPU. For faster responses, use a server with GPU.

### "Out of memory" errors
```bash
# Edit .env and reduce these values:
nano .env
# MAX_TOKENS=1000
# RETRIEVAL_K=3
# EMBEDDING_BATCH_SIZE=32

# Restart
docker-compose -f docker-compose.prod.yml restart
```

### Service won't start
```bash
# Check logs for the specific service
docker-compose -f docker-compose.prod.yml logs [service_name]

# Common services: llm, backend, frontend, postgres
```

### Can't access from browser
- Check if services are running: `docker-compose -f docker-compose.prod.yml ps`
- Check if ports are open: `sudo lsof -i :3000`
- Try accessing from server: `curl http://localhost:3000`

## Need More Help?

- **Detailed Guide**: See [DEPLOYMENT_STEPS.md](./DEPLOYMENT_STEPS.md)
- **Full Documentation**: See [deploy/DEPLOYMENT_GUIDE.md](./deploy/DEPLOYMENT_GUIDE.md)
- **GitHub Issues**: https://github.com/JyothiSwaroopReddy07/AI-Vision-Chatbot/issues

## Architecture

```
User Browser
    ↓
Frontend (Next.js) :3000
    ↓
Backend (FastAPI) :8000
    ↓
├─ LLM (Phi-2) :8080          ← 2.7B parameter model
├─ ChromaDB :8001              ← Vector database
├─ PostgreSQL :5432            ← User data
└─ Redis :6379                 ← Cache
```

## Performance Expectations

### With GPU (8GB+ VRAM)
- Response time: 1-2 seconds
- Concurrent users: 10+
- Recommended for production

### With CPU Only
- Response time: 5-10 seconds
- Concurrent users: 2-3
- Works but slower

## Next Steps After Deployment

1. **Register an account** at http://eye.som.uci.edu:3000
2. **Test the chat** with: "What is age-related macular degeneration?"
3. **Index PubMed articles** (see [DEPLOYMENT_STEPS.md](./DEPLOYMENT_STEPS.md) Step 13)
4. **Set up monitoring** at http://eye.som.uci.edu:3001
5. **Configure backups** (see deployment guide)

---

**Questions?** Check [DEPLOYMENT_STEPS.md](./DEPLOYMENT_STEPS.md) for detailed instructions.

