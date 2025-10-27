#!/bin/bash

echo "PubMed API Keys + Emails Setup"
echo "================================"
echo ""

for i in {1..5}; do
  read -p "API Key #$i: " API_KEY
  read -p "Email #$i: " EMAIL
  export PUBMED_API_KEY_$i="$API_KEY"
  export PUBMED_EMAIL_$i="$EMAIL"
  echo "✓ Set key $i"
  echo ""
done

echo "✓ All 5 key+email pairs configured"
echo ""
echo "Add to .env file to persist:"
echo "PUBMED_API_KEY_1=..."
echo "PUBMED_EMAIL_1=..."
echo "(repeat for 1-5)"
