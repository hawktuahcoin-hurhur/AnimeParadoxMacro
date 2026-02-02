"""Test OCR search for Act 1, Act 2, Act 3 in act1.png"""
import sys
from PIL import Image
from ocr_utils import run_ocr_on_image, fuzzy_match, find_text_multi_strategy
import numpy as np

def test_act_search():
    """Test if we can find Act 1, Act 2, Act 3 in act1.png"""
    print("=" * 60)
    print("Testing OCR search for Acts in act1.png")
    print("=" * 60)
    
    # Load the test image
    try:
        image_path = "testimages/act1.png"
        image = Image.open(image_path)
        print(f"\n✓ Loaded image: {image_path}")
        print(f"  Image size: {image.size}")
    except Exception as e:
        print(f"✗ Failed to load image: {e}")
        return
    
    # Run OCR to get all text
    print("\n" + "=" * 60)
    print("Running OCR on image...")
    print("=" * 60)
    
    img_array = np.array(image)
    results = run_ocr_on_image(img_array, confidence_threshold=0.5)
    
    print(f"\n✓ OCR found {len(results)} text items:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. '{result['text']}' (confidence: {result['confidence']:.2f}, pos: {result['x']},{result['y']}, engine: {result['engine']})")
    
    # Test searching for Act 1, Act 2, Act 3
    search_terms = ["Act 1", "Act 2", "Act 3"]
    
    print("\n" + "=" * 60)
    print("Testing fuzzy matching for each Act...")
    print("=" * 60)
    
    for search_term in search_terms:
        print(f"\n🔍 Searching for: '{search_term}'")
        print("-" * 40)
        
        best_match = None
        best_score = 0
        
        for result in results:
            is_match, score = fuzzy_match(search_term, result['text'])
            print(f"  '{result['text']}' -> Score: {score}, Match: {is_match}")
            
            if score > best_score:
                best_score = score
                best_match = result
        
        if best_match:
            print(f"\n✓ BEST MATCH for '{search_term}':")
            print(f"  Text: '{best_match['text']}'")
            print(f"  Score: {best_score}")
            print(f"  Position: ({best_match['x']}, {best_match['y']})")
            print(f"  Confidence: {best_match['confidence']:.2f}")
            print(f"  Engine: {best_match['engine']}")
        else:
            print(f"\n✗ No match found for '{search_term}'")
    
    # Test multi-strategy search
    print("\n" + "=" * 60)
    print("Testing multi-strategy search...")
    print("=" * 60)
    
    for search_term in search_terms:
        print(f"\n🔍 Multi-strategy search for: '{search_term}'")
        print("-" * 40)
        
        match = find_text_multi_strategy(search_term, image, confidence_threshold=0.5)
        
        if match:
            print(f"✓ FOUND:")
            print(f"  Text: '{match['text']}'")
            print(f"  Fuzzy Score: {match['fuzzy_score']}")
            print(f"  OCR Confidence: {match['confidence']:.2f}")
            print(f"  Position: ({match['x']}, {match['y']})")
            print(f"  Strategy: {match['strategy']}")
        else:
            print(f"✗ NOT FOUND")

if __name__ == "__main__":
    test_act_search()
