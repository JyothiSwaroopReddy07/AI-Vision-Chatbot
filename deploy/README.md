# Server Deployment Instructions

This directory contains all the files needed to deploy the AI-Vision-Chatbot on the UCI Linux server with a self-hosted 2B parameter LLM.

## Quick Start (Recommended)

### Option 1: Automated Setup

1. **SSH into the server:**
   ```bash
   ssh -p 22000 cvemired-admin@eye.som.uci.edu
   # Password: bwnxQznp2Dh6
   ```

2. **Clone the repository:**
   ```bash
   cd ~
   git clone https://github.com/JyothiSwaroopReddy07/AI-Vision-Chatbot.git
   cd AI-Vision-Chatbot
   ```

3. **Create .env file:**
   ```bash
   cp deploy/env.production.example .env
   nano .env
   ```
   
   **Required changes in .env:**
   - Set `SECRET_KEY` (generate with: `openssl rand -hex 32`)
   - Set `JWT_SECRET_KEY` (generate with: `openssl rand -hex 32`)
   - Set `HUGGINGFACE_TOKEN` (get from https://huggingface.co/settings/tokens)
   - Ensure `LLM_PROVIDER=local`
   - Optionally set `PUBMED_API_KEY` for better rate limits

4. **Run the deployment script:**
   ```bash
   chmod +x deploy/quick_deploy.sh
   ./deploy/quick_deploy.sh
   ```

5. **Wait for deployment to complete** (10-15 minutes for model download)

6. **Access the application:**
   - Frontend: http://eye.som.uci.edu:3000
   - Backend: http://eye.som.uci.edu:8000/docs

### Option 2: Manual Setup

Follow the detailed instructions in [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

## Files in This Directory

- **`server_setup.sh`** - Installs Docker, Docker Compose, and sets up the environment
- **`quick_deploy.sh`** - Quick deployment script (run after setup)
- **`env.production.example`** - Example environment configuration
- **`DEPLOYMENT_GUIDE.md`** - Comprehensive deployment guide
- **`README.md`** - This file

## Architecture

The deployment includes:

1. **Local LLM Service** - Phi-2 (2.7B parameters) running on text-generation-inference
2. **Backend API** - FastAPI with RAG pipeline
3. **Frontend** - Next.js web application
4. **PostgreSQL** - User data and chat history
5. **ChromaDB** - Vector database for embeddings
6. **Redis** - Caching and Celery broker
7. **Celery Workers** - Background task processing
8. **Nginx** - Reverse proxy (port 8888, avoiding port 80)
9. **Prometheus + Grafana** - Monitoring

## Port Configuration

**Important:** Port 80 is reserved for Texera application. We use alternative ports:

- Frontend: 3000
- Backend: 8000
- Nginx: 8888 (main entry point)
- LLM: 8080
- PostgreSQL: 5432
- Redis: 6379
- ChromaDB: 8001
- Grafana: 3001
- Prometheus: 9090

## System Requirements

### Minimum
- 16GB RAM
- 100GB disk space
- 4 CPU cores
- Ubuntu 20.04+ or Debian 11+

### Recommended
- 32GB RAM
- 200GB disk space
- 8 CPU cores
- NVIDIA GPU with 8GB+ VRAM (for faster inference)

## LLM Model Options

The default model is **microsoft/phi-2** (2.7B parameters). Alternative options:

### Smaller (faster, less accurate)
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0` (1.1B)
- `stabilityai/stablelm-2-1_6b` (1.6B)

### Larger (slower, more accurate)
- `mistralai/Mistral-7B-Instruct-v0.2` (7B, needs GPU)
- `meta-llama/Llama-2-7b-chat-hf` (7B, needs GPU)

To change model, edit `.env`:
```bash
LOCAL_LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

## Monitoring Deployment

### Check service status
```bash
docker-compose -f docker-compose.prod.yml ps
```

### View logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f llm
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Check if LLM is ready
```bash
# Wait for "Model loaded successfully" message
docker-compose -f docker-compose.prod.yml logs llm | grep -i "ready\|loaded"

# Test LLM directly
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "max_tokens": 10}'
```

## Common Issues

### 1. LLM Service Won't Start

**Symptom:** LLM container keeps restarting

**Solutions:**
- Check logs: `docker-compose -f docker-compose.prod.yml logs llm`
- Verify Hugging Face token is set in .env
- Check available memory: `free -h`
- If out of memory, use a smaller model

### 2. No GPU Detected

**Symptom:** LLM is very slow (>10 seconds per response)

**Solutions:**
- Check GPU: `nvidia-smi`
- If no GPU, edit `docker-compose.prod.yml` and remove the GPU requirements
- Or use CPU-optimized model (quantized)

### 3. Backend Can't Connect to LLM

**Symptom:** Chat returns errors about LLM connection

**Solutions:**
- Verify LLM is running: `docker-compose -f docker-compose.prod.yml ps llm`
- Check LLM health: `curl http://localhost:8080/health`
- Verify `.env` has: `LOCAL_LLM_BASE_URL=http://llm:80`

### 4. Port Already in Use

**Symptom:** Docker Compose fails with "port already allocated"

**Solutions:**
- Check what's using the port: `sudo lsof -i :PORT_NUMBER`
- Change port in `docker-compose.prod.yml`
- Stop conflicting service

### 5. Database Migration Fails

**Symptom:** Backend won't start, database errors

**Solutions:**
```bash
# Run migrations manually
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Check database connection
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.core.database import engine; print('OK')"
```

## Maintenance Commands

### Restart services
```bash
docker-compose -f docker-compose.prod.yml restart
```

### Stop services
```bash
docker-compose -f docker-compose.prod.yml down
```

### Update application
```bash
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
```

### Backup data
```bash
# Backup database
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres visiondb > backup.sql

# Backup ChromaDB
tar -czf chromadb_backup.tar.gz data/chromadb/
```

### Clean up
```bash
# Remove unused Docker images
docker system prune -a

# Remove unused volumes (WARNING: deletes data)
docker volume prune
```

## Performance Tuning

### For GPU Servers
1. Ensure NVIDIA drivers installed
2. Set `LOCAL_LLM_DEVICE=cuda` in .env
3. Monitor: `watch -n 1 nvidia-smi`

### For CPU-Only Servers
1. Use quantized models (4-bit or 8-bit)
2. Reduce `MAX_TOKENS=1000` in .env
3. Reduce `RETRIEVAL_K=3` in .env
4. Increase `CELERY_TASK_TIME_LIMIT=7200` in .env

### Memory Optimization
```bash
# In .env:
EMBEDDING_BATCH_SIZE=32
DATABASE_POOL_SIZE=10

# In docker-compose.prod.yml (celery_worker):
command: celery -A app.celery_app.celery_app worker --loglevel=info --concurrency=2
```

## Security Checklist

- [ ] Changed `SECRET_KEY` in .env
- [ ] Changed `JWT_SECRET_KEY` in .env
- [ ] Set strong PostgreSQL password
- [ ] Configured firewall (ufw or iptables)
- [ ] Enabled HTTPS (if using domain)
- [ ] Restricted database access to localhost
- [ ] Regular security updates: `apt update && apt upgrade`

## Testing the Deployment

### 1. Test Backend Health
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### 2. Test LLM Service
```bash
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is AMD?", "max_tokens": 50}'
```

### 3. Test Frontend
```bash
curl http://localhost:3000
# Should return HTML
```

### 4. Test Full Pipeline
1. Open browser: http://eye.som.uci.edu:3000
2. Register a new account
3. Ask a question: "What is age-related macular degeneration?"
4. Verify response with citations

## Getting Help

- **Logs:** `docker-compose -f docker-compose.prod.yml logs -f`
- **Service Status:** `docker-compose -f docker-compose.prod.yml ps`
- **GitHub Issues:** https://github.com/JyothiSwaroopReddy07/AI-Vision-Chatbot/issues
- **Deployment Guide:** [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

## Next Steps After Deployment

1. **Index PubMed Articles:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/pubmed/index \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"search_terms": ["retina", "AMD"], "max_results": 1000}'
   ```

2. **Configure Monitoring:**
   - Access Grafana: http://eye.som.uci.edu:3001
   - Login: admin/admin
   - Set up dashboards

3. **Set Up Backups:**
   - Schedule daily database backups
   - Schedule weekly ChromaDB backups

4. **Enable HTTPS:**
   - Get SSL certificate (Let's Encrypt)
   - Configure nginx with SSL

## Support

For issues specific to this deployment:
1. Check logs first
2. Review [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
3. Open GitHub issue with logs attached

