"""OCR utilities for screen text recognition"""
import pyautogui
from PIL import Image, ImageGrab, ImageFilter, ImageOps
import cv2
import numpy as np
import time
from rapidfuzz import fuzz, process

# Try to import easyocr
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    # Initialize EasyOCR reader (lazy loading)
    _easyocr_reader = None
except ImportError:
    EASYOCR_AVAILABLE = False
    _easyocr_reader = None

# Try to import paddleocr
try:
    from paddleocr import PaddleOCR
    PADDLEOCR_AVAILABLE = True
    _paddleocr_reader = None
except ImportError:
    PADDLEOCR_AVAILABLE = False
    _paddleocr_reader = None

# Try to import ONNX Runtime with DirectML for Windows GPU acceleration
try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
    # Check if DirectML provider is available (Windows GPU without CUDA)
    available_providers = ort.get_available_providers()
    DIRECTML_AVAILABLE = 'DmlExecutionProvider' in available_providers
except ImportError:
    ONNXRUNTIME_AVAILABLE = False
    DIRECTML_AVAILABLE = False

# Fuzzy matching threshold (0-100, higher = stricter)
# Lowered to 65 for better handling of OCR errors in dynamic game content
FUZZY_MATCH_THRESHOLD = 65

# Configure pytesseract path - update this if tesseract is installed elsewhere
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def get_easyocr_reader():
    """Get or create EasyOCR reader instance (tries GPU first, falls back to CPU)"""
    global _easyocr_reader
    if EASYOCR_AVAILABLE and _easyocr_reader is None:
        try:
            # First try GPU (works if CUDA is available)
            print("Initializing EasyOCR (attempting GPU/CUDA)...")
            _easyocr_reader = easyocr.Reader(['en'], gpu=True, verbose=False)
            print("✓ EasyOCR initialized with GPU (CUDA)")
        except Exception as e:
            # Fall back to CPU if GPU fails (no CUDA or other GPU issues)
            try:
                print(f"⚠ EasyOCR GPU failed ({e}), trying CPU...")
                _easyocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                print("✓ EasyOCR initialized with CPU")
                # If DirectML is available, note it as an option for future enhancement
                if DIRECTML_AVAILABLE:
                    print("ℹ DirectML detected - ONNX Runtime GPU acceleration available for future features")
            except Exception as e2:
                print(f"✗ EasyOCR initialization failed completely: {e2}")
                _easyocr_reader = None
    return _easyocr_reader

def get_paddleocr_reader():
    """Get or create PaddleOCR reader instance (tries GPU/CUDA first, falls back to CPU)"""
    global _paddleocr_reader
    if PADDLEOCR_AVAILABLE and _paddleocr_reader is None:
        try:
            print("Initializing PaddleOCR (attempting GPU/CUDA)...")
            _paddleocr_reader = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True, gpu_mem=500)
            print("✓ PaddleOCR initialized with GPU (CUDA)")
        except Exception as e:
            print(f"⚠ PaddleOCR GPU failed, falling back to CPU: {e}")
            _paddleocr_reader = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
            print("✓ PaddleOCR initialized with CPU")
            # If DirectML is available, note it as an option for future enhancement
            if DIRECTML_AVAILABLE:
                print("ℹ DirectML detected - ONNX Runtime GPU acceleration available for future features")
    return _paddleocr_reader

def capture_screen(region=None):
    """Capture the screen or a specific region"""
    screenshot = ImageGrab.grab(bbox=region)
    return screenshot

def fuzzy_match(text1, text2, threshold=FUZZY_MATCH_THRESHOLD):
    """Check if two strings match using fuzzy matching with multiple strategies.
    More flexible prompt-based matching that looks for similar text.
    Returns: (is_match: bool, score: int)
    """
    text1_lower = text1.lower().strip()
    text2_lower = text2.lower().strip()
    
    # Strategy 1: Exact match (highest priority)
    if text1_lower == text2_lower:
        return (True, 100)
    
    # Strategy 2: One contains the other (substring match)
    if text1_lower in text2_lower or text2_lower in text1_lower:
        # Calculate how much of the shorter string is contained
        shorter = min(len(text1_lower), len(text2_lower))
        longer = max(len(text1_lower), len(text2_lower))
        containment_score = int((shorter / longer) * 100)
        if containment_score >= threshold - 10:  # More lenient for substring matches
            return (True, containment_score)
    
    # Strategy 3: Token sort ratio (handles word order variations)
    token_score = fuzz.token_sort_ratio(text1_lower, text2_lower)
    if token_score >= threshold:
        return (True, token_score)
    
    # Strategy 4: Partial ratio (looks for best matching substring)
    partial_score = fuzz.partial_ratio(text1_lower, text2_lower)
    if partial_score >= threshold:
        return (True, partial_score)
    
    # Strategy 5: Token set ratio (ignores duplicate words, handles extra words)
    token_set_score = fuzz.token_set_ratio(text1_lower, text2_lower)
    if token_set_score >= threshold:
        return (True, token_set_score)
    
    # Return best score even if below threshold
    best_score = max(token_score, partial_score, token_set_score)
    return (best_score >= threshold, best_score)

def preprocess_original(image):
    """Return original image as numpy array (no preprocessing)"""
    return np.array(image)

def preprocess_grayscale(image):
    """Simple grayscale conversion"""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    return img_array

def preprocess_binary_light(image):
    """Binary threshold optimized for light text on dark background"""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    # Invert for light text on dark background
    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)

def preprocess_binary_dark(image):
    """Binary threshold optimized for dark text on light background"""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)

def preprocess_adaptive(image):
    """Adaptive thresholding for varying lighting conditions"""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
    return cv2.cvtColor(adaptive, cv2.COLOR_GRAY2RGB)

def preprocess_contrast(image):
    """Enhance contrast using CLAHE"""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        # Convert to LAB color space
        lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    return img_array

def preprocess_sharpen(image):
    """Sharpen image to make text clearer"""
    img_array = np.array(image)
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    sharpened = cv2.filter2D(img_array, -1, kernel)
    return sharpened

def preprocess_denoise(image):
    """Denoise while preserving edges"""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        denoised = cv2.fastNlMeansDenoisingColored(img_array, None, 10, 10, 7, 21)
        return denoised
    return img_array

def preprocess_image(image):
    """Legacy preprocessing function - basic binary threshold"""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
    return Image.fromarray(denoised)

# List of preprocessing strategies to try for dynamic content
PREPROCESSING_STRATEGIES = [
    ("original", preprocess_original),
    ("contrast", preprocess_contrast),
    ("sharpen", preprocess_sharpen),
    ("grayscale", preprocess_grayscale),
    ("adaptive", preprocess_adaptive),
    ("binary_light", preprocess_binary_light),
    ("binary_dark", preprocess_binary_dark),
    ("denoise", preprocess_denoise),
]

def run_ocr_on_image(img_array, confidence_threshold=0.6):
    """Run OCR on a numpy array image and return all detected text with positions"""
    results_list = []
    
    # Try PaddleOCR first
    if PADDLEOCR_AVAILABLE:
        try:
            reader = get_paddleocr_reader()
            if reader:
                results = reader.ocr(img_array, cls=True)
                if results and results[0]:
                    for line in results[0]:
                        bbox, (text, conf) = line
                        if conf >= confidence_threshold:
                            x = int(sum([point[0] for point in bbox]) / 4)
                            y = int(sum([point[1] for point in bbox]) / 4)
                            results_list.append({
                                'text': text,
                                'confidence': conf,
                                'x': x,
                                'y': y,
                                'engine': 'paddle'
                            })
        except Exception as e:
            pass
    
    # Also try EasyOCR for more coverage
    if EASYOCR_AVAILABLE and len(results_list) == 0:
        try:
            reader = get_easyocr_reader()
            if reader:
                results = reader.readtext(img_array)
                for (bbox, text, conf) in results:
                    if conf >= confidence_threshold:
                        x = int(sum([point[0] for point in bbox]) / 4)
                        y = int(sum([point[1] for point in bbox]) / 4)
                        results_list.append({
                            'text': text,
                            'confidence': conf,
                            'x': x,
                            'y': y,
                            'engine': 'easyocr'
                        })
        except Exception as e:
            pass
    
    return results_list

def find_text_multi_strategy(target_text, screenshot, confidence_threshold=0.6, region=None):
    """
    Try multiple preprocessing strategies to find text.
    Returns the best match across all strategies.
    """
    best_match = None
    best_score = 0
    
    for strategy_name, preprocess_func in PREPROCESSING_STRATEGIES:
        try:
            processed = preprocess_func(screenshot)
            results = run_ocr_on_image(processed, confidence_threshold * 0.8)  # Lower threshold for multi-strategy
            
            for result in results:
                is_match, fuzzy_score = fuzzy_match(target_text, result['text'])
                if is_match:
                    # Combined score from OCR confidence and fuzzy match
                    combined_score = (result['confidence'] * 0.4) + (fuzzy_score / 100 * 0.6)
                    if combined_score > best_score:
                        best_score = combined_score
                        best_match = {
                            'x': result['x'],
                            'y': result['y'],
                            'text': result['text'],
                            'confidence': result['confidence'],
                            'fuzzy_score': fuzzy_score,
                            'strategy': strategy_name
                        }
        except Exception as e:
            continue
    
    return best_match

def find_text_on_screen(target_text, region=None, confidence_threshold=0.6, preprocess=True, use_easyocr=True, multi_strategy=True):
    """
    Find text on screen using OCR with multiple strategies for dynamic content.
    Returns: (x, y) center coordinates if found, None otherwise
    """
    screenshot = capture_screen(region)
    
    # For dynamic game content, use multi-strategy approach
    if multi_strategy:
        result = find_text_multi_strategy(target_text, screenshot, confidence_threshold, region)
        if result:
            x, y = result['x'], result['y']
            # Adjust for region offset if provided
            if region:
                x += region[0]
                y += region[1]
            print(f"[{result['strategy']}] Found '{result['text']}' → '{target_text}' (conf: {result['confidence']:.2f}, fuzzy: {result['fuzzy_score']}) at ({x}, {y})")
            return (x, y)
    
    # Fallback to legacy single-strategy approach
    if preprocess:
        processed = preprocess_image(screenshot)
    else:
        processed = screenshot
    
    # Try PaddleOCR first if available
    if PADDLEOCR_AVAILABLE:
        try:
            reader = get_paddleocr_reader()
            if reader:
                # Convert PIL Image to numpy array
                img_array = np.array(processed)
                results = reader.ocr(img_array, cls=True)
                
                if results and results[0]:
                    for line in results[0]:
                        bbox, (text, conf) = line
                        if conf >= confidence_threshold:
                            # Try fuzzy matching
                            is_match, fuzzy_score = fuzzy_match(target_text, text)
                            if is_match:
                                # Calculate center from bounding box
                                x = int(sum([point[0] for point in bbox]) / 4)
                                y = int(sum([point[1] for point in bbox]) / 4)
                                
                                # Adjust for region offset if provided
                                if region:
                                    x += region[0]
                                    y += region[1]
                                
                                print(f"PaddleOCR found '{text}' → '{target_text}' (conf: {conf:.2f}, fuzzy: {fuzzy_score}) at ({x}, {y})")
                                return (x, y)
        except Exception as e:
            print(f"PaddleOCR error: {e}, falling back to EasyOCR")
    
    # Fallback to EasyOCR (if available and enabled)
    if use_easyocr and EASYOCR_AVAILABLE:
        try:
            reader = get_easyocr_reader()
            if reader:
                # Convert PIL Image to numpy array
                img_array = np.array(processed)
                results = reader.readtext(img_array)
                
                target_lower = target_text.lower()
                for (bbox, text, conf) in results:
                    if conf >= confidence_threshold:
                        # Try fuzzy matching
                        is_match, fuzzy_score = fuzzy_match(target_text, text)
                        if is_match:
                            # Calculate center from bounding box
                            x = int(sum([point[0] for point in bbox]) / 4)
                            y = int(sum([point[1] for point in bbox]) / 4)
                            
                            # Adjust for region offset if provided
                            if region:
                                x += region[0]
                                y += region[1]
                            
                            print(f"EasyOCR found '{text}' → '{target_text}' (conf: {conf:.2f}, fuzzy: {fuzzy_score}) at ({x}, {y})")
                            return (x, y)
        except Exception as e:
            print(f"EasyOCR error: {e}")
    
    if not EASYOCR_AVAILABLE and not PADDLEOCR_AVAILABLE:
        print("WARNING: No OCR engines available. Please install EasyOCR or PaddleOCR.")
    
    return None

def wait_for_stable_frame(region=None, stability_threshold=0.95, max_wait=2.0, check_interval=0.1):
    """
    Wait for the screen to stabilize (animations to settle).
    Compares consecutive frames and returns when they're similar enough.
    """
    import numpy as np
    
    last_frame = None
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        screenshot = capture_screen(region)
        current_frame = np.array(screenshot.convert('L'))  # Grayscale for faster comparison
        
        if last_frame is not None:
            # Compare frames using normalized cross-correlation
            if current_frame.shape == last_frame.shape:
                diff = np.abs(current_frame.astype(float) - last_frame.astype(float))
                similarity = 1.0 - (np.mean(diff) / 255.0)
                
                if similarity >= stability_threshold:
                    return screenshot  # Frame is stable
        
        last_frame = current_frame
        time.sleep(check_interval)
    
    # Return last frame even if not fully stable
    return capture_screen(region)

def find_text_multi_frame(target_text, region=None, confidence_threshold=0.6, num_frames=5, frame_delay=0.15):
    """
    Capture multiple frames and find text that appears consistently.
    This helps with dynamic/animated game content where a single frame might miss text.
    Enhanced for handling game animations with burst capture and consensus voting.
    Returns: (x, y) if found consistently, None otherwise
    """
    from collections import defaultdict
    
    position_votes = defaultdict(int)
    all_results = []
    text_found_count = 0
    
    # Burst capture: take multiple rapid screenshots
    screenshots = []
    for i in range(num_frames):
        screenshots.append(capture_screen(region))
        if i < num_frames - 1:
            time.sleep(frame_delay)
    
    # Process all screenshots
    for screenshot in screenshots:
        result = find_text_multi_strategy(target_text, screenshot, confidence_threshold, region)
        
        if result:
            text_found_count += 1
            # Round position to larger grid (20px) to account for animation jitter
            grid_x = round(result['x'] / 20) * 20
            grid_y = round(result['y'] / 20) * 20
            position_key = (grid_x, grid_y)
            position_votes[position_key] += 1
            all_results.append(result)
    
    # Debug output
    if all_results:
        print(f"[multi-frame] Found '{target_text}' in {text_found_count}/{num_frames} frames")
    
    # If we found the text in at least 1 frame, use it (more lenient for animated content)
    if position_votes:
        best_position = max(position_votes.items(), key=lambda x: x[1])
        
        # Get the result with highest combined score near this position
        best_result = None
        best_combined_score = 0
        for result in all_results:
            grid_x = round(result['x'] / 20) * 20
            grid_y = round(result['y'] / 20) * 20
            if (grid_x, grid_y) == best_position[0]:
                combined_score = result['confidence'] * 0.4 + result['fuzzy_score'] / 100 * 0.6
                if combined_score > best_combined_score:
                    best_combined_score = combined_score
                    best_result = result
        
        if best_result:
            x, y = best_result['x'], best_result['y']
            if region:
                x += region[0]
                y += region[1]
            print(f"[multi-frame] Confirmed '{best_result['text']}' at ({x}, {y}) - found in {best_position[1]}/{num_frames} frames (score: {best_combined_score:.2f})")
            return (x, y)
    
    return None

def find_text_with_retry(target_text, max_attempts=10, delay=0.5, region=None, tolerance=0.6):
    """
    Attempt to find text on screen with retries
    tolerance: OCR confidence threshold (0.0-1.0)
    Returns: (x, y) if found, None otherwise
    """
    for attempt in range(max_attempts):
        result = find_text_on_screen(target_text, region, confidence_threshold=tolerance)
        if result:
            return result
        time.sleep(delay)
    return None

def wait_for_text(target_text, timeout=30, check_interval=0.5, region=None, running_check=None, tolerance=0.6, use_multi_frame=True):
    """
    Wait until target text appears on screen
    running_check should return False when macro should stop
    tolerance: OCR confidence threshold (0.0-1.0)
    use_multi_frame: Use multi-frame consensus for dynamic content (default True)
    timeout: Maximum seconds to wait, or None for indefinite waiting
    Returns: (x, y) if found within timeout, None otherwise
    """
    start_time = time.time()
    attempt_count = 0
    
    while timeout is None or time.time() - start_time < timeout:
        # Check if macro should stop
        if running_check and not running_check():
            return None
        
        attempt_count += 1
        
        # Use multi-frame for better reliability with dynamic content
        # More frames and longer delay for better animation handling
        if use_multi_frame:
            result = find_text_multi_frame(target_text, region, confidence_threshold=tolerance, num_frames=5, frame_delay=0.15)
        else:
            result = find_text_on_screen(target_text, region, confidence_threshold=tolerance)
        
        if result:
            print(f"[wait_for_text] Found '{target_text}' after {attempt_count} attempts ({time.time() - start_time:.1f}s)")
            return result
        
        # Log every 5 attempts
        if attempt_count % 5 == 0:
            elapsed = time.time() - start_time
            print(f"[wait_for_text] Still searching for '{target_text}'... ({attempt_count} attempts, {elapsed:.1f}s)")
        
        time.sleep(check_interval)
    return None

def get_all_text_on_screen(region=None):
    """Get all visible text on screen for debugging"""
    screenshot = capture_screen(region)
    processed = preprocess_image(screenshot)
    
    # Try PaddleOCR first
    if PADDLEOCR_AVAILABLE:
        try:
            reader = get_paddleocr_reader()
            if reader:
                img_array = np.array(processed)
                results = reader.ocr(img_array, cls=True)
                if results and results[0]:
                    return '\n'.join([text for line in results[0] for bbox, (text, conf) in [line]])
        except:
            pass
    
    # Fallback to EasyOCR
    if EASYOCR_AVAILABLE:
        try:
            reader = get_easyocr_reader()
            if reader:
                img_array = np.array(processed)
                results = reader.readtext(img_array)
                return '\n'.join([text for (bbox, text, conf) in results])
        except:
            pass
    
    return ""

def find_any_text(target_texts, region=None, tolerance=0.6, use_multi_frame=True):
    """
    Find any of the target texts on screen using multi-strategy approach.
    Searches for all target texts in a single screenshot for efficiency.
    tolerance: OCR confidence threshold (0.0-1.0)
    use_multi_frame: Use multi-frame consensus for dynamic content
    Returns: (text_found, (x, y)) if found, (None, None) otherwise
    """
    # Capture once and search for all texts
    screenshot = capture_screen(region)
    
    for target_text in target_texts:
        if use_multi_frame:
            # For multi-frame, we need to use the full function
            result = find_text_multi_frame(target_text, region, confidence_threshold=tolerance, num_frames=2, frame_delay=0.05)
        else:
            result = find_text_multi_strategy(target_text, screenshot, tolerance, region)
            if result:
                x, y = result['x'], result['y']
                if region:
                    x += region[0]
                    y += region[1]
                result = (x, y)
        
        if result:
            return (target_text, result)
    
    return (None, None)

def find_any_text_fast(target_texts, region=None, tolerance=0.6):
    """
    Fast version of find_any_text - single screenshot, multiple strategies.
    Good for quick checks during upgrade loops.
    Returns: (text_found, (x, y)) if found, (None, None) otherwise
    """
    screenshot = capture_screen(region)
    
    for target_text in target_texts:
        result = find_text_multi_strategy(target_text, screenshot, tolerance, region)
        if result:
            x, y = result['x'], result['y']
            if region:
                x += region[0]
                y += region[1]
            return (target_text, (x, y))
    
    return (None, None)
