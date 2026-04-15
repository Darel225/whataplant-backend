"""
services/opencv_service.py — Prétraitement image (version minimale)
"""

import cv2
import numpy as np
import base64
from config import IMAGE_SIZE, IMAGE_QUALITY


def pretraiter_depuis_bytes(image_bytes: bytes) -> bytes:
    """
    Version minimale : seulement redimensionnement et conversion.
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Image illisible ou format non supporté")

    # Seulement redimensionner
    img = cv2.resize(img, IMAGE_SIZE)

    # Reconvertit en bytes JPEG
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, IMAGE_QUALITY])
    return buffer.tobytes()


def pretraiter_depuis_base64(image_base64: str) -> bytes:
    """Reçoit une image en Base64 et retourne les bytes."""
    if "," in image_base64:
        image_base64 = image_base64.split(",")[1]
    image_bytes = base64.b64decode(image_base64)
    return pretraiter_depuis_bytes(image_bytes)