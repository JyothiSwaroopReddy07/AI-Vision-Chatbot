#!/bin/bash
# Quick Deployment Script for AI-Vision-Chatbot
# This script assumes you're already on the server and have cloned the repo

set -e

echo "=========================================="
echo "AI-Vision-Chatbot Quick Deployment"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "Error: docker-compose.prod.yml not found!"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    echo ""
    echo "Please create a .env file first:"
    echo "  cp deploy/env.production.example .env"
    echo "  nano .env"
    echo ""
    echo "Make sure to set:"
    echo "  - SECRET_KEY"
    echo "  - JWT_SECRET_KEY"
    echo "  - HUGGINGFACE_TOKEN"
    echo "  - LLM_PROVIDER=local"
    exit 1
fi

# Check Docker
echo "[1/8] Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "Docker not found! Please install Docker first."
    exit 1
fi
echo "✓ Docker found: $(docker --version)"

# Check Docker Compose
echo "[2/8] Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose not found! Please install Docker Compose first."
    exit 1
fi
echo "✓ Docker Compose found: $(docker-compose --version)"

# Create data directories
echo "[3/8] Creating data directories..."
mkdir -p data/chromadb
mkdir -p data/msigdb
mkdir -p data/pubmed_pdfs
mkdir -p data/processed
mkdir -p data/logs
mkdir -p data/uploads
echo "✓ Data directories created"

# Check GPU
echo "[4/8] Checking for GPU..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ GPU detected:"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    GPU_AVAILABLE=true
else
    echo "⚠ No GPU detected - will use CPU (slower inference)"
    GPU_AVAILABLE=false
fi

# Pull/Build images
echo "[5/8] Building Docker images (this may take 10-15 minutes)..."
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services
echo "[6/8] Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
echo "[7/8] Waiting for services to be ready..."
echo "This may take 10-15 minutes for the LLM model to download..."

# Wait for postgres
echo -n "Waiting for PostgreSQL..."
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres &> /dev/null; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
done

# Wait for redis
echo -n "Waiting for Redis..."
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping &> /dev/null; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
done

# Wait for LLM (this takes the longest)
echo "Waiting for LLM service (downloading model, ~5GB)..."
echo "You can monitor progress with: docker-compose -f docker-compose.prod.yml logs -f llm"
sleep 30  # Give it some time to start downloading

# Run database migrations
echo "[8/8] Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head || echo "⚠ Migration failed - may need to run manually"

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Services Status:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "Access Points:"
echo "  Frontend:        http://eye.som.uci.edu:3000"
echo "  Backend API:     http://eye.som.uci.edu:8000"
echo "  API Docs:        http://eye.som.uci.edu:8000/docs"
echo "  Nginx Proxy:     http://eye.som.uci.edu:8888"
echo "  Grafana:         http://eye.som.uci.edu:3001 (admin/admin)"
echo "  Prometheus:      http://eye.som.uci.edu:9090"
echo ""
echo "Useful Commands:"
echo "  View logs:       docker-compose -f docker-compose.prod.yml logs -f"
echo "  View LLM logs:   docker-compose -f docker-compose.prod.yml logs -f llm"
echo "  Restart:         docker-compose -f docker-compose.prod.yml restart"
echo "  Stop:            docker-compose -f docker-compose.prod.yml down"
echo ""
echo "Note: The LLM may still be downloading. Check logs with:"
echo "  docker-compose -f docker-compose.prod.yml logs -f llm"
echo ""
echo "Wait for 'Model loaded successfully' message before using the application."
echo ""

