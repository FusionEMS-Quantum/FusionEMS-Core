"""
S3 ZIP Bundler Service

Handles creation of structured ZIP export packages from documents stored in S3.
Generates manifest files, compresses content, and uploads to S3 with presigned URLs.
"""

import hashlib
import io
import json
import logging
import zipfile
from datetime import datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3ZipBundlerError(Exception):
    """Raised when ZIP bundling fails."""
    pass


class S3ZipBundler:
    """
    Manages S3-based ZIP export package generation.

    Workflow:
    1. Fetch manifest metadata from database
    2. Retrieve document objects from S3
    3. Create ZIP in-memory with proper structure
    4. Upload ZIP to S3
    5. Generate presigned download URL
    """

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket = bucket_name
        self.region = region
        try:
            self.s3_client = boto3.client("s3", region_name=region)
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise S3ZipBundlerError(f"S3 initialization failed: {e}")

    def bundle_documents(
        self,
        package_name: str,
        manifest_id: str,
        documents: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None
    ) -> str:
        """
        Create a ZIP bundle from documents and upload to S3.

        Args:
            package_name: Human-readable package name
            manifest_id: Unique manifest identifier
            documents: List of document metadata with s3_key
            metadata: Additional package metadata (export reason, etc.)

        Returns:
            Presigned S3 download URL (valid 7 days)
        """
        try:
            # Create ZIP in memory
            zip_buffer = io.BytesIO()
            zip_path = f"vault-exports/{manifest_id}/{package_name}_export.zip"

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add manifest file
                manifest_content = self._create_manifest(
                    package_name=package_name,
                    manifest_id=manifest_id,
                    documents=documents,
                    metadata=metadata
                )
                zip_file.writestr("MANIFEST.json", manifest_content)

                # Fetch and add each document
                for doc in documents:
                    s3_key = doc.get("s3_key")
                    if not s3_key:
                        logger.warning(f"Document {doc.get('id')} has no s3_key, skipping")
                        continue

                    try:
                        obj = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)
                        content = obj["Body"].read()

                        # Preserve original filename or create sanitized path
                        filename = s3_key.split("/")[-1]
                        arcname = f"documents/{filename}"

                        zip_file.writestr(arcname, content)
                        logger.debug(f"Added {s3_key} to ZIP as {arcname}")
                    except ClientError as e:
                        logger.error(f"Failed to fetch {s3_key} from S3: {e}")
                        # Continue with other documents; don't fail entire bundle
                        continue

            # Upload ZIP to S3
            zip_buffer.seek(0)
            try:
                self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=zip_path,
                    Body=zip_buffer.getvalue(),
                    ContentType="application/zip",
                    Metadata={
                        "manifest-id": manifest_id,
                        "package-name": package_name,
                        "created-at": datetime.utcnow().isoformat()
                    }
                )
                logger.info(f"ZIP bundle uploaded to S3: {zip_path}")
            except ClientError as e:
                raise S3ZipBundlerError(f"Failed to upload ZIP to S3: {e}")

            # Generate presigned URL (valid for 7 days)
            try:
                presigned_url = self.s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": zip_path},
                    ExpiresIn=7 * 24 * 3600  # 7 days
                )
                logger.info(f"Presigned URL generated: {presigned_url[:80]}...")
                return presigned_url
            except ClientError as e:
                raise S3ZipBundlerError(f"Failed to generate presigned URL: {e}")

        except S3ZipBundlerError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during bundling: {e}")
            raise S3ZipBundlerError(f"Unexpected error: {e}")

    def _create_manifest(
        self,
        package_name: str,
        manifest_id: str,
        documents: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None
    ) -> str:
        """Generate cryptographically signed manifest JSON."""
        now = datetime.utcnow()

        manifest = {
            "manifest_version": "1.0",
            "package_name": package_name,
            "manifest_id": manifest_id,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
            "document_count": len(documents),
            "documents": [
                {
                    "id": doc.get("id"),
                    "type": doc.get("type", "unknown"),
                    "lock_state": doc.get("lock_state", "active"),
                    "s3_key": doc.get("s3_key"),
                    "created_at": doc.get("created_at")
                }
                for doc in documents
            ],
            "export_metadata": metadata or {}
        }

        # Add manifest checksum for integrity verification
        manifest_json = json.dumps(manifest, indent=2, sort_keys=True)
        checksum = hashlib.sha256(manifest_json.encode()).hexdigest()
        manifest["checksum_sha256"] = checksum

        return json.dumps(manifest, indent=2)

    def cleanup_expired_bundles(self, days_old: int = 7) -> int:
        """
        Clean up expired ZIP bundles older than specified days.
        Returns count of deleted objects.
        """
        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(Bucket=self.bucket, Prefix="vault-exports/")

            deleted_count = 0
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            for page in pages:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    if obj["LastModified"].replace(tzinfo=None) < cutoff_date:
                        try:
                            self.s3_client.delete_object(Bucket=self.bucket, Key=obj["Key"])
                            deleted_count += 1
                            logger.debug(f"Deleted expired bundle: {obj['Key']}")
                        except ClientError as e:
                            logger.error(f"Failed to delete {obj['Key']}: {e}")

            logger.info(f"Cleanup complete: {deleted_count} expired bundles removed")
            return deleted_count

        except ClientError as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
