import cv2
import numpy as np
from PIL import ImageGrab, Image
import os

region = (796,168,1756,768)
script_dir = os.path.dirname(__file__)
template_path = os.path.join(script_dir, 'buttons', 'Areas.png')
print('Template path:', template_path)

template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
if template is None:
    print('Failed to load template')
    raise SystemExit(1)
print('Template shape:', template.shape)

screenshot = ImageGrab.grab(bbox=region)
screenshot_path = os.path.join(script_dir, 'debug_screenshot.png')
screenshot.save(screenshot_path)
print('Saved screenshot to', screenshot_path)

screen_np = np.array(screenshot.convert('L'))
print('Screenshot shape (H,W):', screen_np.shape)

res = cv2.matchTemplate(screen_np, template, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
print('matchTemplate min_val, max_val:', min_val, max_val)
print('max_loc:', max_loc)

# Draw rectangle on original colored screenshot
screenshot_color = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
h, w = template.shape
top_left = max_loc
bottom_right = (top_left[0] + w, top_left[1] + h)
cv2.rectangle(screenshot_color, top_left, bottom_right, (0,0,255), 2)
debug_out = os.path.join(script_dir, 'debug_match_areas.png')
cv2.imwrite(debug_out, screenshot_color)
print('Wrote debug match image to', debug_out)

# Also print center coordinates adjusted to full screen
center_x = max_loc[0] + w//2 + region[0]
center_y = max_loc[1] + h//2 + region[1]
print('Detected center (screen coords):', (center_x, center_y))
print('Confidence:', max_val)
