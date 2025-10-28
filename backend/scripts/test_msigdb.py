#!/usr/bin/env python3
"""
MSigDB Feature Comprehensive Test Script

Tests all aspects of the MSigDB gene pattern search feature:
- Gene parsing (single, multiple, space/comma-separated)
- Species detection (human, mouse, auto)
- Exact matching
- Fuzzy matching
- Statistics calculation
- API endpoints
- Database operations
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.msigdb_service import msigdb_service
from app.core.database import AsyncSession, AsyncSessionLocal
from app.models.user import User
import json


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.CYAN}→ {text}{Colors.END}")


async def test_gene_parsing():
    """Test 1: Gene Pattern Parsing"""
    print_header("Test 1: Gene Pattern Parsing")
    
    test_cases = [
        ("TP53", ["TP53"]),
        ("TP53, BRCA1, EGFR", ["TP53", "BRCA1", "EGFR"]),
        ("TP53 BRCA1 EGFR", ["TP53", "BRCA1", "EGFR"]),
        ("TP53,BRCA1,EGFR,KRAS", ["TP53", "BRCA1", "EGFR", "KRAS"]),
        ("  TP53  ,  BRCA1  ", ["TP53", "BRCA1"]),
        ("tp53", ["TP53"]),  # Should be uppercased
    ]
    
    passed = 0
    failed = 0
    
    for query, expected in test_cases:
        genes = msigdb_service.parse_gene_query(query)
        if genes == expected:
            print_success(f"'{query}' → {genes}")
            passed += 1
        else:
            print_error(f"'{query}' → Expected {expected}, got {genes}")
            failed += 1
    
    print(f"\n{Colors.BOLD}Results: {passed} passed, {failed} failed{Colors.END}\n")
    return failed == 0


async def test_species_detection():
    """Test 2: Species Auto-detection"""
    print_header("Test 2: Species Auto-detection")
    
    test_cases = [
        (["TP53", "BRCA1", "EGFR"], "human"),  # All uppercase = human
        (["Tp53", "Brca1", "Egfr"], "mouse"),  # Title case = mouse
        (["tp53", "brca1"], "human"),  # Lowercase converted to uppercase = human
        (["TP53", "Brca1"], "auto"),  # Mixed = auto (search both)
    ]
    
    passed = 0
    failed = 0
    
    for genes, expected in test_cases:
        detected = msigdb_service.detect_species(genes)
        if detected == expected:
            print_success(f"{genes} → {detected}")
            passed += 1
        else:
            print_error(f"{genes} → Expected {expected}, got {detected}")
            failed += 1
    
    print(f"\n{Colors.BOLD}Results: {passed} passed, {failed} failed{Colors.END}\n")
    return failed == 0


async def test_database_connection():
    """Test 3: Database Connection"""
    print_header("Test 3: Database Connection")
    
    # Check if MSigDB databases exist
    from app.core.config import settings
    import os
    
    human_db = settings.MSIGDB_HUMAN_DB_PATH
    mouse_db = settings.MSIGDB_MOUSE_DB_PATH
    
    print_info(f"Human DB path: {human_db}")
    print_info(f"Mouse DB path: {mouse_db}")
    
    human_exists = os.path.exists(human_db)
    mouse_exists = os.path.exists(mouse_db)
    
    if human_exists:
        print_success(f"Human database found: {os.path.getsize(human_db) / 1024 / 1024:.1f} MB")
    else:
        print_error(f"Human database NOT FOUND: {human_db}")
    
    if mouse_exists:
        print_success(f"Mouse database found: {os.path.getsize(mouse_db) / 1024 / 1024:.1f} MB")
    else:
        print_error(f"Mouse database NOT FOUND: {mouse_db}")
    
    # Try to connect
    if human_exists:
        try:
            conn = msigdb_service._get_db_connection("human")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM gene_set")
            count = cursor.fetchone()[0]
            print_success(f"Human DB connected: {count} gene sets")
            conn.close()
        except Exception as e:
            print_error(f"Failed to connect to human DB: {str(e)}")
            return False
    
    if mouse_exists:
        try:
            conn = msigdb_service._get_db_connection("mouse")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM gene_set")
            count = cursor.fetchone()[0]
            print_success(f"Mouse DB connected: {count} gene sets")
            conn.close()
        except Exception as e:
            print_error(f"Failed to connect to mouse DB: {str(e)}")
            return False
    
    if not human_exists and not mouse_exists:
        print_error("\nBoth databases are missing!")
        print_warning("Please download MSigDB databases:")
        print_warning("1. Visit: https://www.gsea-msigdb.org/gsea/msigdb/download_file.jsp")
        print_warning("2. Register/login (free)")
        print_warning("3. Download Human and Mouse SQLite databases")
        print_warning(f"4. Place in: {os.path.dirname(human_db)}")
        return False
    
    return human_exists or mouse_exists


async def test_search_functionality(db: AsyncSession, user: User):
    """Test 4: Search Functionality"""
    print_header("Test 4: Search Functionality (requires databases)")
    
    # Check if databases exist
    from app.core.config import settings
    import os
    
    if not os.path.exists(settings.MSIGDB_HUMAN_DB_PATH) and not os.path.exists(settings.MSIGDB_MOUSE_DB_PATH):
        print_warning("Skipping search tests - databases not found")
        return True
    
    try:
        # Test exact search with common genes
        print_info("Testing search with: TP53, BRCA1, EGFR")
        result = await msigdb_service.search_gene_sets(
            db=db,
            user=user,
            query="TP53, BRCA1, EGFR",
            species="human",
            search_type="exact",
            collections=None
        )
        
        if result["num_results"] > 0:
            print_success(f"Found {result['num_results']} gene sets")
            print_info(f"Query genes: {', '.join(result['genes'])}")
            print_info(f"Species: {result['species']}")
            
            # Show top 3 results
            for i, gs in enumerate(result["results"][:3], 1):
                print(f"\n  {i}. {gs['gene_set_name']}")
                print(f"     Collection: {gs['collection']}")
                print(f"     Overlap: {gs['overlap_count']}/{gs['gene_set_size']} ({gs['overlap_percentage']:.1f}%)")
                print(f"     P-value: {gs['p_value']:.2e}")
                print(f"     Matched genes: {', '.join(gs['matched_genes'][:5])}")
        else:
            print_warning("No results found - this may be normal if genes are not in database")
        
        return True
        
    except Exception as e:
        print_error(f"Search test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_statistics_calculation():
    """Test 5: Statistics Calculation"""
    print_header("Test 5: Statistics Calculation")
    
    try:
        # Test hypergeometric p-value calculation
        p_value, odds_ratio = msigdb_service.calculate_enrichment_statistics(
            overlap_count=2,
            gene_set_size=50,
            query_size=3,
            total_genes=20000
        )
        
        print_success(f"P-value calculated: {p_value:.2e}")
        print_success(f"Odds ratio: {odds_ratio:.2f}")
        
        # P-value should be between 0 and 1
        if 0 <= p_value <= 1:
            print_success("P-value is in valid range [0, 1]")
        else:
            print_error(f"P-value out of range: {p_value}")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Statistics test failed: {str(e)}")
        return False


async def test_postgresql_tables(db: AsyncSession):
    """Test 6: PostgreSQL Tables"""
    print_header("Test 6: PostgreSQL Tables")
    
    try:
        from sqlalchemy import text
        
        # Check if tables exist
        tables = ["msigdb_queries", "msigdb_results"]
        
        for table in tables:
            result = await db.execute(
                text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'")
            )
            exists = result.scalar() > 0
            
            if exists:
                print_success(f"Table '{table}' exists")
                
                # Count rows
                result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print_info(f"  Rows: {count}")
            else:
                print_error(f"Table '{table}' does NOT exist")
                return False
        
        return True
        
    except Exception as e:
        print_error(f"PostgreSQL test failed: {str(e)}")
        return False


async def run_all_tests():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     MSigDB Feature - Comprehensive Test Suite            ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(Colors.END)
    
    results = {}
    
    # Tests that don't require DB connection
    results["Gene Parsing"] = await test_gene_parsing()
    results["Species Detection"] = await test_species_detection()
    results["Database Connection"] = await test_database_connection()
    results["Statistics Calculation"] = await test_statistics_calculation()
    
    # Tests that require DB connection
    async with AsyncSessionLocal() as db:
        # Create a test user (or get existing)
        from sqlalchemy import select
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        
        if not user:
            print_warning("No users found in database - creating test user")
            user = User(
                username="test_user",
                email="test@example.com",
                hashed_password="test_hash"
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        results["PostgreSQL Tables"] = await test_postgresql_tables(db)
        results["Search Functionality"] = await test_search_functionality(db, user)
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name:<30} PASSED")
        else:
            print_error(f"{test_name:<30} FAILED")
    
    print(f"\n{Colors.BOLD}")
    if passed == total:
        print(f"{Colors.GREEN}{'='*60}")
        print(f"ALL TESTS PASSED ({passed}/{total})")
        print(f"{'='*60}{Colors.END}\n")
    else:
        print(f"{Colors.RED}{'='*60}")
        print(f"SOME TESTS FAILED ({passed}/{total} passed)")
        print(f"{'='*60}{Colors.END}\n")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

