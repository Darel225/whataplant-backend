import cloudinary
import cloudinary.uploader
from typing import Optional, Dict, Any

from config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_FOLDER,
)


def cloudinary_est_configure() -> bool:
    return bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)


def configurer_cloudinary() -> None:
    if not cloudinary_est_configure():
        return
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )


def uploader_image_bytes(
    image_bytes: bytes,
    *,
    user_id: Optional[int] = None,
    filename: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Upload une image sur Cloudinary et renvoie le résultat (incl. secure_url).
    Retourne None si Cloudinary n'est pas configuré.
    """
    if not cloudinary_est_configure():
        return None

    configurer_cloudinary()

    public_id = None
    if filename:
        public_id = filename.rsplit(".", 1)[0]

    folder = CLOUDINARY_FOLDER
    if user_id is not None:
        folder = f"{CLOUDINARY_FOLDER}/user_{user_id}"

    result = cloudinary.uploader.upload(
        image_bytes,
        resource_type="image",
        folder=folder,
        public_id=public_id,
        overwrite=False,
        unique_filename=True,
    )
    return result

