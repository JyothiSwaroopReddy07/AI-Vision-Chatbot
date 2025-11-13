#!/bin/bash
# Server Setup Script for AI-Vision-Chatbot with Local LLM
# Run this script on the Linux server after SSH login

set -e

echo "=== AI-Vision-Chatbot Server Deployment ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check system resources
echo -e "${GREEN}[1/10] Checking system resources...${NC}"
echo "OS Info:"
uname -a
echo ""
echo "Memory:"
free -h
echo ""
echo "Disk Space:"
df -h /
echo ""
echo "GPU Info:"
nvidia-smi || echo "No GPU detected - will use CPU (slower)"
echo ""

# Check if Docker is installed
echo -e "${GREEN}[2/10] Checking Docker installation...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker not found. Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}Docker installed successfully${NC}"
else
    echo "Docker is already installed: $(docker --version)"
fi

# Check if Docker Compose is installed
echo -e "${GREEN}[3/10] Checking Docker Compose installation...${NC}"
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Docker Compose not found. Installing...${NC}"
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}Docker Compose installed successfully${NC}"
else
    echo "Docker Compose is already installed: $(docker-compose --version)"
fi

# Create deployment directory
echo -e "${GREEN}[4/10] Setting up deployment directory...${NC}"
DEPLOY_DIR="$HOME/ai-vision-chatbot"
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR

# Clone repository
echo -e "${GREEN}[5/10] Cloning repository...${NC}"
if [ -d ".git" ]; then
    echo "Repository already exists. Pulling latest changes..."
    git pull origin main || git pull origin master
else
    echo "Cloning repository..."
    git clone https://github.com/JyothiSwaroopReddy07/AI-Vision-Chatbot.git .
fi

# Create necessary directories
echo -e "${GREEN}[6/10] Creating data directories...${NC}"
mkdir -p data/chromadb
mkdir -p data/msigdb
mkdir -p data/pubmed_pdfs
mkdir -p data/processed
mkdir -p data/logs
mkdir -p data/uploads
mkdir -p llm_models

# Check if .env file exists
echo -e "${GREEN}[7/10] Checking environment configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Please copy your .env file to: $DEPLOY_DIR/.env"
    echo "Then run this script again."
    exit 1
else
    echo ".env file found"
fi

# Download LLM model (we'll use a 2B parameter model)
echo -e "${GREEN}[8/10] Preparing LLM model configuration...${NC}"
echo "LLM model will be downloaded when the container starts"
echo "Using Phi-2 (2.7B parameters) - Microsoft's efficient model"

# Update docker-compose with LLM service
echo -e "${GREEN}[9/10] Updating docker-compose configuration...${NC}"
echo "Docker compose will be updated with LLM service and custom ports"

# Start services
echo -e "${GREEN}[10/10] Starting services...${NC}"
echo "Building and starting Docker containers..."
docker-compose -f docker-compose.prod.yml up -d --build

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Services are starting up. This may take a few minutes..."
echo ""
echo "Check status with: docker-compose -f docker-compose.prod.yml ps"
echo "View logs with: docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "Access the application at:"
echo "  - Frontend: http://eye.som.uci.edu:3000"
echo "  - Backend API: http://eye.som.uci.edu:8000"
echo "  - API Docs: http://eye.som.uci.edu:8000/docs"
echo ""
echo -e "${YELLOW}Note: Initial startup may take 10-15 minutes to download the LLM model${NC}"

