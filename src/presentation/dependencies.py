import os
import logging
from pathlib import Path
from functools import lru_cache
from typing import Generator
from fastapi import Depends
import mlflow

from src.infrastructure.onnx_model import ONNXMovieRecommender
from src.application.services import RecommendationService
from src.domain.interfaces import IMovieRecommender


logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


@lru_cache(maxsize=1)
def get_model() -> IMovieRecommender:
    model_name = "movie_recommender"
    model_alias = "production"
    model_uri = f"models:/{model_name}@{model_alias}"
    
    logger.info(f"[Model] Загрузка модели из MLflow Registry: {model_uri}")
    
    try:
        model_dir = mlflow.artifacts.download_artifacts(artifact_uri=model_uri)
        model_path = os.path.join(model_dir, "model.onnx")
        logger.info(f"Модель скачана из MLflow: {model_path}")
        
    except Exception as e:
        logger.warning(f"Ошибка загрузки из MLflow: {type(e).__name__}: {e}")
    
    return ONNXMovieRecommender(model_path)


def get_recommendation_service(model: IMovieRecommender = Depends(get_model)) -> RecommendationService:
    return RecommendationService(model=model)