from pathlib import Path
from datetime import datetime, timezone
import boto3
import logging
from botocore.exceptions import ClientError, NoCredentialsError

# module-level singleton — don't build a new client per file, it opens a fresh
# connection pool each time; the watcher calls this once per file all day
_s3_client = None
log = logging.getLogger("aws")

def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")  # no keys here — reads AWS_PROFILE / ~/.aws/credentials / IAM role automatically
    return _s3_client


def upload_to_s3(local_path: Path, bucket: str, key: str) -> str:
    """
    Upload a local file to S3. Returns the s3:// URI on success.
    Raises on failure instead of swallowing it — let the watcher's
    existing `except Exception: log.exception(...)` around on_new_file
    catch and log the full context.
    """

    client = _get_s3_client()
    log.info(f"Uploading {str(local_path)} -> s3://{bucket}/{key}")
    try:
        client.upload_file(str(local_path), bucket, key)
    except NoCredentialsError:
        log.error("No AWS credentials found — check AWS_PROFILE / ~/.aws/credentials")
        raise
    except ClientError as e:
        log.error(f"S3 upload failed: {e.response['Error']['Code']} — {e.response['Error']['Message']}")
        raise

    uri = f"s3://{bucket}/{key}"
    log.info(f"Uploaded: {uri}")
    return uri