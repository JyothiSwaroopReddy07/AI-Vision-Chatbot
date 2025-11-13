#!/bin/bash
# Automated Deployment Script for AI-Vision-Chatbot
# This script will be run ON THE SERVER after SSH login

set -e

echo "=========================================="
echo "AI-Vision-Chatbot Automated Deployment"
echo "=========================================="
echo ""

# Generate secrets
echo "[1/12] Generating secret keys..."
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
echo "✓ Secret keys generated"

# Prompt for Hugging Face token
echo ""
echo "[2/12] Hugging Face Token Required"
echo "Please enter your Hugging Face token (get from https://huggingface.co/settings/tokens):"
read -p "HUGGINGFACE_TOKEN: " HUGGINGFACE_TOKEN

if [ -z "$HUGGINGFACE_TOKEN" ]; then
    echo "Error: Hugging Face token is required!"
    echo "Get one from: https://huggingface.co/settings/tokens"
    exit 1
fi

# Optional: Prompt for PubMed API key
echo ""
echo "[3/12] PubMed API Key (Optional - press Enter to skip)"
read -p "PUBMED_API_KEY: " PUBMED_API_KEY

# Clone repository
echo ""
echo "[4/12] Cloning repository..."
cd ~
if [ -d "AI-Vision-Chatbot" ]; then
    echo "Repository already exists. Pulling latest changes..."
    cd AI-Vision-Chatbot
    git pull origin main || git pull origin master
else
    git clone https://github.com/JyothiSwaroopReddy07/AI-Vision-Chatbot.git
    cd AI-Vision-Chatbot
fi
echo "✓ Repository ready"

# Create .env file
echo ""
echo "[5/12] Creating .env file..."
cat > .env << EOF
# Auto-generated Environment Configuration
# Generated on: $(date)

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================
APP_NAME=Vision ChatBot Agent
APP_VERSION=1.0.0
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_ORIGINS=http://eye.som.uci.edu:3000,http://eye.som.uci.edu:8888

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/visiondb
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=

# ============================================================================
# CHROMADB CONFIGURATION
# ============================================================================
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_PERSIST_DIR=/data/chromadb

# ============================================================================
# LLM CONFIGURATION - LOCAL MODEL (2B Parameters)
# ============================================================================
LLM_PROVIDER=local
LOCAL_LLM_BASE_URL=http://llm:80
LOCAL_LLM_MODEL=microsoft/phi-2
LOCAL_LLM_DEVICE=cuda
LOCAL_LLM_MAX_LENGTH=4096
LOCAL_LLM_API_KEY=EMPTY

# Hugging Face Token
HUGGINGFACE_TOKEN=$HUGGINGFACE_TOKEN

# OpenAI Configuration (not used, but required by config)
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# ============================================================================
# EMBEDDING CONFIGURATION
# ============================================================================
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=64

# ============================================================================
# RAG CONFIGURATION
# ============================================================================
RETRIEVAL_K=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TEMPERATURE=0.7
MAX_TOKENS=2000
TOP_P=0.9

# ============================================================================
# PUBMED CONFIGURATION
# ============================================================================
PUBMED_API_KEY=$PUBMED_API_KEY
PUBMED_EMAIL=vision.research.ai@uci.edu
PUBMED_MAX_RESULTS=10000
PUBMED_BATCH_SIZE=100

# ============================================================================
# FILE UPLOAD CONFIGURATION
# ============================================================================
UPLOAD_DIR=/data/uploads
MAX_UPLOAD_SIZE=50000000
ALLOWED_EXTENSIONS=pdf,txt,doc,docx,png,jpg,jpeg

# ============================================================================
# STORAGE PATHS
# ============================================================================
PUBMED_PDF_DIR=/data/pubmed_pdfs
PROCESSED_DATA_DIR=/data/processed
LOGS_DIR=/data/logs

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CELERY_TASK_TRACK_STARTED=True
CELERY_TASK_TIME_LIMIT=3600

# ============================================================================
# AUTHENTICATION & JWT
# ============================================================================
JWT_SECRET_KEY=$JWT_SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================================================
# RATE LIMITING
# ============================================================================
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# ============================================================================
# CORS CONFIGURATION
# ============================================================================
CORS_ENABLED=True
CORS_ALLOW_CREDENTIALS=True

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL=INFO
LOG_FORMAT=json

# ============================================================================
# MONITORING
# ============================================================================
PROMETHEUS_ENABLED=True
PROMETHEUS_PORT=9090

# ============================================================================
# OCR CONFIGURATION
# ============================================================================
TESSERACT_PATH=/usr/bin/tesseract
TESSERACT_LANG=eng

# ============================================================================
# PATHWAY ANALYSIS
# ============================================================================
PATHWAY_DATABASES=KEGG,Reactome,GO_BP,GO_MF,GO_CC
PATHWAY_P_VALUE_THRESHOLD=0.05
PATHWAY_FDR_METHOD=fdr_bh

# ============================================================================
# MSIGDB CONFIGURATION
# ============================================================================
MSIGDB_HUMAN_DB_PATH=/data/msigdb/msigdb_v2025.1.Hs.db
MSIGDB_MOUSE_DB_PATH=/data/msigdb/msigdb_v2025.1.Mm.db
MSIGDB_P_VALUE_THRESHOLD=0.05
MSIGDB_FDR_METHOD=fdr_bh
MSIGDB_MIN_GENE_SET_SIZE=5
MSIGDB_MAX_GENE_SET_SIZE=500

# ============================================================================
# EMAIL CONFIGURATION (Optional)
# ============================================================================
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@visionchatbot.com

# ============================================================================
# SENTRY (Optional)
# ============================================================================
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
EOF

echo "✓ .env file created"

# Check Docker
echo ""
echo "[6/12] Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✓ Docker installed"
    echo ""
    echo "⚠️  IMPORTANT: You need to log out and log back in for Docker permissions to take effect."
    echo "After logging back in, run this script again."
    exit 0
else
    echo "✓ Docker found: $(docker --version)"
fi

# Check Docker Compose
echo ""
echo "[7/12] Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found. Installing..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✓ Docker Compose installed"
else
    echo "✓ Docker Compose found: $(docker-compose --version)"
fi

# Create directories
echo ""
echo "[8/12] Creating data directories..."
mkdir -p data/chromadb
mkdir -p data/msigdb
mkdir -p data/pubmed_pdfs
mkdir -p data/processed
mkdir -p data/logs
mkdir -p data/uploads
echo "✓ Directories created"

# Check GPU
echo ""
echo "[9/12] Checking for GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "⚠️  No GPU detected - will use CPU (slower)"
fi

# Stop any existing containers
echo ""
echo "[10/12] Stopping any existing containers..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
echo "✓ Cleaned up old containers"

# Build and start services
echo ""
echo "[11/12] Building and starting services..."
echo "This will take 10-15 minutes to download the LLM model (~5GB)"
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for services
echo ""
echo "[12/12] Waiting for services to be ready..."
echo "Waiting for PostgreSQL..."
sleep 10
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres &> /dev/null; then
        echo "✓ PostgreSQL ready"
        break
    fi
    sleep 2
done

echo "Waiting for Redis..."
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping &> /dev/null; then
        echo "✓ Redis ready"
        break
    fi
    sleep 2
done

# Run migrations
echo ""
echo "Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head || echo "⚠️  Migrations may need to be run manually later"

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "🎉 Your AI-Vision-Chatbot is now deploying!"
echo ""
echo "⏳ The LLM model is still downloading in the background."
echo "   This will take 10-15 minutes. Monitor with:"
echo "   docker-compose -f docker-compose.prod.yml logs -f llm"
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "🌐 Access Points:"
echo "   Frontend:     http://eye.som.uci.edu:3000"
echo "   Backend API:  http://eye.som.uci.edu:8000"
echo "   API Docs:     http://eye.som.uci.edu:8000/docs"
echo "   Grafana:      http://eye.som.uci.edu:3001 (admin/admin)"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:    docker-compose -f docker-compose.prod.yml logs -f"
echo "   View status:  docker-compose -f docker-compose.prod.yml ps"
echo "   Restart:      docker-compose -f docker-compose.prod.yml restart"
echo "   Stop:         docker-compose -f docker-compose.prod.yml down"
echo ""
echo "⚠️  Wait for 'Model loaded successfully' in LLM logs before using!"
echo ""

