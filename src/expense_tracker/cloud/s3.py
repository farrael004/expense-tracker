import boto3
from botocore.exceptions import ClientError

from expense_tracker.cloud.base import CloudStorageProvider


class S3Provider(CloudStorageProvider):
    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_region: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix.rstrip("/") + "/" if prefix else ""
        self._client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )

    def _full_key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def upload(self, key: str, data: str) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=self._full_key(key),
            Body=data.encode("utf-8"),
            ContentType="application/json",
        )

    def download(self, key: str) -> str | None:
        try:
            response = self._client.get_object(
                Bucket=self._bucket,
                Key=self._full_key(key),
            )
            return response["Body"].read().decode("utf-8")
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return None
            raise
