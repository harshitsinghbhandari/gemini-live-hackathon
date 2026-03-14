import asyncio
import random
import string
import time
import logging
import concurrent.futures
from typing import List, Dict
import numpy as np
import cv2
import mss

from rapidocr_onnxruntime import RapidOCR

logger = logging.getLogger("aegis.screen.ocr")

ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# Initialize RapidOCR once
try:
    ocr_engine = RapidOCR()
    logger.info("RapidOCR engine initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RapidOCR: {e}")
    ocr_engine = None

OCR_CONFIDENCE_THRESHOLD = 0.4  # RapidOCR confidence threshold
IOU_THRESHOLD = 0.5
TILE_RESIZE_FACTOR = 0.5
MAX_THREADS = 6

# Tile definitions
tiles = []
tile_cache = {}

def _generate_id(length: int = 4) -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def calculate_iou(box1, box2):
    y1_min, x1_min, y1_max, x1_max = box1
    y2_min, x2_min, y2_max, x2_max = box2

    inter_ymin = max(y1_min, y2_min)
    inter_xmin = max(x1_min, x2_min)
    inter_ymax = min(y1_max, y2_max)
    inter_xmax = min(x1_max, x2_max)

    inter_area = max(0, inter_ymax - inter_ymin) * max(0, inter_xmax - inter_xmin)
    area1 = (y1_max - y1_min) * (x1_max - x1_min)
    area2 = (y2_max - y2_min) * (x2_max - x2_min)

    union_area = area1 + area2 - inter_area
    return inter_area / union_area if union_area != 0 else 0

def _get_regions_for_element(ymin, xmin, h, w) -> List[str]:
    regions = []
    if ymin < h * 0.05: regions.append("top_bar")
    elif ymin > h * 0.95: regions.append("bottom_bar")
    if h * 0.05 <= ymin <= h * 0.95:
        if xmin < w * 0.15: regions.append("left_sidebar")
        elif xmin > w * 0.85: regions.append("right_sidebar")
        else: regions.append("main_content")
    if not regions: regions.append("main_content")
    return regions

def _run_ocr_on_tile(tile_img: np.ndarray, tile_info: Dict) -> List[Dict]:
    if ocr_engine is None: return []

    start_time = time.time()
    small_tile = cv2.resize(tile_img, None, fx=TILE_RESIZE_FACTOR, fy=TILE_RESIZE_FACTOR)
    results, _ = ocr_engine(small_tile)
    if not results: return []

    elements = []
    offset_x, offset_y = tile_info['bbox'][0], tile_info['bbox'][1]

    for bbox, text, conf in results:
        if conf < OCR_CONFIDENCE_THRESHOLD: continue
        xmin = int(bbox[0][0] / TILE_RESIZE_FACTOR) + offset_x
        ymin = int(bbox[0][1] / TILE_RESIZE_FACTOR) + offset_y
        xmax = int(bbox[2][0] / TILE_RESIZE_FACTOR) + offset_x
        ymax = int(bbox[2][1] / TILE_RESIZE_FACTOR) + offset_y
        elements.append({
            "text": text,
            "ymin": ymin, "xmin": xmin, "ymax": ymax, "xmax": xmax,
            "confidence": round(float(conf), 3)
        })

    logger.debug(f"Tile {tile_info['id']} OCR took {time.time() - start_time:.3f}s, found {len(elements)}")
    return elements

def _init_tiles(w, h):
    global tiles
    tiles = []
    rows, cols = 2, 3
    tile_w, tile_h = w // cols, h // rows
    for r in range(rows):
        for c in range(cols):
            xmin = c * tile_w
            ymin = r * tile_h
            xmax = (c + 1) * tile_w if c < cols - 1 else w
            ymax = (r + 1) * tile_h if r < rows - 1 else h
            tiles.append({
                'id': f"tile_{r}_{c}",
                'bbox': (xmin, ymin, xmax, ymax),
                'screen_w': w,
                'screen_h': h
            })

def _process_frame(context):
    global tiles, tile_cache

    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)[:, :, :3]
        h, w = img.shape[:2]

    if not tiles or tiles[0]['screen_w'] != w or tiles[0]['screen_h'] != h:
        _init_tiles(w, h)

    changed_tiles = []
    for tile in tiles:
        xmin, ymin, xmax, ymax = tile['bbox']
        tile_img = img[ymin:ymax, xmin:xmax]

        prev_tile = tile_cache.get(tile['id'], {}).get('img')
        is_changed = True
        if prev_tile is not None and prev_tile.shape == tile_img.shape:
            diff = cv2.absdiff(prev_tile, tile_img)
            _, thresh = cv2.threshold(cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY), 25, 255, cv2.THRESH_BINARY)
            if cv2.countNonZero(thresh) < 100:
                is_changed = False

        if is_changed:
            changed_tiles.append((tile, tile_img))
            existing = tile_cache.get(tile['id'], {}).get('elements', [])
            tile_cache[tile['id']] = {'img': tile_img, 'timestamp': time.time(), 'elements': existing}

    if not changed_tiles:
        return None

    all_new_elements = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(_run_ocr_on_tile, img_data, info): info for info, img_data in changed_tiles}
        for future in concurrent.futures.as_completed(futures):
            elements = future.result()
            tile_id = futures[future]['id']
            tile_cache[tile_id]['elements'] = elements
            all_new_elements.extend(elements)

    merged_elements = []
    for tile in tiles:
        merged_elements.extend(tile_cache.get(tile['id'], {}).get('elements', []))

    deduplicated = []
    merged_elements.sort(key=lambda x: x['confidence'], reverse=True)
    for el in merged_elements:
        if all(calculate_iou((el['ymin'], el['xmin'], el['ymax'], el['xmax']),
                             (d_el['ymin'], d_el['xmin'], d_el['ymax'], d_el['xmax'])) <= IOU_THRESHOLD
               for d_el in deduplicated):
            deduplicated.append(el)

    final_elements = {}
    annotated_json = []
    regions_map = {r: [] for r in ["top_bar", "bottom_bar", "left_sidebar", "right_sidebar", "main_content"]}

    for i, el in enumerate(deduplicated):
        eid = _generate_id()
        el['id'] = eid
        el['label_num'] = i + 1
        final_elements[eid] = el

        annotated_json.append({
            'id': eid,
            'text': el['text'],
            'ymin': el['ymin'], 'ymax': el['ymax'],
            'xmin': el['xmin'], 'xmax': el['xmax'],
            'label_num': el['label_num']
        })

        for region in _get_regions_for_element(el['ymin'], el['xmin'], h, w):
            regions_map[region].append({'id': eid, 'text': el['text'], 'label_num': el['label_num']})

    return {
        "elements": final_elements,
        "regions": regions_map,
        "annotated_json": annotated_json,
        "screen_w": w,
        "screen_h": h,
        "timestamp": time.time(),
        "count": len(final_elements)
    }

async def ocr_background_loop(context) -> None:
    """Background OCR loop for RapidOCR."""
    logger.info("RapidOCR background loop started")
    from aegis.tools.context import window_state

    OCR_LOOP_DELAY = 10

    while True:
        try:
            loop_start = time.time()
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(ocr_executor, _process_frame, context)

            if result:
                context.ocr_cache = result
                setattr(window_state, 'ocr_cache', result)
                duration = time.time() - loop_start
                logger.info(f"OCR Pipeline latency: {duration:.3f}s | Detected: {result['count']}")

        except Exception as e:
            logger.error(f"OCR loop error: {e}")
            await asyncio.sleep(1)

        await asyncio.sleep(OCR_LOOP_DELAY)