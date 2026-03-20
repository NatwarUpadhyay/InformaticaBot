"""Vision module for image captioning supporting both local and API models.
Can switch between local lightweight models and OpenRouter API.
"""
import requests
import base64
from src.config import OPENROUTER_KEY
from PIL import Image
import io

# --- Configuration ---
# API Models - use Mistral Small 3.1 which is free and reliable
VISION_API_MODEL = "mistralai/mistral-small-3.1-24b-instruct:free"  # Free, reliable, good quality
VISION_API_FALLBACK = "openrouter/auto"  # Auto-select best available model
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Local Models - lightweight vision options
LOCAL_VISION_MODEL = "Salesforce/blip-image-captioning-base"  # Reliable image captioning

# Default mode
# Use API = True for good quality with Mistral Small 3.1 (free)
# Falls back to local BLIP if API fails
USE_LOCAL = False  # Use API model by default (Mistral Small 3.1 is free and good)

# Global pipeline cache for local models
_vision_pipeline = None

def _init_local_vision_pipeline():
    """Initialize local vision pipeline (lazy loading)"""
    global _vision_pipeline
    
    if _vision_pipeline is None:
        print(f"🚀 Loading local vision model: {LOCAL_VISION_MODEL}")
        from transformers import BlipForConditionalGeneration, AutoProcessor
        import torch
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        _vision_pipeline = {
            "model": BlipForConditionalGeneration.from_pretrained(LOCAL_VISION_MODEL).to(device),
            "processor": AutoProcessor.from_pretrained(LOCAL_VISION_MODEL),
            "device": device
        }
    
    return _vision_pipeline

def set_vision_source(use_local: bool = False):
    """Switch between local and API models"""
    global USE_LOCAL
    USE_LOCAL = use_local
    if use_local:
        _init_local_vision_pipeline()

def caption_image(image_bytes: bytes, use_local: bool = None) -> dict:
    """
    Generate caption and tags for an image.
    
    Args:
        image_bytes: Raw image bytes
        use_local: Override global setting (None = use global USE_LOCAL)
        
    Returns:
        dict with 'caption' and 'tags' keys
    """
    mode = use_local if use_local is not None else USE_LOCAL
    
    if mode:
        return _caption_local(image_bytes)
    else:
        return _caption_api(image_bytes)

def _caption_local(image_bytes: bytes) -> dict:
    """Generate caption using local BLIP model"""
    try:
        from PIL import Image as PILImage
        import torch
        
        pipeline = _init_local_vision_pipeline()
        model = pipeline["model"]
        processor = pipeline["processor"]
        device = pipeline["device"]
        
        # Load and convert image
        image = PILImage.open(io.BytesIO(image_bytes))
        image = image.convert("RGB")
        
        # Process image and generate caption
        inputs = processor(images=image, return_tensors="pt").to(device)
        
        with torch.no_grad():
            out = model.generate(**inputs, max_length=50, num_beams=3)
        
        caption_text = processor.decode(out[0], skip_special_tokens=True).strip()
        
        if not caption_text:
            caption_text = "A photo of an image."
        
        # Extract tags
        words = caption_text.lower().split()
        stop_words = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "is", "are", "was", "were", "of", "for", "with", "by", "this", "that"}
        tags = [w.strip(".,!?;:") for w in words if w.lower() not in stop_words and len(w) > 2][:3]
        
        return {
            "caption": caption_text,
            "tags": tags if tags else ["image", "photo", "picture"]
        }
        
    except Exception as e:
        print(f"⚠️ Local Vision Model Error: {str(e)}")
        return {
            "caption": "Unable to generate caption with local model.",
            "tags": ["error"],
            "error": str(e)
        }

def _caption_api(image_bytes: bytes) -> dict:
    """Generate caption using Mistral Small 3.1 from OpenRouter
    
    Mistral Small 3.1 is:
    - Free tier available
    - Reliable and stable
    - Good at following structured prompts
    - Fast responses
    
    Falls back to local BLIP if API fails
    """
    try:
        # Validate image
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("RGB")
        
        # Convert to base64 with proper data URL format
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        image_data_url = f"data:image/jpeg;base64,{image_base64}"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "RAG Bot",
            "Content-Type": "application/json"
        }
        
        # Structured prompt for Mistral
        prompt_text = (
            "Look at this image carefully and respond in exactly this format:\n"
            "CAPTION: <one sentence describing what is in the image>\n"
            "TAGS: <tag1>, <tag2>, <tag3>\n\n"
            "Keep the caption under 15 words. Tags should be single descriptive words."
        )
        
        # Try primary model first (Mistral Small 3.1)
        payload = {
            "model": VISION_API_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt_text
                        }
                    ]
                }
            ],
            "temperature": 0.3,
            "max_tokens": 150
        }
        
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=15)
        
        # If primary fails, try fallback
        if response.status_code != 200:
            print(f"⚠️ Mistral Small failed ({response.status_code}), trying fallback...")
            payload["model"] = VISION_API_FALLBACK
            response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=15)
        
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            text = result["choices"][0]["message"]["content"].strip()
            
            # Parse structured format: CAPTION: ... TAGS: ...
            caption = ""
            tags = []
            
            for line in text.split('\n'):
                line = line.strip()
                if line.startswith("CAPTION:"):
                    caption = line.replace("CAPTION:", "").strip()
                elif line.startswith("TAGS:"):
                    tags_str = line.replace("TAGS:", "").strip()
                    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            
            # Fallback if parsing failed
            if not caption:
                caption = text.split('\n')[0][:100]
            if not tags:
                tags = ["image", "photo"]
            
            return {
                "caption": caption,
                "tags": tags[:3]  # Limit to 3 tags
            }
        else:
            # Empty response, use local
            print("⚠️ API returned empty response, using local BLIP")
            return _caption_local(image_bytes)
            
    except requests.exceptions.Timeout:
        print("⚠️ API timeout, using local BLIP")
        return _caption_local(image_bytes)
    except requests.exceptions.ConnectionError:
        print("⚠️ API connection error, using local BLIP")
        return _caption_local(image_bytes)
    except Exception as e:
        print(f"⚠️ API error ({str(e)}), using local BLIP")
        return _caption_local(image_bytes)

def _fallback_caption(image) -> str:
    """Fallback caption generation based on image properties"""
    try:
        if image is None:
            return "Image analysis: Unable to process the image at this time."
        
        # Use basic image properties for fallback
        width, height = image.size
        aspect = "landscape" if width > height else ("portrait" if height > width else "square")
        
        # Try to detect basic colors
        colors = _get_dominant_colors(image)
        color_desc = f"with {colors} tones" if colors else ""
        
        return f"Image analysis: A {aspect} format image {color_desc}. Image dimensions: {width}x{height} pixels."
    except:
        return "Image analysis: An image has been uploaded. Unable to generate detailed description at this time."

def _get_dominant_colors(image) -> str:
    """Get basic color information from image"""
    try:
        # Simple color detection
        pixels = list(image.getdata())
        if not pixels:
            return ""
        
        avg_r = sum(p[0] if isinstance(p, tuple) else p for p in pixels) // len(pixels)
        
        if avg_r > 150:
            return "bright"
        elif avg_r < 100:
            return "dark"
        else:
            return "medium-toned"
    except:
        return ""

def describe_image(image_bytes: bytes, use_local: bool = None) -> str:
    """
    Generate a complete description for an image (caption + tags).
    
    Args:
        image_bytes: Raw image bytes
        use_local: Override global setting (None = use global USE_LOCAL)
        
    Returns:
        Formatted description string
    """
    result = caption_image(image_bytes, use_local=use_local)
    
    caption = result.get("caption", "No caption generated")
    tags = result.get("tags", [])
    
    description = f"📸 **Image Description:**\n\n{caption}\n\n"
    if tags:
        description += f"🏷️ **Tags**: {', '.join(tags)}"
    
    return description
