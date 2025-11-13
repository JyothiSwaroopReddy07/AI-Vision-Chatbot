#!/bin/bash
# Deployment script that uses existing .env file
# Run this if you already have a .env file configured

set -e

echo "=========================================="
echo "AI-Vision-Chatbot Deployment"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo ""
    echo "Please create a .env file first:"
    echo "  1. Copy the example: cp deploy/env.production.example .env"
    echo "  2. Edit it: nano .env"
    echo "  3. Set required values:"
    echo "     - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "     - JWT_SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "     - HUGGINGFACE_TOKEN (from https://huggingface.co/settings/tokens)"
    echo ""
    exit 1
fi

# Verify required variables are set
echo "[1/8] Checking .env configuration..."
source .env

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "your-super-secret-key-change-this-in-production" ]; then
    echo "❌ Error: SECRET_KEY not set in .env"
    echo "Generate one with: openssl rand -hex 32"
    exit 1
fi

if [ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "your-jwt-secret-key-change-this" ]; then
    echo "❌ Error: JWT_SECRET_KEY not set in .env"
    echo "Generate one with: openssl rand -hex 32"
    exit 1
fi

if [ -z "$HUGGINGFACE_TOKEN" ] || [ "$HUGGINGFACE_TOKEN" = "your_huggingface_token_here" ]; then
    echo "❌ Error: HUGGINGFACE_TOKEN not set in .env"
    echo "Get one from: https://huggingface.co/settings/tokens"
    exit 1
fi

echo "✓ .env configuration looks good"

# Check Docker
echo ""
echo "[2/8] Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✓ Docker installed"
    echo ""
    echo "⚠️  IMPORTANT: Log out and log back in, then run this script again."
    exit 0
else
    echo "✓ Docker found: $(docker --version)"
fi

# Check Docker Compose
echo ""
echo "[3/8] Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✓ Docker Compose installed"
else
    echo "✓ Docker Compose found: $(docker-compose --version)"
fi

# Create directories
echo ""
echo "[4/8] Creating data directories..."
mkdir -p data/chromadb
mkdir -p data/msigdb
mkdir -p data/pubmed_pdfs
mkdir -p data/processed
mkdir -p data/logs
mkdir -p data/uploads
echo "✓ Directories created"

# Check GPU
echo ""
echo "[5/8] Checking for GPU..."
if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null; then
        echo "✓ GPU detected and working"
    else
        echo "⚠️  GPU detected but driver not working - will use CPU (slower)"
    fi
else
    echo "⚠️  No GPU detected - will use CPU (slower)"
fi

# Stop existing containers
echo ""
echo "[6/8] Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
echo "✓ Cleaned up"

# Build and start
echo ""
echo "[7/8] Building and starting services..."
echo "⏳ This will take 10-15 minutes to download the LLM model (~5GB)"
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for services
echo ""
echo "[8/8] Waiting for services..."
sleep 10

echo "Waiting for PostgreSQL..."
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres &> /dev/null 2>&1; then
        echo "✓ PostgreSQL ready"
        break
    fi
    sleep 2
done

echo "Waiting for Redis..."
for i in {1..30}; do
    if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping &> /dev/null 2>&1; then
        echo "✓ Redis ready"
        break
    fi
    sleep 2
done

# Run migrations
echo ""
echo "Running database migrations..."
sleep 5
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head 2>/dev/null || echo "⚠️  Run migrations manually: docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head"

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "🎉 Services are starting up!"
echo ""
echo "⏳ LLM model is downloading in the background (10-15 min)"
echo "   Monitor: docker-compose -f docker-compose.prod.yml logs -f llm"
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

