#!/bin/bash
#
# Production RAG Population Runner
# This script ensures proper environment and runs the RAG populator
#

set -e

echo "============================================================="
echo "  Production RAG Population System"
echo "============================================================="
echo ""

# Force local embeddings (no OpenAI)
export LLM_PROVIDER=local
export OPENAI_API_KEY=""
export EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

echo "✓ Environment configured for local embeddings"
echo "✓ Model: $EMBEDDING_MODEL"
echo ""

# Create data directories
mkdir -p /data/pubmed_pdfs
mkdir -p /data/processed

echo "✓ Data directories created"
echo ""

# Run the populator
echo "🚀 Starting RAG population..."
echo "   This will take 3-6 hours to download 10,000+ articles"
echo "   Progress is saved continuously - safe to interrupt and resume"
echo ""

python /app/scripts/production_rag_populator.py

echo ""
echo "✅ RAG population complete!"

