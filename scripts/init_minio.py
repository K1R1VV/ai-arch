import boto3
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from botocore.exceptions import ClientError


def upload_data():
    data_path = Path("data/ratings.csv")
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        'user_id': np.random.randint(1, 100, 500),
        'movie_id': np.random.randint(1, 200, 500),
        'genre': np.random.choice(['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror'], 500),
        'year': np.random.randint(1990, 2024, 500),
        'rating': np.random.uniform(1.0, 5.0, 500)
    }
    df = pd.DataFrame(data)
    df.to_csv(data_path, index=False)
    print(f"[Init] Создан локальный файл {data_path}")

    s3 = boto3.client(
        's3',
        endpoint_url=os.getenv("MINIO_ENDPOINT", 'http://localhost:9000'),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", 'minioadmin'),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", 'minioadmin')
    )
    bucket = os.getenv("MINIO_BUCKET", "datasets")
    key = "data/ratings.csv"

    try:
        s3.head_bucket(Bucket=bucket)
        print(f"[Init] Бакет '{bucket}' уже существует.")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404' or error_code == 'NoSuchBucket':
            print(f"[Init] Бакет '{bucket}' не найден. Создаю...")
            s3.create_bucket(Bucket=bucket)
            print(f"[Init] Бакет '{bucket}' успешно создан.")
        else:
            raise

    print(f"[Init] Загрузка '{key}' в бакет '{bucket}'...")
    s3.upload_file(str(data_path), bucket, key)
    print("[Init] Успешно! Данные v1.0 загружены в MinIO.")

    bucket_2 = os.getenv("MINIO_MODELS_BUCKET", "models")
    model_local_path = "models/movie_recommender.onnx"
    try:
        s3.head_bucket(Bucket=bucket_2)
        print(f"[Init] Бакет '{bucket_2}' уже существует.")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404' or error_code == 'NoSuchBucket':
            print(f"[Init] Бакет '{bucket_2}' не найден. Создаю...")
            s3.create_bucket(Bucket=bucket_2)
            print(f"[Init] Бакет '{bucket_2}' успешно создан.")
        else:
            raise


if __name__ == "__main__":
    upload_data()