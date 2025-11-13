# Production Deployment Guide - AI-Vision-Chatbot with Local LLM

This guide will help you deploy the AI-Vision-Chatbot application on the UCI Linux server with a self-hosted 2B parameter LLM.

## Prerequisites

- SSH access to `eye.som.uci.edu` on port 22000
- Server with:
  - Ubuntu/Debian Linux
  - 16GB+ RAM (32GB recommended)
  - 100GB+ disk space
  - GPU (optional, but recommended for faster inference)
  - Docker and Docker Compose

## Deployment Steps

### Step 1: Connect to the Server

```bash
ssh -p 22000 cvemired-admin@eye.som.uci.edu
# Password: bwnxQznp2Dh6
```

### Step 2: Run the Setup Script

```bash
# Download the setup script
curl -O https://raw.githubusercontent.com/JyothiSwaroopReddy07/AI-Vision-Chatbot/main/deploy/server_setup.sh

# Make it executable
chmod +x server_setup.sh

# Run the setup (this will install Docker if needed)
./server_setup.sh
```

**Note:** If Docker was just installed, you may need to log out and log back in for group permissions to take effect.

### Step 3: Configure Environment Variables

```bash
cd ~/ai-vision-chatbot

# Copy the example environment file
cp deploy/env.production.example .env

# Edit the .env file with your settings
nano .env
```

**Important settings to configure:**

1. **Secret Keys** (generate random strings):
   ```bash
   SECRET_KEY=$(openssl rand -hex 32)
   JWT_SECRET_KEY=$(openssl rand -hex 32)
   ```

2. **Hugging Face Token** (required for downloading models):
   - Get token from: https://huggingface.co/settings/tokens
   - Set: `HUGGINGFACE_TOKEN=your_token_here`

3. **LLM Provider**:
   ```
   LLM_PROVIDER=local
   LOCAL_LLM_BASE_URL=http://llm:80
   LOCAL_LLM_MODEL=microsoft/phi-2
   ```

4. **Server URLs**:
   ```
   ALLOWED_ORIGINS=http://eye.som.uci.edu:3000,http://eye.som.uci.edu:8888
   ```

5. **Optional - PubMed API Key** (for better rate limits):
   - Get from: https://www.ncbi.nlm.nih.gov/account/
   - Set: `PUBMED_API_KEY=your_key_here`

### Step 4: Check GPU Availability

```bash
# Check if NVIDIA GPU is available
nvidia-smi

# If GPU is available, the LLM will use it automatically
# If no GPU, the deployment will use CPU (slower but works)
```

**If no GPU is detected**, you'll need to modify `docker-compose.prod.yml`:

```bash
# Edit docker-compose file
nano docker-compose.prod.yml

# Comment out the GPU-based LLM service and use CPU version
# Or remove the deploy.resources section from the llm service
```

### Step 5: Start the Application

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d --build

# This will:
# 1. Download the Phi-2 model (~5GB, takes 10-15 minutes)
# 2. Build backend and frontend containers
# 3. Start PostgreSQL, Redis, ChromaDB
# 4. Start the LLM inference service
# 5. Start Celery workers
# 6. Start monitoring services
```

### Step 6: Monitor the Deployment

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs (all services)
docker-compose -f docker-compose.prod.yml logs -f

# View logs (specific service)
docker-compose -f docker-compose.prod.yml logs -f llm
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend

# Check if LLM is ready (wait for "Model loaded successfully")
docker-compose -f docker-compose.prod.yml logs -f llm | grep -i "ready"
```

### Step 7: Initialize the Database

```bash
# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify database is ready
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.core.database import engine; print('Database connected!')"
```

### Step 8: Access the Application

Once all services are running:

- **Frontend**: http://eye.som.uci.edu:3000
- **Backend API**: http://eye.som.uci.edu:8000
- **API Documentation**: http://eye.som.uci.edu:8000/docs
- **Nginx Proxy**: http://eye.som.uci.edu:8888
- **Grafana Dashboard**: http://eye.som.uci.edu:3001 (admin/admin)
- **Prometheus**: http://eye.som.uci.edu:9090

### Step 9: Test the LLM

```bash
# Test the LLM directly
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is age-related macular degeneration?",
    "max_tokens": 100
  }'

# Test through the backend API
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "What is AMD?",
    "include_citations": true
  }'
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  Nginx (8888)   │  ← Reverse Proxy
              └────────┬────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
┌────────────────┐         ┌─────────────────┐
│ Frontend (3000)│         │ Backend (8000)  │
└────────────────┘         └────────┬────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
            ┌───────────┐   ┌──────────┐   ┌──────────────┐
            │ LLM (8080)│   │PostgreSQL│   │  ChromaDB    │
            │  Phi-2    │   │  (5432)  │   │   (8001)     │
            └───────────┘   └──────────┘   └──────────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │ Redis (6379) │
                            └──────────────┘
```

## Troubleshooting

### LLM Service Won't Start

```bash
# Check LLM logs
docker-compose -f docker-compose.prod.yml logs llm

# Common issues:
# 1. Out of memory - reduce batch size or use smaller model
# 2. GPU not detected - use CPU version
# 3. Model download failed - check Hugging Face token
```

### Backend Can't Connect to LLM

```bash
# Check if LLM is healthy
curl http://localhost:8080/health

# Check backend logs
docker-compose -f docker-compose.prod.yml logs backend | grep -i llm

# Verify environment variables
docker-compose -f docker-compose.prod.yml exec backend env | grep LLM
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Solutions:
# 1. Reduce Celery worker concurrency in docker-compose.prod.yml
# 2. Use smaller batch sizes in .env
# 3. Add swap space to the server
```

### Slow Response Times

```bash
# Check if using GPU
docker-compose -f docker-compose.prod.yml exec llm nvidia-smi

# If using CPU, expect 5-10 seconds per response
# With GPU, expect 1-2 seconds per response

# Optimize:
# 1. Enable GPU if available
# 2. Reduce MAX_TOKENS in .env
# 3. Use quantized model (4-bit or 8-bit)
```

### Database Connection Errors

```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml ps postgres

# Restart PostgreSQL
docker-compose -f docker-compose.prod.yml restart postgres

# Check database logs
docker-compose -f docker-compose.prod.yml logs postgres
```

## Maintenance

### Viewing Logs

```bash
# All logs
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f [service_name]

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Restarting Services

```bash
# Restart all services
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend
docker-compose -f docker-compose.prod.yml restart llm
```

### Updating the Application

```bash
cd ~/ai-vision-chatbot

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Run database migrations if needed
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Backup Data

```bash
# Backup PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres visiondb > backup_$(date +%Y%m%d).sql

# Backup ChromaDB
tar -czf chromadb_backup_$(date +%Y%m%d).tar.gz data/chromadb/

# Backup uploaded files
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz data/uploads/
```

### Stopping the Application

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose -f docker-compose.prod.yml down -v
```

## Performance Optimization

### For GPU Servers

1. Ensure NVIDIA drivers and Docker GPU support are installed
2. Use `LOCAL_LLM_DEVICE=cuda` in .env
3. Monitor GPU usage: `watch -n 1 nvidia-smi`

### For CPU-Only Servers

1. Use quantized models (4-bit or 8-bit)
2. Reduce `MAX_TOKENS` and `RETRIEVAL_K` in .env
3. Increase `CELERY_TASK_TIME_LIMIT` for longer processing

### Memory Optimization

```bash
# In .env, adjust:
EMBEDDING_BATCH_SIZE=32  # Reduce from 64
DATABASE_POOL_SIZE=10    # Reduce from 20
CELERY_WORKER_CONCURRENCY=2  # In docker-compose.prod.yml
```

## Security Considerations

1. **Change default passwords** in .env
2. **Use strong JWT secrets**
3. **Enable HTTPS** with SSL certificates (configure nginx)
4. **Restrict database access** to localhost only
5. **Set up firewall rules** to limit exposed ports
6. **Regular security updates**: `apt update && apt upgrade`

## Support

For issues or questions:
- GitHub Issues: https://github.com/JyothiSwaroopReddy07/AI-Vision-Chatbot/issues
- Check logs: `docker-compose -f docker-compose.prod.yml logs -f`
- Server status: `docker-compose -f docker-compose.prod.yml ps`

## Alternative LLM Models

If Phi-2 doesn't work well, try these alternatives:

### Smaller Models (faster, less accurate)
- `TinyLlama/TinyLlama-1.1B-Chat-v1.0` (1.1B params)
- `stabilityai/stablelm-2-1_6b` (1.6B params)

### Larger Models (slower, more accurate)
- `mistralai/Mistral-7B-Instruct-v0.2` (7B params, needs 16GB+ VRAM)
- `meta-llama/Llama-2-7b-chat-hf` (7B params, needs 16GB+ VRAM)

To change model, update in .env:
```
LOCAL_LLM_MODEL=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

And restart:
```bash
docker-compose -f docker-compose.prod.yml restart llm backend
```

