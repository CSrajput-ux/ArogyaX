"""
ArogyaX Healthcare Platform — Security Validation & Sanitization Helpers
"""

import os
import random
import string
from werkzeug.utils import secure_filename
from PIL import Image
from backend.config import Config

def allowed_file(filename):
    """Check if the uploaded file has a permitted extension."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

def validate_image_integrity(filepath):
    """
    Validate that an uploaded image file is a valid, readable image using PIL.
    Prevents polyglot file execution and corrupted uploads.
    """
    try:
        with Image.open(filepath) as img:
            img.verify()
        return True
    except Exception:
        return False

def sanitize_safe_filename(prefix, raw_filename):
    """Generate a clean, sanitized unique filename for uploads."""
    clean_name = secure_filename(raw_filename)
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    name_part, ext = os.path.splitext(clean_name)
    return f"{prefix}_{name_part[:30]}_{rand_suffix}{ext}"

def sanitize_text(text, max_len=1000):
    """Strip dangerous characters and trim text input."""
    if not text:
        return ''
    return str(text).strip()[:max_len]
