"""Product photos on Cloudinary (same account as profile photos).

Uploads are normalised before leaving the server: EXIF rotation applied,
longest side capped, re-encoded as WebP. Thumbnails are produced by Cloudinary
URL transformations on the frontend, so only one file is stored per product.
"""
import logging
from dataclasses import dataclass
from io import BytesIO
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import (
    PRODUZZY_CLOUDINARY_API_KEY,
    PRODUZZY_CLOUDINARY_API_SECRET,
    PRODUZZY_CLOUDINARY_CLOUD_NAME,
)
from app.services import avatar_storage_service

MAX_PRODUCT_IMAGE_BYTES = 8 * 1024 * 1024
MAX_PRODUCT_IMAGE_DIMENSION = 1200
ALLOWED_PRODUCT_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
PRODUCT_IMAGE_FOLDER = "produzzy/products"

logger = logging.getLogger(__name__)


class ProductImageValidationError(ValueError):
    pass


class ProductImageStorageNotConfiguredError(RuntimeError):
    pass


class ProductImageStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProductImageUploadResult:
    url: str
    public_id: str


def _configure():
    if not avatar_storage_service.is_configured():
        raise ProductImageStorageNotConfiguredError(
            "Upload de foto de produto ainda não configurado."
        )

    cloudinary = avatar_storage_service.cloudinary
    cloudinary.config(
        cloud_name=PRODUZZY_CLOUDINARY_CLOUD_NAME,
        api_key=PRODUZZY_CLOUDINARY_API_KEY,
        api_secret=PRODUZZY_CLOUDINARY_API_SECRET,
        secure=True,
    )
    return cloudinary


async def prepare_product_image(file: UploadFile) -> bytes:
    content = await file.read(MAX_PRODUCT_IMAGE_BYTES + 1)

    if len(content) > MAX_PRODUCT_IMAGE_BYTES:
        raise ProductImageValidationError("A imagem deve ter no máximo 8 MB.")

    if not content:
        raise ProductImageValidationError("Envie uma imagem JPG, PNG ou WebP.")

    try:
        image = Image.open(BytesIO(content))
        image_format = (image.format or "").upper()

        if image_format == "JPG":
            image_format = "JPEG"

        if image_format not in ALLOWED_PRODUCT_IMAGE_FORMATS:
            raise ProductImageValidationError("Use uma imagem JPG, PNG ou WebP.")

        image = ImageOps.exif_transpose(image)
        image.load()
    except ProductImageValidationError:
        raise
    except (OSError, UnidentifiedImageError, ValueError):
        raise ProductImageValidationError("Use uma imagem JPG, PNG ou WebP.")

    # Keep the photo's own proportions; the UI crops thumbnails to squares.
    image.thumbnail(
        (MAX_PRODUCT_IMAGE_DIMENSION, MAX_PRODUCT_IMAGE_DIMENSION),
        Image.Resampling.LANCZOS,
    )

    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    output = BytesIO()
    image.save(output, format="WEBP", quality=84, method=6)

    return output.getvalue()


def upload_product_image(content: bytes, workspace_id: int, product_id: int):
    cloudinary = _configure()

    try:
        result = cloudinary.uploader.upload(
            BytesIO(content),
            folder=PRODUCT_IMAGE_FOLDER,
            public_id=f"ws{workspace_id}_p{product_id}_{uuid4().hex}",
            resource_type="image",
            overwrite=True,
        )
    except Exception as error:
        raise ProductImageStorageError(
            "Não foi possível enviar a foto do produto."
        ) from error

    public_id = result.get("public_id")
    url = result.get("secure_url") or result.get("url")

    if not public_id or not url:
        raise ProductImageStorageError("Não foi possível enviar a foto do produto.")

    return ProductImageUploadResult(url=url, public_id=public_id)


def delete_product_image(public_id: str | None):
    if not public_id:
        return

    cloudinary = _configure()

    try:
        cloudinary.uploader.destroy(public_id, invalidate=True, resource_type="image")
    except Exception as error:
        raise ProductImageStorageError(
            "Não foi possível remover a foto do produto."
        ) from error


def delete_product_image_quietly(public_id: str | None):
    """Best-effort removal: a storage hiccup must not fail the request whose
    database change already happened."""
    try:
        delete_product_image(public_id)
    except Exception:
        logger.exception("Failed to remove a product image from storage.")
