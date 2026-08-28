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

try:
    import cloudinary
    import cloudinary.uploader
except ImportError:  # pragma: no cover - exercised by configuration checks.
    cloudinary = None


MAX_AVATAR_BYTES = 5 * 1024 * 1024
MAX_AVATAR_DIMENSION = 512
ALLOWED_AVATAR_FORMATS = {"JPEG", "PNG", "WEBP"}
AVATAR_FOLDER = "produzzy/avatars"


class AvatarValidationError(ValueError):
    pass


class AvatarStorageNotConfiguredError(RuntimeError):
    pass


class AvatarStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreparedAvatar:
    content: bytes
    content_type: str = "image/webp"


@dataclass(frozen=True)
class AvatarUploadResult:
    url: str
    public_id: str


def is_configured():
    return all(
        (
            cloudinary,
            PRODUZZY_CLOUDINARY_CLOUD_NAME,
            PRODUZZY_CLOUDINARY_API_KEY,
            PRODUZZY_CLOUDINARY_API_SECRET,
        )
    )


def ensure_configured():
    if is_configured():
        return

    raise AvatarStorageNotConfiguredError(
        "Upload de foto de perfil ainda não configurado."
    )


async def prepare_avatar_file(file: UploadFile):
    content = await file.read(MAX_AVATAR_BYTES + 1)

    if len(content) > MAX_AVATAR_BYTES:
        raise AvatarValidationError("A imagem deve ter no máximo 5 MB.")

    if not content:
        raise AvatarValidationError("Envie uma imagem JPG, PNG ou WebP.")

    try:
        image = Image.open(BytesIO(content))
        image_format = (image.format or "").upper()

        if image_format == "JPG":
            image_format = "JPEG"

        if image_format not in ALLOWED_AVATAR_FORMATS:
            raise AvatarValidationError("Use uma imagem JPG, PNG ou WebP.")

        image = ImageOps.exif_transpose(image)
        image.load()
    except AvatarValidationError:
        raise
    except (OSError, UnidentifiedImageError, ValueError):
        raise AvatarValidationError("Use uma imagem JPG, PNG ou WebP.")

    width, height = image.size
    square_side = min(width, height)
    left = (width - square_side) // 2
    top = (height - square_side) // 2
    image = image.crop((left, top, left + square_side, top + square_side))

    if square_side > MAX_AVATAR_DIMENSION:
        image = image.resize(
            (MAX_AVATAR_DIMENSION, MAX_AVATAR_DIMENSION),
            Image.Resampling.LANCZOS,
        )

    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    output = BytesIO()
    image.save(output, format="WEBP", quality=86, method=6)

    return PreparedAvatar(content=output.getvalue())


def upload_avatar(content: bytes, user_id: int):
    ensure_configured()
    cloudinary.config(
        cloud_name=PRODUZZY_CLOUDINARY_CLOUD_NAME,
        api_key=PRODUZZY_CLOUDINARY_API_KEY,
        api_secret=PRODUZZY_CLOUDINARY_API_SECRET,
        secure=True,
    )

    try:
        result = cloudinary.uploader.upload(
            BytesIO(content),
            folder=AVATAR_FOLDER,
            public_id=f"user_{user_id}_{uuid4().hex}",
            resource_type="image",
            overwrite=True,
        )
    except Exception as error:
        raise AvatarStorageError("Não foi possível enviar a foto de perfil.") from error

    public_id = result.get("public_id")
    url = result.get("secure_url") or result.get("url")

    if not public_id or not url:
        raise AvatarStorageError("Não foi possível enviar a foto de perfil.")

    return AvatarUploadResult(url=url, public_id=public_id)


def delete_avatar(public_id: str):
    if not public_id:
        return

    ensure_configured()
    cloudinary.config(
        cloud_name=PRODUZZY_CLOUDINARY_CLOUD_NAME,
        api_key=PRODUZZY_CLOUDINARY_API_KEY,
        api_secret=PRODUZZY_CLOUDINARY_API_SECRET,
        secure=True,
    )

    try:
        cloudinary.uploader.destroy(
            public_id,
            invalidate=True,
            resource_type="image",
        )
    except Exception as error:
        raise AvatarStorageError("Não foi possível remover a foto de perfil.") from error
