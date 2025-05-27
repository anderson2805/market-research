#!/usr/bin/env python3
"""
Test script for the related companies functionality
Run this from the project root directory
"""

import asyncio
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from services.related_companies import find_companies

async def test_company_search():
    """Test the sequential company search functionality"""
    print("Testing sequential company search...")
    print("=" * 50)
    
    try:
        # Test with a smaller number of searches for testing
        results = await find_companies(
            region="Silicon Valley",
            country="USA",
            num_searches=3
        )
        
        print(f"Search completed successfully!")
        print(f"Total companies found: {results['total_found']}")
        print(f"Successful searches: {results['successful_searches']}/{results['total_searches']}")
        print(f"Summary: {results['summary']}")
        print("\nQueries used:")
        for i, query in enumerate(results['search_queries_used'], 1):
            print(f"{i}. {query}")
        
        print(f"\nFirst 10 companies found:")
        for i, company in enumerate(results['companies'][:10], 1):
            print(f"{i}. {company.get('name', 'Unknown')}")
            if company.get('industry'):
                print(f"   Industry: {company['industry']}")
            if company.get('description'):
                print(f"   Description: {company['description'][:100]}...")
            print()
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting related companies test...")
    asyncio.run(test_company_search()) 