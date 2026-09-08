"""
ArogyaX Healthcare Platform — Backend Configuration & Security Settings
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env with override
load_dotenv(override=True)

class Config:
    # ── Core Flask Security ──────────────────────────────────────────
    SECRET_KEY = os.getenv('SECRET_KEY', 'arogyax-enterprise-healthcare-secret-2024')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB maximum upload size
    
    # ── Session & Cookie Hardening ───────────────────────────────────
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # ── Paths & Upload Folders ───────────────────────────────────────
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'frontend', 'templates')
    STATIC_FOLDER = os.path.join(BASE_DIR, 'frontend', 'static')
    
    UPLOAD_FOLDER = os.path.join(STATIC_FOLDER, 'uploads', 'profile_photos')
    PRESCRIPTIONS_FOLDER = os.path.join(STATIC_FOLDER, 'prescriptions')
    SCANS_FOLDER = os.path.join(STATIC_FOLDER, 'uploads', 'profile_photos', 'scans')
    VAULT_FOLDER = os.path.join(STATIC_FOLDER, 'uploads', 'profile_photos', 'vault')
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf'}
    
    # ── MongoDB Atlas ────────────────────────────────────────────────
    MONGO_URI = os.getenv('MONGO_URI', '')
    
    # ── Google Gemini AI ─────────────────────────────────────────────
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = 'gemini-2.5-flash'
    
    # ── Mail Server Configuration ────────────────────────────────────
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
