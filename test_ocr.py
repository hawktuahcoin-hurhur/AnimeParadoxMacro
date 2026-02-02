"""Test PaddleOCR on area.png and search for 'Areas' or 'Area'"""
import numpy as np
from PIL import Image
import cv2
from paddleocr import PaddleOCR
from rapidfuzz import fuzz

def preprocess_image(image):
    """Preprocess image for better OCR accuracy"""
    # Convert to numpy array
    img_array = np.array(image)
    
    # Convert to grayscale
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Apply thresholding
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
    
    return Image.fromarray(denoised)

# Load the image
print("Loading area.png...")
image_path = "testimages/area.png"
image = Image.open(image_path)

# Convert to RGB if needed
if image.mode != 'RGB':
    image = image.convert('RGB')

print(f"Image size: {image.size}")
print(f"Image mode: {image.mode}")
print("\n" + "="*80)
print("Testing with ORIGINAL image:")
print("="*80)

# Initialize PaddleOCR (simpler initialization for v2)
print("Initializing PaddleOCR...")
ocr = PaddleOCR(use_angle_cls=True, lang='en')

# Test with original image
img_array = np.array(image)
results = ocr.ocr(img_array, cls=True)

if results and results[0]:
    print(f"\nFound {len(results[0])} text regions:")
    print("-" * 80)
    for i, line in enumerate(results[0], 1):
        bbox, (text, conf) = line
        # Calculate center
        x = int(sum([point[0] for point in bbox]) / 4)
        y = int(sum([point[1] for point in bbox]) / 4)
        print(f"{i}. Text: '{text}'")
        print(f"   Confidence: {conf:.4f} ({conf*100:.2f}%)")
        print(f"   Position: ({x}, {y})")
        print(f"   BBox: {bbox}")
        print()
else:
    print("No text found!")

print("\n" + "="*80)
print("Testing with PREPROCESSED image:")
print("="*80)

# Test with preprocessed image
processed = preprocess_image(image)
img_array_processed = np.array(processed)
results_processed = ocr.ocr(img_array_processed, cls=True)

if results_processed and results_processed[0]:
    print(f"\nFound {len(results_processed[0])} text regions:")
    print("-" * 80)
    for i, line in enumerate(results_processed[0], 1):
        bbox, (text, conf) = line
        # Calculate center
        x = int(sum([point[0] for point in bbox]) / 4)
        y = int(sum([point[1] for point in bbox]) / 4)
        print(f"{i}. Text: '{text}'")
        print(f"   Confidence: {conf:.4f} ({conf*100:.2f}%)")
        print(f"   Position: ({x}, {y})")
        print(f"   BBox: {bbox}")
        print()
else:
    print("No text found!")

print("\n" + "="*80)
print("Summary:")
print("="*80)
print(f"Original image: {len(results[0]) if results and results[0] else 0} detections")
print(f"Preprocessed image: {len(results_processed[0]) if results_processed and results_processed[0] else 0} detections")

# Search for "Areas" or "Area"
print("\n" + "="*80)
print("Searching for 'Areas' or 'Area':")
print("="*80)

target_texts = ["Areas", "Area"]
found_matches = []

# Check both original and preprocessed results
all_results = []
if results and results[0]:
    all_results.extend([("Original", line) for line in results[0]])
if results_processed and results_processed[0]:
    all_results.extend([("Preprocessed", line) for line in results_processed[0]])

for source, line in all_results:
    bbox, (text, conf) = line
    for target in target_texts:
        # Use fuzzy matching with 75% threshold
        score = fuzz.token_sort_ratio(text.lower(), target.lower())
        if score >= 75:
            x = int(sum([point[0] for point in bbox]) / 4)
            y = int(sum([point[1] for point in bbox]) / 4)
            match_info = {
                'source': source,
                'detected': text,
                'target': target,
                'confidence': conf,
                'fuzzy_score': score,
                'position': (x, y),
                'bbox': bbox
            }
            found_matches.append(match_info)
            break

if found_matches:
    print(f"\n✓ Found {len(found_matches)} match(es):")
    for i, match in enumerate(found_matches, 1):
        print(f"\n{i}. Match found!")
        print(f"   Source: {match['source']} image")
        print(f"   Detected: '{match['detected']}' → Target: '{match['target']}'")
        print(f"   OCR Confidence: {match['confidence']:.4f} ({match['confidence']*100:.2f}%)")
        print(f"   Fuzzy Match Score: {match['fuzzy_score']}/100")
        print(f"   Position: {match['position']}")
        print(f"   BBox: {match['bbox']}")
else:
    print("\n✗ No matches found for 'Areas' or 'Area' (fuzzy threshold: 75%)")
    print("\nAll detected text:")
    for source, line in all_results:
        bbox, (text, conf) = line
        print(f"  - '{text}' (conf: {conf:.2f}, source: {source})")

