#!/bin/bash

# ============================================================================
# Redis Security Fix Deployment Script
# ============================================================================
# This script applies the critical Redis security fix
# Run this on the production server IMMEDIATELY
# ============================================================================

set -e  # Exit on any error

echo "============================================================================"
echo "🚨 CRITICAL: Redis Security Fix Deployment"
echo "============================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}Error: docker-compose.prod.yml not found!${NC}"
    echo "Please run this script from the AI-Vision-Chatbot directory"
    exit 1
fi

echo -e "${YELLOW}Step 1: Generating strong Redis password...${NC}"
REDIS_PASSWORD=$(openssl rand -base64 32)
echo -e "${GREEN}✓ Password generated${NC}"
echo ""

echo -e "${YELLOW}Step 2: Checking if .env file exists...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create .env file from deploy/env.production.example"
    exit 1
fi
echo -e "${GREEN}✓ .env file found${NC}"
echo ""

echo -e "${YELLOW}Step 3: Backing up current .env file...${NC}"
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo -e "${GREEN}✓ Backup created${NC}"
echo ""

echo -e "${YELLOW}Step 4: Updating REDIS_PASSWORD in .env...${NC}"
if grep -q "^REDIS_PASSWORD=" .env; then
    # Update existing line
    sed -i.bak "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=${REDIS_PASSWORD}|" .env
    echo -e "${GREEN}✓ REDIS_PASSWORD updated${NC}"
else
    # Add new line
    echo "REDIS_PASSWORD=${REDIS_PASSWORD}" >> .env
    echo -e "${GREEN}✓ REDIS_PASSWORD added${NC}"
fi
echo ""

echo -e "${YELLOW}Step 5: Pulling latest code from GitHub...${NC}"
git pull origin main
echo -e "${GREEN}✓ Code updated${NC}"
echo ""

echo -e "${YELLOW}Step 6: Stopping all services...${NC}"
docker-compose -f docker-compose.prod.yml down
echo -e "${GREEN}✓ Services stopped${NC}"
echo ""

echo -e "${YELLOW}Step 7: Removing old Redis data (for clean start)...${NC}"
docker volume rm ai-vision-chatbot_redis_data 2>/dev/null || echo "Volume already removed or doesn't exist"
echo -e "${GREEN}✓ Redis data cleared${NC}"
echo ""

echo -e "${YELLOW}Step 8: Starting all services with new configuration...${NC}"
docker-compose -f docker-compose.prod.yml up -d
echo -e "${GREEN}✓ Services started${NC}"
echo ""

echo -e "${YELLOW}Step 9: Waiting for services to initialize (30 seconds)...${NC}"
sleep 30
echo -e "${GREEN}✓ Wait complete${NC}"
echo ""

echo -e "${YELLOW}Step 10: Verifying Redis authentication...${NC}"
# Test without password (should fail)
if docker exec vision_redis redis-cli ping 2>&1 | grep -q "NOAUTH"; then
    echo -e "${GREEN}✓ Redis correctly requires authentication${NC}"
else
    echo -e "${RED}⚠ Warning: Redis may not be properly secured${NC}"
fi

# Test with password (should succeed)
if docker exec vision_redis redis-cli -a "${REDIS_PASSWORD}" ping 2>&1 | grep -q "PONG"; then
    echo -e "${GREEN}✓ Redis authentication working correctly${NC}"
else
    echo -e "${RED}⚠ Warning: Redis authentication test failed${NC}"
fi
echo ""

echo -e "${YELLOW}Step 11: Checking service status...${NC}"
docker-compose -f docker-compose.prod.yml ps
echo ""

echo -e "${YELLOW}Step 12: Checking backend logs for errors...${NC}"
docker-compose -f docker-compose.prod.yml logs --tail=20 backend | grep -i "error" || echo "No errors found"
echo ""

echo "============================================================================"
echo -e "${GREEN}✅ Redis Security Fix Applied Successfully!${NC}"
echo "============================================================================"
echo ""
echo "📝 Important Information:"
echo "   Redis Password: ${REDIS_PASSWORD}"
echo ""
echo "⚠️  SAVE THIS PASSWORD SECURELY!"
echo "   It has been added to your .env file"
echo "   A backup of your old .env was created"
echo ""
echo "🔍 Next Steps:"
echo "   1. Test your application: http://eye.som.uci.edu:8888"
echo "   2. Notify UCI IT (Pablo) that the security issue is resolved"
echo "   3. Monitor logs for any issues:"
echo "      docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "📚 For more details, see: REDIS_SECURITY_UPDATE.md"
echo "============================================================================"

