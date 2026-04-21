# src/presentation/tasks.py
"""
Модуль задач Celery для асинхронного инференса.

Использует ленивую инициализацию сервиса: модель загружается из MLflow
только в момент выполнения задачи, а не при старте воркера.
"""

from typing import Optional
from src.application.services import RecommendationService
from src.presentation.dependencies import get_model, reload_model
from src.presentation.celery_app import celery_app
from src.config.genre_encoding import encode_genre
from src.infrastructure.onnx_model import UninitializedRecommender
import logging
import time

logger = logging.getLogger(__name__)

_service_instance: Optional[RecommendationService] = None
_last_init_error: Optional[str] = None


def _get_service() -> RecommendationService:
    global _service_instance, _last_init_error

    if _service_instance is not None:
        return _service_instance
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"[Worker] Попытка инициализации сервиса (попытка {attempt + 1}/{max_retries})...")
            model = get_model()

            if isinstance(model, UninitializedRecommender):
                _last_init_error = model.error_message
                logger.warning(f"[Worker] Модель не инициализирована: {model.error_message}")
                break
            
            _service_instance = RecommendationService(model=model)
            logger.info("[Worker] Сервис успешно инициализирован")
            return _service_instance
            
        except Exception as e:
            _last_init_error = str(e)
            logger.warning(f"[Worker] Ошибка инициализации (попытка {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                logger.error(f"[Worker] Не удалось инициализировать сервис после {max_retries} попыток")

    fallback_model = UninitializedRecommender(_last_init_error or "Failed to initialize model")
    return RecommendationService(model=fallback_model)


@celery_app.task(
    name="recommend_for_user_task",
    bind=True,
    autoretry_for=(RuntimeError,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    retry_backoff=True
)
def recommend_for_user_task(self, user_id: int, candidate_movies: list, top_n: int = 3) -> dict:
    logger.info(f"[Celery] Задача рекомендаций: user={user_id}, movies={len(candidate_movies)}")
    service = _get_service()
    model = service.model
    if isinstance(model, UninitializedRecommender):
        raise RuntimeError(f"Model not available: {model.error_message}")

    encoded_candidates = []
    for c in candidate_movies:
        genre_str = c.get("genre", "Action")
        encoded_candidates.append({
            "movie_id": c["movie_id"],
            "year": c.get("year", 2023),
            "genre_encoded": encode_genre(genre_str)
        })

    recommendations = service.get_recommendations(user_id, encoded_candidates, top_n)

    result = {
        "recommendations": [
            {
                "movie_id": rec.movie_id,
                "predicted_score": rec.predicted_score,
                "reason": rec.reason
            }
            for rec in recommendations
        ]
    }
    
    logger.info(f"[Celery] Задача выполнена: {len(result['recommendations'])} рекомендаций")
    return result 


@celery_app.task(
    name="predict_rating_task",
    bind=True,
    autoretry_for=(RuntimeError,),
    retry_kwargs={'max_retries': 3, 'countdown': 5},
    retry_backoff=True
)
def predict_rating_task(self, user_id: int, movie_id: int, year: int = 2023, genre: str = "Action") -> dict:
    logger.info(f"[Celery] Предсказание рейтинга: user={user_id}, movie={movie_id}")
    service = _get_service()
    model = service.model
    if isinstance(model, UninitializedRecommender):
        raise RuntimeError(f"Model not available: {model.error_message}")
    genre_encoded = encode_genre(genre)
    score = service.predict_rating(user_id, movie_id, year, genre_encoded)
    
    result = {
        "user_id": user_id,
        "movie_id": movie_id,
        "predicted_rating": round(score, 2)
    }
    
    logger.debug(f"[Celery] Предсказание: {score:.2f}")
    return result