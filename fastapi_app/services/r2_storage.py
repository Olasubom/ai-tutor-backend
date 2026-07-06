"""Cloudflare R2 storage client — optional S3-compatible upload backend for Render deployments."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY_ID", "")
_SECRET_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
_BUCKET = os.environ.get("R2_BUCKET_NAME", "aitutor-uploads")


def is_configured() -> bool:
    return bool(_ACCOUNT_ID and _ACCESS_KEY and _SECRET_KEY and _BUCKET)


def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=f"https://{_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=_ACCESS_KEY,
        aws_secret_access_key=_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def upload_file(local_path: str, object_key: str) -> str:
    """Upload a file to R2. Returns the object key."""
    if not is_configured():
        raise RuntimeError("R2 is not configured")
    _client().upload_file(local_path, _BUCKET, object_key)
    return object_key


def download_file(object_key: str, local_path: str) -> None:
    """Download a file from R2 to a local path."""
    if not is_configured():
        raise RuntimeError("R2 is not configured")
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    _client().download_file(_BUCKET, object_key, local_path)


def get_file_bytes(object_key: str) -> Optional[bytes]:
    """Read a file's bytes directly from R2 without saving to disk."""
    if not is_configured():
        return None
    try:
        response = _client().get_object(Bucket=_BUCKET, Key=object_key)
        return response["Body"].read()
    except Exception:
        logger.exception("r2_get_failed", extra={"object_key": object_key})
        return None


def file_exists(object_key: str) -> bool:
    if not is_configured():
        return False
    try:
        _client().head_object(Bucket=_BUCKET, Key=object_key)
        return True
    except Exception:
        return False
