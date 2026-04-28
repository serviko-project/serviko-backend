import uuid
from enum import Enum

from supabase import create_client

from app.core.config import get_settings
from app.core.exceptions import ValidationException


class StorageBucket(str, Enum):
    PROFILE_IMAGES = "profile-images"
    PROVIDER_DOCUMENTS = "provider-documents"


# Bucket validation rules
BUCKET_RULES: dict[StorageBucket, dict] = {
    StorageBucket.PROFILE_IMAGES: {
        "max_size_bytes": 5 * 1024 * 1024,  # 5 MB
        "allowed_mime_types": {"image/jpeg", "image/png", "image/webp"},
        "label": "Profile image",
    },
    StorageBucket.PROVIDER_DOCUMENTS: {
        "max_size_bytes": 10 * 1024 * 1024,  # 10MB
        "allowed_mime_types": {
            "image/jpeg",
            "image/png",
            "image/webp",
            "application/pdf",
        },
        "label": "Provider document",
    },
}


def _get_supabase_client():
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def _resolve_bucket_name(bucket: StorageBucket) -> str:
    settings = get_settings()
    if bucket == StorageBucket.PROFILE_IMAGES:
        return settings.SUPABASE_BUCKET_PROFILE_IMAGES
    return settings.SUPABASE_BUCKET_PROVIDER_DOCUMENTS


def validate_file(
    file_bytes: bytes,
    content_type: str,
    bucket: StorageBucket,
) -> None:
    rules = BUCKET_RULES[bucket]

    if len(file_bytes) > rules["max_size_bytes"]:
        max_mb = rules["max_size_bytes"] / (1024 * 1024)
        raise ValidationException(
            f"{rules['label']} must be smaller than {max_mb:.0f}MB"
        )

    if content_type not in rules["allowed_mime_types"]:
        allowed = ", ".join(sorted(rules["allowed_mime_types"]))
        raise ValidationException(
            f"{rules['label']} type '{content_type}' is not allowed. Allowed: {allowed}"
        )


def upload_file(
    bucket: StorageBucket,
    folder: str,
    file_bytes: bytes,
    content_type: str,
) -> str:
    # Validate before uploading
    validate_file(file_bytes, content_type, bucket)

    # Generate unique filename
    ext = content_type.split("/")[-1]
    if ext == "jpeg":
        ext = "jpg"
    filename = f"{folder}/{uuid.uuid4().hex}.{ext}"

    bucket_name = _resolve_bucket_name(bucket)
    client = _get_supabase_client()

    client.storage.from_(bucket_name).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": content_type},
    )

    # Public bucket for Profile Images -> return public URL
    if bucket == StorageBucket.PROFILE_IMAGES:
        return client.storage.from_(bucket_name).get_public_url(filename)

    # Private bucket for Provider Documents -> return relative path 
    return filename


def delete_file(bucket: StorageBucket, file_path: str) -> None:
    bucket_name = _resolve_bucket_name(bucket)
    client = _get_supabase_client()

    if file_path.startswith("http"):
        marker = f"/object/public/{bucket_name}/"
        idx = file_path.find(marker)
        if idx != -1:
            file_path = file_path[idx + len(marker):]

    client.storage.from_(bucket_name).remove([file_path])


def create_signed_url(
    bucket: StorageBucket,
    file_path: str,
    expires_in: int = 3600,
) -> str:
    bucket_name = _resolve_bucket_name(bucket)
    client = _get_supabase_client()
    result = client.storage.from_(bucket_name).create_signed_url(
        file_path, expires_in
    )
    return result["signedURL"]
