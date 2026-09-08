"""
ArogyaX Healthcare Platform — Google Gemini AI Integration Service
Features: Natural language clinical explanations & Multimodal Vision Scan Analysis
"""

import os
import certifi
from PIL import Image
from backend.config import Config

try:
    from google import genai as google_genai
    from google.genai import types as genai_types
    GEMINI_SDK_AVAILABLE = True
except Exception:
    GEMINI_SDK_AVAILABLE = False

GEMINI_AVAILABLE = GEMINI_SDK_AVAILABLE
gemini_client = None

def init_gemini(app=None):
    global gemini_client
    if GEMINI_SDK_AVAILABLE and Config.GEMINI_API_KEY and not Config.GEMINI_API_KEY.startswith('AIzaSyYOUR'):
        try:
            gemini_client = google_genai.Client(api_key=Config.GEMINI_API_KEY)
            print("SUCCESS: Gemini AI connected successfully.")
        except Exception as e:
            print(f"WARNING: Gemini AI init failed: {e}")
            gemini_client = None
    else:
        print("INFO: Gemini AI not configured or key missing.")

def is_gemini_enabled():
    return gemini_client is not None

def get_disease_explanation(disease, symptoms_list):
    """Call Google Gemini to generate plain-language clinical insights & home care tips."""
    if not gemini_client:
        return None
    try:
        prompt = f"""You are a helpful, empathetic medical assistant on the ArogyaX digital healthcare platform.
A patient is experiencing symptoms: {', '.join(symptoms_list)}.
Our AI diagnostic assessment indicates a probable match for: {disease}.

Please provide:
1. Clinical Summary: A brief, plain-language explanation of {disease} in 2-3 sentences.
2. Home Care & Supportive Measures: 3-4 clear, practical recommendations.
3. Clinical Next Steps: A clear recommendation regarding when to consult a medical doctor.

Maintain a professional, reassuring tone. Use clean paragraph breaks and headers."""

        response = gemini_client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Gemini LLM error: {e}")
        return None

get_gemini_disease_explanation = get_disease_explanation

def analyze_medical_scan(image_path, scan_type):
    """Analyze radiological scans (Brain MRI, Chest X-Ray, Cataract Eye) using Gemini Multimodal Vision."""
    if not gemini_client or not os.path.exists(image_path):
        return None
    try:
        img = Image.open(image_path)
        prompts = {
            'brain': "This is a brain MRI scan uploaded to the ArogyaX healthcare platform. Analyze this image for educational and clinical guidance purposes. Describe observations in clear clinical terms a patient can understand (structural symmetry, ventricles, any focal density anomalies). Always conclude with a disclaimer that this is a preliminary AI review and formal radiological evaluation is required.",
            'lung': "This is a chest X-ray image uploaded to the ArogyaX healthcare platform. Analyze the lung fields, cardiac silhouette, and rib cage. Note any opacities, consolidation, or effusion patterns. Always conclude with a disclaimer that this is a preliminary AI review and a pulmonologist consultation is recommended.",
            'cataract': "This is an ocular / eye photograph uploaded to the ArogyaX healthcare platform. Analyze the clarity of the lens, pupil margin, and cornea for signs of cataract or cloudiness. Always conclude with a disclaimer that this is an AI screening tool and an ophthalmologist slit-lamp exam is needed.",
        }
        prompt = prompts.get(scan_type, "Analyze this medical image for clinical overview purposes. Always end with a medical disclaimer.")
        response = gemini_client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=[prompt, img]
        )
        return response.text
    except Exception as e:
        print(f"Gemini Vision error: {e}")
        return None

analyze_scan_with_gemini = analyze_medical_scan
