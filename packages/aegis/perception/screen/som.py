import PIL.Image, PIL.ImageDraw, PIL.ImageFont
import logging

logger = logging.getLogger("aegis.screen.som")

def draw_som_labels(image: PIL.Image.Image, elements: list[dict]) -> PIL.Image.Image:
    """
    Draw bounding boxes and numeric labels on the image for each interactive element.
    
    Args:
        image: Original PIL Image.
        elements: List of dicts with 'id' and 'box'|'bbox' (x, y, w, h).
        
    Returns:
        Annotated PIL Image.
    """
    draw = PIL.ImageDraw.Draw(image)
    
    # Try to load a font, fallback to default
    try:
        font = PIL.ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
    except Exception:
        font = PIL.ImageFont.load_default()

    for el in elements:
        try:
            # Handle both 'box' from browser and 'bbox' from native
            box = el.get('box') or el.get('bbox')
            if not box:
                continue
                
            x, y, w, h = box['x'], box['y'], box['w'], box['h']
            label_id = str(el['id'])
            
            # Draw bounding box
            draw.rectangle([x, y, x + w, y + h], outline="red", width=2)
            
            # Draw label background
            text_bbox = draw.textbbox((x, y), label_id, font=font)
            # Add some padding
            label_rect = [x, y, text_bbox[2] + 4, text_bbox[3] + 4]
            draw.rectangle(label_rect, fill="red")
            
            # Draw label text
            draw.text((x + 2, y + 2), label_id, fill="white", font=font)
        except Exception as e:
            logger.error(f"Failed to draw label for element {el.get('id')}: {e}")

    return image
