"""
Standalone test for fabrication code extractor without pytest dependencies.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.shared.utils.business.fabrication_code_extractor import FabricationCodeExtractor


def test_basic_extraction():
    """Test basic extraction patterns."""
    print("\n=== Testing Basic Extraction ===")
    
    tests = [
        ("A1012M2AX1012", "AX1012"),
        ("E1061M2EX1061", "EX1061"),
        ("A1012-VM2AX1012", "AX1012"),
        ("E1061-LM2EX1061", "EX1061"),
        ("E1061-FM2EX1061", "EX1061"),
        ("ER1011-8M2ERX1011", "ERX1011"),
        ("F1041-5M2FX1041", "FX1041"),
        ("F1041-BM2FX1041", "FX1041"),
        ("E1068-CM4EX1068", "EX1068"),
        ("E1068-AM4EX1068-A", "EX1068-A"),
        ("BX101-1DOCM2BX101", "BX101"),
    ]
    
    passed = 0
    failed = 0
    
    for packaging_code, expected in tests:
        result = FabricationCodeExtractor.extract_fabrication_code(packaging_code)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
            print(f"{status} {packaging_code:25s} → {result:15s} (expected: {expected})")
        else:
            failed += 1
            print(f"{status} {packaging_code:25s} → {result:15s} (expected: {expected}) FAILED!")
    
    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


def test_different_relation_keys():
    """Test different M# relation keys."""
    print("\n=== Testing Different Relation Keys ===")
    
    tests = [
        ("A1012M2AX1012", "AX1012"),
        ("B2034M4BX2034", "BX2034"),
        ("C3045M5CX3045", "CX3045"),
        ("D4056M7DX4056", "DX4056"),
        ("E5067M12EX5067", "EX5067"),
        ("F6078M13FX6078", "FX6078"),
    ]
    
    passed = 0
    failed = 0
    
    for packaging_code, expected in tests:
        result = FabricationCodeExtractor.extract_fabrication_code(packaging_code)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
            print(f"{status} {packaging_code:25s} → {result:15s}")
        else:
            failed += 1
            print(f"{status} {packaging_code:25s} → {result:15s} (expected: {expected}) FAILED!")
    
    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


def test_edge_cases():
    """Test edge cases."""
    print("\n=== Testing Edge Cases ===")
    
    tests = [
        ("NOPATTERN", None, "No M# pattern"),
        ("", None, "Empty string"),
        (None, None, "None value"),
        ("  A1012M2AX1012  ", "AX1012", "With whitespace"),
    ]
    
    passed = 0
    failed = 0
    
    for packaging_code, expected, description in tests:
        result = FabricationCodeExtractor.extract_fabrication_code(packaging_code)
        status = "✓" if result == expected else "✗"
        
        if result == expected:
            passed += 1
            print(f"{status} {str(packaging_code):25s} → {str(result):15s} ({description})")
        else:
            failed += 1
            print(f"{status} {str(packaging_code):25s} → {str(result):15s} (expected: {expected}) - {description} FAILED!")
    
    print(f"\n{passed} passed, {failed} failed")
    return failed == 0


def test_with_details():
    """Test extraction with details."""
    print("\n=== Testing Extraction with Details ===")
    
    code = "A1012-VM2AX1012"
    result = FabricationCodeExtractor.extract_with_details(code)
    
    print(f"Input Code: {code}")
    print(f"Original: {result['original_code']}")
    print(f"Base Code: {result['base_code']}")
    print(f"Relation Key: {result['relation_key']}")
    print(f"Fabrication Code: {result['fabrication_code']}")
    print(f"Success: {result['success']}")
    
    expected_values = {
        'original_code': 'A1012-VM2AX1012',
        'base_code': 'A1012-V',
        'relation_key': 'M2',
        'fabrication_code': 'AX1012',
        'success': True
    }
    
    all_match = all(result[key] == expected_values[key] for key in expected_values)
    
    if all_match:
        print("\n✓ All details match expected values")
        return True
    else:
        print("\n✗ Some details don't match!")
        for key in expected_values:
            if result[key] != expected_values[key]:
                print(f"  {key}: got '{result[key]}', expected '{expected_values[key]}'")
        return False


if __name__ == "__main__":
    print("="*60)
    print("FABRICATION CODE EXTRACTOR - STANDALONE TESTS")
    print("="*60)
    
    all_passed = True
    
    all_passed &= test_basic_extraction()
    all_passed &= test_different_relation_keys()
    all_passed &= test_edge_cases()
    all_passed &= test_with_details()
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("="*60)
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("="*60)
        sys.exit(1)
