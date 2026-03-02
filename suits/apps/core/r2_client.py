import boto3
import os

CLOUDFLARE_R2_KEY_ID = os.getenv("CLOUDFLARE_R2_KEY_ID")
CLOUDFLARE_R2_SECRET_KEY = os.getenv("CLOUDFLARE_R2_SECRET_KEY")
CLOUDFLARE_R2_BUCKET = os.getenv("CLOUDFLARE_R2_BUCKET")
CLOUDFLARE_R2_ACCOUNT_ID = os.getenv("CLOUDFLARE_R2_ACCOUNT_ID")

session = boto3.session.Session()
s3_client = session.client(
    "s3",
    region_name="auto",
    endpoint_url=f"https://{CLOUDFLARE_R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=CLOUDFLARE_R2_KEY_ID,
    aws_secret_access_key=CLOUDFLARE_R2_SECRET_KEY
)

def generate_r2_key(job, filename):
    """
    Tenant-safe R2 key generator.
    """
    tenant = get_current_tenant()
    if not tenant:
        raise Exception("Tenant context missing")

    return f"tenant_{tenant.id}/job_{job.id}/{filename}"


def upload_file(file_obj, key):
    s3_client.upload_fileobj(
        file_obj,
        CLOUDFLARE_R2_BUCKET,
        key
    )

def generate_signed_url(key, expires=3600):
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": CLOUDFLARE_R2_BUCKET, "Key": key},
        ExpiresIn=expires
    )
    return url