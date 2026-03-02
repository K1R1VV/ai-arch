import os
import sys
from src.infrastructure.storage import S3Storage
from src.application.services import DataSyncService, RecommendationService

def main():
    s3_config = {
        "endpoint_url": os.getenv("MINIO_ENDPOINT"),
        "access_key": os.getenv("MINIO_ACCESS_KEY"),
        "secret_key": os.getenv("MINIO_SECRET_KEY"),
        "bucket": os.getenv("MINIO_BUCKET", "datasets")
    }

    storage = S3Storage(**s3_config)

    sync_service = DataSyncService(storage=storage)
    try:
        sync_service.sync_dataset(
            remote_path="data/ratings.csv",
            local_path="data/ratings.csv"
        )
    except Exception as e:
        print(f"[Warning] Не удалось синхронизировать данные: {e}")
        print("Продолжаем работу с локальными файлами...")

    rec_service = RecommendationService(data_path="data/ratings.csv")
    user_id = 1
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
        except ValueError:
            print("Invalid user_id. Using default 1.")
            
    print(f"Running recommendations for User ID: {user_id}")
    results = rec_service.get_recommendations(user_id)

    if not results:
        print("No recommendations found.")
    else:
        for rec in results:
            print(f"Movie ID: {rec.movie_id}, Score: {rec.predicted_score}")


if __name__ == "__main__":
    main()