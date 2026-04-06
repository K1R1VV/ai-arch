import os
import logging
from pathlib import Path
from functools import lru_cache
from typing import Generator
from fastapi import Depends
from src.infrastructure.onnx_model import ONNXMovieRecommender
from src.infrastructure.storage import S3Storage
from src.application.services import RecommendationService, DataSyncService
from src.domain.interfaces import IMovieRecommender, IDataStorage


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_model() -> IMovieRecommender:
    model_path = os.getenv("MODEL_PATH", "models/movie_recommender.onnx")

    if not Path(model_path).exists():
        logger.warning(f"Модель не найдена: {model_path}. Скачивание из MinIO...")
        try:
            Path(model_path).parent.mkdir(parents=True, exist_ok=True)

            storage = S3Storage(
                endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
                access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                bucket="models"
            )
            
            storage.download_file(
                remote_path="models/movie_recommender.onnx",
                local_path=model_path
            )
            
            logger.info(f"Модель успешно скачана: {model_path}")
            
        except Exception as e:
            logger.error(f"Не удалось скачать модель: {type(e).__name__}: {e}")
            raise

    return ONNXMovieRecommender(model_path)


@lru_cache(maxsize=1)
def get_storage_factory():
    def _create_storage(bucket: str = "datasets") -> IDataStorage:
        return S3Storage(
            endpoint_url=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            bucket=bucket
        )
    return _create_storage


def get_recommendation_service(model: IMovieRecommender = Depends(get_model)) -> RecommendationService:
    if model is None:
        model = get_model()
    return RecommendationService(model=model)


def get_data_sync_service(bucket: str = "datasets") -> DataSyncService:
    storage_factory = get_storage_factory()
    storage = storage_factory(bucket=bucket)
    return DataSyncService(storage=storage)


def get_model_storage_service() -> DataSyncService:
    return get_data_sync_service(bucket="models")
