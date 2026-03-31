import os
from functools import lru_cache
from typing import Generator
from fastapi import Depends
from src.infrastructure.onnx_model import ONNXMovieRecommender
from src.infrastructure.storage import S3Storage
from src.application.services import RecommendationService, DataSyncService
from src.domain.interfaces import IMovieRecommender, IDataStorage


@lru_cache(maxsize=1)
def get_model() -> IMovieRecommender:
    model_path = os.getenv("MODEL_PATH", "models/movie_recommender.onnx")
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
    return RecommendationService(model=model)


def get_data_sync_service(bucket: str = "datasets") -> DataSyncService:
    storage_factory = get_storage_factory()
    storage = storage_factory(bucket=bucket)
    return DataSyncService(storage=storage)


def get_model_storage_service() -> DataSyncService:
    return get_data_sync_service(bucket="models")