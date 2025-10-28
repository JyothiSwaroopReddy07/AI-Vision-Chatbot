#!/bin/bash

# MSigDB Database Download Script
# Downloads Human and Mouse MSigDB SQLite databases from Broad Institute

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
MSIGDB_DIR="$PROJECT_ROOT/data/msigdb"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MSigDB Database Download Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Create directory if it doesn't exist
mkdir -p "$MSIGDB_DIR"

# MSigDB version
VERSION="2024.1"

# Database URLs
HUMAN_DB_URL="https://data.broadinstitute.org/gsea-msigdb/msigdb/release/${VERSION}.Hs/msigdb_v${VERSION}.Hs.db"
MOUSE_DB_URL="https://data.broadinstitute.org/gsea-msigdb/msigdb/release/${VERSION}.Mm/msigdb_v${VERSION}.Mm.db"

HUMAN_DB_FILE="$MSIGDB_DIR/msigdb_v${VERSION}.Hs.db"
MOUSE_DB_FILE="$MSIGDB_DIR/msigdb_v${VERSION}.Mm.db"

# Function to download database
download_db() {
    local url=$1
    local output_file=$2
    local species=$3
    
    echo -e "${YELLOW}Downloading ${species} MSigDB database...${NC}"
    echo "URL: $url"
    echo "Output: $output_file"
    echo ""
    
    if [ -f "$output_file" ]; then
        echo -e "${YELLOW}File already exists: $output_file${NC}"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Skipping ${species} database download.${NC}"
            echo ""
            return
        fi
        rm "$output_file"
    fi
    
    # Try downloading with curl
    if command -v curl &> /dev/null; then
        if curl -L -f -o "$output_file" "$url"; then
            echo -e "${GREEN}✓ Successfully downloaded ${species} database!${NC}"
            echo -e "Size: $(du -h "$output_file" | cut -f1)"
            echo ""
        else
            echo -e "${RED}✗ Failed to download ${species} database with curl${NC}"
            echo -e "${YELLOW}Please download manually from: https://www.gsea-msigdb.org/gsea/msigdb/download_file.jsp${NC}"
            echo ""
        fi
    elif command -v wget &> /dev/null; then
        if wget -O "$output_file" "$url"; then
            echo -e "${GREEN}✓ Successfully downloaded ${species} database!${NC}"
            echo -e "Size: $(du -h "$output_file" | cut -f1)"
            echo ""
        else
            echo -e "${RED}✗ Failed to download ${species} database with wget${NC}"
            echo -e "${YELLOW}Please download manually from: https://www.gsea-msigdb.org/gsea/msigdb/download_file.jsp${NC}"
            echo ""
        fi
    else
        echo -e "${RED}✗ Neither curl nor wget is available${NC}"
        echo -e "${YELLOW}Please install curl or wget, or download manually from:${NC}"
        echo -e "https://www.gsea-msigdb.org/gsea/msigdb/download_file.jsp"
        echo ""
        exit 1
    fi
}

# Download Human database
download_db "$HUMAN_DB_URL" "$HUMAN_DB_FILE" "Human"

# Download Mouse database
download_db "$MOUSE_DB_URL" "$MOUSE_DB_FILE" "Mouse"

# Verify files
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Verification${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

if [ -f "$HUMAN_DB_FILE" ] && [ -s "$HUMAN_DB_FILE" ]; then
    echo -e "${GREEN}✓ Human database: OK${NC}"
    echo "  Path: $HUMAN_DB_FILE"
    echo "  Size: $(du -h "$HUMAN_DB_FILE" | cut -f1)"
    
    # Try to verify it's a valid SQLite database
    if command -v sqlite3 &> /dev/null; then
        if sqlite3 "$HUMAN_DB_FILE" "SELECT COUNT(*) FROM sqlite_master;" &> /dev/null; then
            echo -e "${GREEN}  Valid SQLite database: YES${NC}"
        else
            echo -e "${RED}  Valid SQLite database: NO${NC}"
        fi
    fi
else
    echo -e "${RED}✗ Human database: MISSING or EMPTY${NC}"
fi

echo ""

if [ -f "$MOUSE_DB_FILE" ] && [ -s "$MOUSE_DB_FILE" ]; then
    echo -e "${GREEN}✓ Mouse database: OK${NC}"
    echo "  Path: $MOUSE_DB_FILE"
    echo "  Size: $(du -h "$MOUSE_DB_FILE" | cut -f1)"
    
    # Try to verify it's a valid SQLite database
    if command -v sqlite3 &> /dev/null; then
        if sqlite3 "$MOUSE_DB_FILE" "SELECT COUNT(*) FROM sqlite_master;" &> /dev/null; then
            echo -e "${GREEN}  Valid SQLite database: YES${NC}"
        else
            echo -e "${RED}  Valid SQLite database: NO${NC}"
        fi
    fi
else
    echo -e "${RED}✗ Mouse database: MISSING or EMPTY${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Next Steps${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "1. Run database migration:"
echo "   cd backend && python3 -m alembic upgrade head"
echo ""
echo "2. Restart backend:"
echo "   docker-compose restart backend"
echo ""
echo "3. Test MSigDB feature:"
echo "   Open http://localhost:3000 and search for: TP53, BRCA1, EGFR"
echo ""
echo -e "${GREEN}Done!${NC}"

