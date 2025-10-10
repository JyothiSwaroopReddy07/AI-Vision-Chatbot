# Deployment Guide - Vision ChatBot Agent

This guide provides step-by-step instructions for deploying the Vision ChatBot Agent on a Linux server.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Docker Deployment](#docker-deployment)
4. [Manual Deployment](#manual-deployment)
5. [Initial Data Setup](#initial-data-setup)
6. [Configuration](#configuration)
7. [Monitoring](#monitoring)
8. [Maintenance](#maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements
- **CPU**: 36-Core (as specified)
- **RAM**: 256GB
- **Storage**: 7TB
- **OS**: Ubuntu Server 22.04 LTS or later

### Software Requirements
- Docker 24.0+
- Docker Compose 2.20+
- Git
- OpenSSL (for SSL certificates)

---

## Server Setup

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 3. Install Additional Tools

```bash
sudo apt install -y git curl wget htop net-tools
```

### 4. Configure Firewall

```bash
# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

---

## Docker Deployment (Recommended)

### 1. Clone Repository

```bash
cd /opt
sudo git clone https://github.com/yourusername/vision-chatbot-agent.git
cd vision-chatbot-agent
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

**Required configurations in `.env`:**

```bash
# Database
DATABASE_URL=postgresql://postgres:STRONG_PASSWORD@postgres:5432/visiondb

# JWT Secret (generate with: openssl rand -hex 32)
SECRET_KEY=your-generated-secret-key-here
JWT_SECRET_KEY=your-generated-jwt-secret-key-here

# OpenAI API (if using OpenAI)
OPENAI_API_KEY=your-openai-api-key-here

# PubMed
PUBMED_EMAIL=your-email@example.com
PUBMED_API_KEY=your-ncbi-api-key-optional

# Domain
ALLOWED_ORIGINS=https://your-domain.com,http://your-domain.com
```

### 3. Create Data Directories

```bash
# Create necessary directories
sudo mkdir -p /data/uploads
sudo mkdir -p /data/pubmed_pdfs
sudo mkdir -p /data/processed
sudo mkdir -p /data/logs
sudo mkdir -p /data/chromadb

# Set permissions
sudo chown -R $USER:$USER /data
```

### 4. Build and Start Services

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 5. Initialize Database

```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Create admin user (optional)
docker-compose exec backend python -c "
from app.core.database import SessionLocal
from app.services.user_service import user_service
import asyncio

async def create_admin():
    db = SessionLocal()
    try:
        user = await user_service.create_user(
            db=db,
            email='admin@example.com',
            username='admin',
            password='change-this-password',
            full_name='Admin User'
        )
        user.role = 'admin'
        db.commit()
        print('Admin user created successfully')
    finally:
        db.close()

asyncio.run(create_admin())
"
```

### 6. Configure SSL (Let's Encrypt)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Stop Nginx temporarily
docker-compose stop nginx

# Generate SSL certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/

# Update Nginx configuration (uncomment HTTPS block in nginx.conf)
nano nginx/nginx.conf

# Restart Nginx
docker-compose start nginx
```

---

## Manual Deployment

### 1. Install Python and Dependencies

```bash
# Install Python 3.10+
sudo apt install -y python3.10 python3.10-venv python3-pip

# Install system dependencies
sudo apt install -y \
    postgresql postgresql-contrib \
    redis-server \
    tesseract-ocr \
    poppler-utils \
    nginx
```

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
nano .env

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Setup Frontend

```bash
cd frontend

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install dependencies
npm install

# Build application
npm run build

# Start frontend
npm start
```

### 4. Setup Celery Workers

```bash
cd backend
source venv/bin/activate

# Start Celery worker
celery -A app.celery_app.celery_app worker --loglevel=info --concurrency=4

# Start Celery beat (in another terminal)
celery -A app.celery_app.celery_app beat --loglevel=info
```

### 5. Configure Nginx

```bash
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf
sudo nginx -t
sudo systemctl restart nginx
```

---

## Initial Data Setup

### 1. Index PubMed Articles

Using API:

```bash
curl -X POST http://localhost:8000/api/v1/pubmed/index \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "search_terms": [
      "age-related macular degeneration",
      "glaucoma genetics",
      "retina genomics",
      "diabetic retinopathy"
    ],
    "max_results": 10000,
    "date_range": "2020-2024"
  }'
```

Using Python script:

```bash
docker-compose exec backend python -c "
from app.services.pubmed_service import pubmed_service
from app.core.database import SessionLocal
import asyncio

async def index_articles():
    db = SessionLocal()
    try:
        result = await pubmed_service.run_indexing_job(
            db=db,
            search_terms=[
                'age-related macular degeneration',
                'glaucoma genetics',
                'retina genomics'
            ],
            max_results=10000,
            date_range='2020-2024'
        )
        print(f'Indexed {result[\"articles_indexed\"]} articles')
    finally:
        db.close()

asyncio.run(index_articles())
"
```

### 2. Check Indexing Status

```bash
curl http://localhost:8000/api/v1/pubmed/stats \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Configuration

### Environment Variables

**Critical settings:**

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |
| `REDIS_URL` | Redis connection | `redis://redis:6379/0` |
| `SECRET_KEY` | Application secret | `openssl rand -hex 32` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `EMBEDDING_MODEL` | Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| `LLM_PROVIDER` | LLM provider | `openai` or `local` |

### Resource Allocation

**Docker resource limits (optional):**

```yaml
# In docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 32G
        reservations:
          cpus: '4'
          memory: 16G
```

---

## Monitoring

### 1. Access Monitoring Dashboards

- **Grafana**: http://your-server:3001 (admin/admin)
- **Prometheus**: http://your-server:9090

### 2. Check Service Health

```bash
# Service status
docker-compose ps

# Service logs
docker-compose logs backend
docker-compose logs frontend
docker-compose logs celery_worker

# Follow logs in real-time
docker-compose logs -f --tail=100 backend
```

### 3. Monitor Resources

```bash
# System resources
htop

# Docker stats
docker stats

# Disk usage
df -h
du -sh /data/*
```

### 4. Database Monitoring

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d visiondb

# Check database size
SELECT pg_size_pretty(pg_database_size('visiondb'));

# Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Maintenance

### Backup

**Database backup:**

```bash
# Backup database
docker-compose exec -T postgres pg_dump -U postgres visiondb > backup_$(date +%Y%m%d).sql

# Restore database
docker-compose exec -T postgres psql -U postgres visiondb < backup_20240101.sql
```

**ChromaDB backup:**

```bash
# Backup ChromaDB data
tar -czf chromadb_backup_$(date +%Y%m%d).tar.gz /data/chromadb

# Restore ChromaDB data
tar -xzf chromadb_backup_20240101.tar.gz -C /data/
```

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart services
docker-compose down
docker-compose build
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head
```

### Log Rotation

```bash
# Configure log rotation
sudo nano /etc/logrotate.d/vision-chatbot

# Add configuration:
/data/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
}
```

---

## Troubleshooting

### Common Issues

**1. Backend won't start**

```bash
# Check logs
docker-compose logs backend

# Common fixes:
# - Verify database connection
# - Check environment variables
# - Ensure migrations are applied
docker-compose exec backend alembic upgrade head
```

**2. ChromaDB connection error**

```bash
# Restart ChromaDB
docker-compose restart chromadb

# Check ChromaDB logs
docker-compose logs chromadb

# Verify ChromaDB is accessible
curl http://localhost:8001/api/v1/heartbeat
```

**3. Out of memory errors**

```bash
# Check memory usage
free -h

# Reduce batch sizes in .env:
EMBEDDING_BATCH_SIZE=32
PUBMED_BATCH_SIZE=50

# Restart services
docker-compose restart backend celery_worker
```

**4. Slow query responses**

```bash
# Check vector store stats
curl http://localhost:8000/api/v1/pubmed/stats \
  -H "Authorization: Bearer YOUR_TOKEN"

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHDB

# Optimize PostgreSQL
docker-compose exec postgres psql -U postgres -d visiondb -c "VACUUM ANALYZE;"
```

**5. Celery tasks not processing**

```bash
# Check Celery worker logs
docker-compose logs celery_worker

# Restart Celery worker
docker-compose restart celery_worker

# Check Redis connection
docker-compose exec redis redis-cli ping
```

### Health Checks

```bash
# Check all services
curl http://localhost:8000/health

# Check database
docker-compose exec postgres pg_isready

# Check Redis
docker-compose exec redis redis-cli ping

# Check ChromaDB
curl http://localhost:8001/api/v1/heartbeat
```

### Performance Tuning

**PostgreSQL:**

```sql
-- In PostgreSQL console
ALTER SYSTEM SET shared_buffers = '16GB';
ALTER SYSTEM SET effective_cache_size = '48GB';
ALTER SYSTEM SET maintenance_work_mem = '2GB';
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET max_connections = 200;

-- Restart PostgreSQL
```

**Redis:**

```bash
# Edit Redis configuration
docker-compose exec redis redis-cli CONFIG SET maxmemory 8gb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

---

## Security Best Practices

1. **Change default passwords** in `.env`
2. **Use strong secrets** (generate with `openssl rand -hex 32`)
3. **Enable firewall** and allow only necessary ports
4. **Set up SSL/TLS** with Let's Encrypt
5. **Regular backups** of database and vector store
6. **Monitor logs** for suspicious activity
7. **Keep system updated** with security patches
8. **Use environment-specific configurations** (dev/staging/prod)

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourusername/vision-chatbot-agent/issues
- Documentation: https://docs.visionchatbot.com
- Email: support@visionchatbot.com

---

**Deployment completed! Your Vision ChatBot Agent is now running.**

Access the application at: http://your-domain.com (or https://your-domain.com with SSL)

