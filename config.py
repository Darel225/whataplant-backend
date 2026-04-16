"""
config.py — Variables de configuration
=======================================
Toutes les clés API et paramètres sont centralisés ici.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# BASE DE DONNEES MySQL
# ============================================================
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", "3306"))
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME     = os.getenv("DB_NAME", "whataplant")

# ============================================================
# API PLANTNET
# ============================================================
PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY", "")
PLANTNET_URL     = "https://my-api.plantnet.org/v2/identify/all"

# ============================================================
# API GROQ
# ============================================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

# Modèles vision disponibles
GROQ_VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "llama-3.2-11b-vision-preview",
]

# ============================================================
# PARAMETRES IMAGE
# ============================================================
IMAGE_SIZE    = (600, 600)
IMAGE_QUALITY = 95
UPLOAD_DIR    = "uploads"  # Dossier pour stocker les images scannées
UPLOAD_DIR_ABS = os.path.join(BASE_DIR, UPLOAD_DIR)

# ============================================================
# CLOUDINARY (stockage persistant images)
# ============================================================
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY    = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")
CLOUDINARY_FOLDER     = os.getenv("CLOUDINARY_FOLDER", "whataplant/scans")


# ============================================================
# DEBUG
# ============================================================
print(f"GROQ_API_KEY chargée: {'OUI' if GROQ_API_KEY else 'NON'} (longueur: {len(GROQ_API_KEY) if GROQ_API_KEY else 0})")
print(f"GROQ_VISION_MODELS: {GROQ_VISION_MODELS}")
print(f"IMAGE_SIZE: {IMAGE_SIZE}")
print(f"IMAGE_QUALITY: {IMAGE_QUALITY}")
print(f"UPLOAD_DIR: {UPLOAD_DIR}")
print(f"CLOUDINARY configuré: {'OUI' if (CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET) else 'NON'}")

