from PIL import ImageGrab
import numpy as np
import cv2
import easyocr
import time
import base64
import io
import requests
import json

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "qwen3-vl:2b"   # change to e.g. "qwen3-vl:7b" for local weights
OCR_THRESHOLD   = 0.7
OCR_LANGUAGES   = ['en']
VISION_PROMPT   = "What do you see in this screenshot? Describe everything visible in detail."

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def ts(start: float) -> str:
    """Return a nicely formatted elapsed-time string."""
    return f"{time.time() - start:.3f}s"


def encode_image_to_base64(pil_image) -> str:
    """Convert a PIL image to a base64-encoded PNG string."""
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# ──────────────────────────────────────────────
# STEP 0 – warm-up delay
# ──────────────────────────────────────────────
time.sleep(2)
print("=" * 60)
print(f"Script started at  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
start = time.time()


# ──────────────────────────────────────────────
# STEP 1 – initialise OCR
# ──────────────────────────────────────────────
print(f"\n[{ts(start)}] Initialising EasyOCR (languages: {OCR_LANGUAGES}) …")
reader = easyocr.Reader(OCR_LANGUAGES)
print(f"[{ts(start)}] EasyOCR ready.")


# ──────────────────────────────────────────────
# STEP 2 – capture screen
# ──────────────────────────────────────────────
print(f"\n[{ts(start)}] Capturing screenshot …")
screenshot = ImageGrab.grab()
print(f"[{ts(start)}] Screenshot captured  ({screenshot.width}×{screenshot.height} px).")


# ──────────────────────────────────────────────
# STEP 3 – prepare OpenCV image
# ──────────────────────────────────────────────
print(f"\n[{ts(start)}] Converting to NumPy array …")
img_rgb = np.array(screenshot)
print(f"[{ts(start)}] Converted to NumPy array.")

print(f"[{ts(start)}] Converting colour space RGB → BGR …")
img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
print(f"[{ts(start)}] Colour conversion done.")


# ──────────────────────────────────────────────
# STEP 4 – run OCR
# ──────────────────────────────────────────────
print(f"\n[{ts(start)}] Running OCR …")
ocr_start = time.time()
result = reader.readtext(img_bgr)
print(f"[{ts(start)}] OCR finished in {time.time() - ocr_start:.3f}s  "
      f"({len(result)} raw detections).")

filtered = [r for r in result if r[2] >= OCR_THRESHOLD]
print(f"[{ts(start)}] After confidence filter (≥{OCR_THRESHOLD}): "
      f"{len(filtered)} detections kept.")

# print("\n── OCR Results ──")
# for bbox, text, conf in filtered:
#     cx = int((bbox[0][0] + bbox[2][0]) / 2)
#     cy = int((bbox[0][1] + bbox[2][1]) / 2)
#     print(f"  Text: '{text:<40}' | Conf: {conf:.2f} | Centre: ({cx}, {cy})")


# ──────────────────────────────────────────────
# STEP 5 – annotate image
# ──────────────────────────────────────────────
print(f"\n[{ts(start)}] Annotating image with OCR bounding boxes …")
annotated = img_bgr.copy()
for bbox, text, conf in filtered:
    pts = np.array(bbox).astype(int)
    cv2.polylines(annotated, [pts.reshape((-1, 1, 2))], True, (0, 255, 0), 2)
    cv2.putText(annotated, text,
                (pts[0][0], pts[0][1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
print(f"[{ts(start)}] Annotation complete.")


# ──────────────────────────────────────────────
# STEP 6 – send screenshot to Qwen3-VL via Ollama
# ──────────────────────────────────────────────
print(f"\n[{ts(start)}] Encoding screenshot as base64 for Qwen3-VL …")
b64_image = encode_image_to_base64(screenshot)
print(f"[{ts(start)}] Encoding done  ({len(b64_image):,} chars).")

print(f"[{ts(start)}] Sending request to Ollama  (model: {OLLAMA_MODEL}) …")
print(f"           Prompt: \"{VISION_PROMPT}\"")

vision_start = time.time()
try:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "user",
                "content": VISION_PROMPT,
                "images": [b64_image],
            }
        ],
        "stream": False,
    }

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=300,          # generous timeout for large model
    )
    response.raise_for_status()

    data = response.json()
    vision_reply = data.get("message", {}).get("content", "<no content returned>")
    vision_elapsed = time.time() - vision_start

    print(f"[{ts(start)}] Qwen3-VL responded in {vision_elapsed:.3f}s.")
    print("\n── Qwen3-VL Vision Response ──")
    print(vision_reply)

except requests.exceptions.ConnectionError:
    print(f"[{ts(start)}] ✗ Could not connect to Ollama at {OLLAMA_BASE_URL}.")
    print("          Make sure Ollama is running:  ollama serve")
except requests.exceptions.Timeout:
    print(f"[{ts(start)}] ✗ Request timed out. The model may still be loading.")
except Exception as exc:
    print(f"[{ts(start)}] ✗ Unexpected error: {exc}")


# ──────────────────────────────────────────────
# STEP 7 – display annotated image
# ──────────────────────────────────────────────
print(f"\n[{ts(start)}] Opening annotated preview (press any key to close) …")
cv2.imshow("OCR Result – Qwen3-VL Screen Analyser", annotated)
cv2.waitKey(0)
cv2.destroyAllWindows()


# ──────────────────────────────────────────────
# DONE
# ──────────────────────────────────────────────
total = time.time() - start
print(f"\n{'=' * 60}")
print(f"  Total runtime: {total:.3f}s")
print(f"{'=' * 60}\n")