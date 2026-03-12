from PIL import ImageGrab
import numpy as np
import cv2
import easyocr
import time

time.sleep(2)
print("Initialized at ", time.time())
start = time.time()
# Initialize OCR
reader = easyocr.Reader(['en'])

print("OCR Initialized at ", time.time() - start, " from start")
# Capture screen
screenshot = ImageGrab.grab()

print(" Screenshot grabbed at ", time.time() - start, " from start")
img = np.array(screenshot)

print(" Converted to numpy array at ", time.time() - start, " from start")
img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

print(" Converted to BGR at ", time.time() - start, " from start")
# OCR
result = reader.readtext(img)

print(" OCR completed at ", time.time() - start, " from start")
# Filter low-confidence results
threshold = 0.7
filtered = [r for r in result if r[2] >= threshold]

# Print text + center coordinates
for bbox, text, conf in filtered:
    center_x = int((bbox[0][0] + bbox[2][0]) / 2)
    center_y = int((bbox[0][1] + bbox[2][1]) / 2)
    print(f"Text: '{text}' | Confidence: {conf:.2f} | Center: ({center_x},{center_y})")

# Optional: visualize
for bbox, text, conf in filtered:
    bbox = np.array(bbox).astype(int)
    cv2.polylines(img, [bbox.reshape((-1,1,2))], True, (0,255,0), 2)
    cv2.putText(img, text, (bbox[0][0], bbox[0][1]-5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

cv2.imshow("OCR Result", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
print(f"Time taken = {time.time() - start}")