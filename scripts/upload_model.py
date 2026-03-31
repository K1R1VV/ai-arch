import os
from src.infrastructure.storage import S3Storage


def upload(bucket: str='models', local_path: str="models/movie_recommender.onnx", remote_path: str="models/movie_recommender.onnx"):
    storage = S3Storage(
        endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        bucket=bucket
    )
    storage.upload_file(local_path=local_path, remote_path=remote_path)
    print("Модель обновлена в хранилище")


if __name__ == "__main__":
    upload()