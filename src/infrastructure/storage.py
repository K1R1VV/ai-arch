import boto3
from src.domain.interfaces import IDataStorage

class S3Storage(IDataStorage): 
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, bucket: str):
        self.s3 = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        self.bucket = bucket

    def download_file(self, remote_path: str, local_path: str) -> None:
        print(f"[Storage] Скачивание {remote_path} -> {local_path}...")
        self.s3.download_file(self.bucket, remote_path, local_path)

    def upload_file(self, local_path: str, remote_path: str) -> None:
        print(f"[Storage] Загрузка {local_path} -> {remote_path}...")
        self.s3.upload_file(local_path, self.bucket, remote_path)