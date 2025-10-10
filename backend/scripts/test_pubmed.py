#!/usr/bin/env python3
"""
Test script to debug PubMed API connection
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Bio import Entrez
from app.core.config import settings

# Configure Entrez
Entrez.email = settings.PUBMED_EMAIL
print(f"Using email: {Entrez.email}")

if settings.PUBMED_API_KEY:
    Entrez.api_key = settings.PUBMED_API_KEY
    print(f"Using API key: {settings.PUBMED_API_KEY[:10]}...")

# Test simple query
try:
    print("\nTest 1: Simple search for 'glaucoma'")
    handle = Entrez.esearch(
        db="pubmed",
        term="glaucoma",
        retmax=5
    )
    record = Entrez.read(handle)
    handle.close()
    print(f"✓ Found {len(record['IdList'])} results")
    print(f"  PMIDs: {record['IdList']}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test with field qualifier
try:
    print("\nTest 2: Search with field qualifier")
    handle = Entrez.esearch(
        db="pubmed",
        term="glaucoma[Title]",
        retmax=5
    )
    record = Entrez.read(handle)
    handle.close()
    print(f"✓ Found {len(record['IdList'])} results")
    print(f"  PMIDs: {record['IdList']}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test with date range
try:
    print("\nTest 3: Search with date range")
    handle = Entrez.esearch(
        db="pubmed",
        term="glaucoma AND 2020:2024[pdat]",
        retmax=5
    )
    record = Entrez.read(handle)
    handle.close()
    print(f"✓ Found {len(record['IdList'])} results")
    print(f"  PMIDs: {record['IdList']}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ All tests complete!")

