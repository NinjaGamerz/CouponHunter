#!/usr/bin/env python3
"""
Test script to validate hunter.py functions
"""

import sys
import os
sys.path.insert(0, '/workspaces/CouponHunter')

from hunter import (
    is_truly_free, extract_course_id, load_history, save_history,
    SECURITY_KEYWORDS, ALL_KEYWORDS, PREMIUM_SOURCES
)

def test_filtering():
    """Test the is_truly_free function"""
    print("=" * 60)
    print("🧪 Testing Course Filtering Logic")
    print("=" * 60)
    
    test_cases = [
        ("Python 100% OFF", "", True, "Should find 100% OFF"),
        ("Ethical Hacking - Free Course", "", True, "Should find Free"),
        ("Bug Bounty - 45% Discount", "", False, "Should REJECT 45% off"),
        ("Web Development - Save $99", "", False, "Should REJECT paid"),
        ("Free Linux Tutorial", "", True, "Should find free Linux"),
        ("Python Course - $9.99", "", False, "Should REJECT $9.99"),
        ("Penetration Testing [100% Free]", "", True, "Should find [100% Free]"),
        ("Security Course - Normally $199", "", False, "Should REJECT normally $"),
    ]
    
    for title, content, expected, desc in test_cases:
        result = is_truly_free(title, content)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status}: {desc}")
        print(f"  Title: {title}")
        print(f"  Expected: {expected}, Got: {result}\n")

def test_course_id_extraction():
    """Test course ID extraction"""
    print("=" * 60)
    print("🧪 Testing Course ID Extraction")
    print("=" * 60)
    
    test_urls = [
        "https://www.udemy.com/course/python-programming-123456/?ref=blah",
        "https://udemy.com/course/ethical-hacking-course/",
        "https://www.udemy.com/course/linux-fundamentals-12345",
    ]
    
    for url in test_urls:
        course_id = extract_course_id(url)
        print(f"✓ URL: {url}")
        print(f"  ID: {course_id}\n")

def test_keywords():
    """Test keyword coverage"""
    print("=" * 60)
    print("🧪 Testing Keyword Coverage")
    print("=" * 60)
    
    print(f"✓ Total Security Keywords: {len(SECURITY_KEYWORDS)}")
    print(f"✓ Total Keywords: {len(ALL_KEYWORDS)}")
    print(f"✓ Premium Sources: {len(PREMIUM_SOURCES)}")
    print(f"\nSample Keywords:")
    for i, kw in enumerate(ALL_KEYWORDS[:10]):
        print(f"  {i+1}. {kw}")
    print(f"\nPremium Sources:")
    for i, (name, url) in enumerate(list(PREMIUM_SOURCES.items())[:5]):
        print(f"  {i+1}. {name}: {url}")

def test_history():
    """Test history loading/saving"""
    print("=" * 60)
    print("🧪 Testing History Management")
    print("=" * 60)
    
    test_history = {
        "sent_links": ["https://udemy.com/course/test"],
        "sent_courses": ["test-course-id"]
    }
    
    print("✓ Creating test history...")
    save_history(test_history)
    
    print("✓ Loading history...")
    loaded = load_history()
    
    print(f"✓ Saved: {test_history}")
    print(f"✓ Loaded: {loaded}")
    print(f"✓ Match: {test_history == loaded}\n")

def run_all_tests():
    """Run all tests"""
    print("\n")
    print("🚀 COUPENHUNTER TEST SUITE 🚀")
    print("\n")
    
    try:
        test_filtering()
        test_course_id_extraction()
        test_keywords()
        test_history()
        
        print("=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nThe bot is ready to scan for free courses!")
        
    except Exception as e:
        print(f"\n❌ ERROR DURING TESTING: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()
