# apps/core/r2_client.py

import boto3
import os

# ✅ FIX: `get_current_tenant` was used inside `generate_r2_key` but was never
#         imported. Every file upload would crash with NameError.
from apps.tenants.context import get_current_tenant

CLOUDFLARE_R2_KEY_ID     = os.getenv("CLOUDFLARE_R2_KEY_ID")
CLOUDFLARE_R2_SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_KEY")
CLOUDFLARE_R2_BUCKET     = os.getenv("CLOUDFLARE_R2_BUCKET")
CLOUDFLARE_R2_ACCOUNT_ID = os.getenv("CLOUDFLARE_R2_ACCOUNT_ID")

session = boto3.session.Session()
s3_client = session.client(
    "s3",
    region_name="auto",
    endpoint_url=f"https://{CLOUDFLARE_R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=CLOUDFLARE_R2_KEY_ID,
    aws_secret_access_key=CLOUDFLARE_R2_SECRET_KEY,
)


def generate_r2_key(job, filename: str) -> str:
    """
    Build a tenant-scoped storage key so files from different tenants
    are physically separated in the bucket.

    Format: tenant_{id}/job_{id}/{filename}
    """
    tenant = get_current_tenant()
    if not tenant:
        raise Exception("Tenant context missing — cannot generate R2 key.")
    return f"tenant_{tenant.id}/job_{job.id}/{filename}"


def upload_file(file_obj, key: str) -> None:
    """Upload an open file-like object to R2 under the given key."""
    s3_client.upload_fileobj(file_obj, CLOUDFLARE_R2_BUCKET, key)


def generate_signed_url(key: str, expires: int = 3600) -> str:
    """
    Return a pre-signed URL that allows temporary read access to a private file.
    Default expiry: 1 hour.
    """
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": CLOUDFLARE_R2_BUCKET, "Key": key},
        ExpiresIn=expires,
    )