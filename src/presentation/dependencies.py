import os
import logging
from pathlib import Path
from functools import lru_cache
from fastapi import Depends
import mlflow
from mlflow.exceptions import RestException
from typing import Optional

from src.infrastructure.onnx_model import ONNXMovieRecommender, UninitializedRecommender
from src.application.services import RecommendationService
from src.domain.interfaces import IMovieRecommender

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

_model_load_attempted = False
_model_load_error: Optional[str] = None


@lru_cache(maxsize=1)
def get_model() -> IMovieRecommender:
    global _model_load_attempted, _model_load_error
    _model_load_attempted = True
    
    model_name = "movie_recommender"
    model_alias = "production"
    model_uri = f"models:/{model_name}@{model_alias}"
    local_model_path = os.getenv("MODEL_PATH", "models/movie_recommender.onnx")
    
    logger.info(f"[Model] Загрузка модели из MLflow Registry: {model_uri}")
    
    try:
        model_dir = mlflow.artifacts.download_artifacts(artifact_uri=model_uri)
        model_path = os.path.join(model_dir, "model.onnx")
        logger.info(f"Модель скачана из MLflow: {model_path}")
        return ONNXMovieRecommender(model_path)
        
    except (RestException, Exception) as e:
        logger.warning(f"Ошибка загрузки из MLflow: {type(e).__name__}: {e}")
        logger.info(f"Fallback: проверка локальной копии: {local_model_path}")
        
        if Path(local_model_path).exists():
            logger.info(f"Загружена локальная модель: {local_model_path}")
            return ONNXMovieRecommender(local_model_path)

        _model_load_error = f"Model not found: MLflow alias '{model_alias}' not set, local path '{local_model_path}' does not exist"
        logger.error(f"{_model_load_error}")
        return UninitializedRecommender(_model_load_error)


def get_recommendation_service(
    model: IMovieRecommender = Depends(get_model)
) -> RecommendationService:
    return RecommendationService(model=model)


def check_model_status() -> dict:
    global _model_load_attempted, _model_load_error
    
    if not _model_load_attempted:
        _ = get_model()
    
    model = get_model()
    return {
        "model_loaded": getattr(model, "is_loaded", False),
        "model_type": type(model).__name__,
        "error": _model_load_error if not getattr(model, "is_loaded", False) else None
    }


def reload_model() -> IMovieRecommender:
    global _model_load_attempted, _model_load_error
    get_model.cache_clear()
    _model_load_attempted = False
    _model_load_error = None
    return get_model()


def get_service(model: Optional[IMovieRecommender] = None) -> RecommendationService:
    if model is None:
        model = get_model()
    return RecommendationService(model=model)