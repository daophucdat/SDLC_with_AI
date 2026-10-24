"""S3 / MinIO adapter (ADR-06, SEC-03). boto3 is synchronous, so calls run in a worker thread."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


class S3DocumentStorage:
    def __init__(
        self,
        *,
        bucket: str,
        endpoint: str | None,
        region: str,
        access_key: str | None,
        secret_key: str | None,
        sse: str | None,
    ) -> None:
        self._bucket, self._sse = bucket, sse
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=10,
            ),
        )

    def _extra(self) -> dict:
        extra = {"ContentType": "application/pdf"}
        if self._sse:
            extra["ServerSideEncryption"] = self._sse
        return extra

    async def put_file(self, key: str, local_path: str, size_bytes: int) -> None:
        await asyncio.to_thread(self._client.upload_file, local_path, self._bucket, key, ExtraArgs=self._extra())

    async def download_to(self, key: str, local_path: str) -> None:
        await asyncio.to_thread(self._client.download_file, self._bucket, key, local_path)

    def _delete_all_versions(self, key: str) -> None:
        # The bucket is versioned (backups, REL-02). A plain DeleteObject only adds a delete marker and the PDF would
        # stay recoverable — SEC-06 requires it to be gone, so every version and delete marker is removed.
        paginator = self._client.get_paginator("list_object_versions")
        found = False
        for page in paginator.paginate(Bucket=self._bucket, Prefix=key):
            items = [
                {"Key": v["Key"], "VersionId": v["VersionId"]}
                for v in page.get("Versions", []) + page.get("DeleteMarkers", [])
                if v["Key"] == key
            ]
            if items:
                found = True
                self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": items, "Quiet": True})
        if not found:  # unversioned bucket (or nothing there): plain delete is idempotent
            self._client.delete_object(Bucket=self._bucket, Key=key)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._delete_all_versions, key)

    async def size(self, key: str) -> int | None:
        try:
            head = await asyncio.to_thread(self._client.head_object, Bucket=self._bucket, Key=key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                return None
            raise
        return int(head["ContentLength"])

    async def read_range(self, key: str, start: int, end: int) -> AsyncIterator[bytes]:
        obj = await asyncio.to_thread(
            self._client.get_object, Bucket=self._bucket, Key=key, Range=f"bytes={start}-{end}"
        )
        body = obj["Body"]
        try:
            while chunk := await asyncio.to_thread(body.read, 64 * 1024):
                yield chunk
        finally:
            body.close()

    async def health(self) -> bool:
        try:
            await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)
            return True
        except (BotoCoreError, ClientError):
            return False
