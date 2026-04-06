import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from src.domain.entities import (
    Recommendation,
    PredictRatingRequest,
    PredictRatingResponse,
    MovieCandidate,
    RecommendRequest,
    SyncDataRequest,
    SyncResponse,
    HealthResponse,
)

from src.domain.interfaces import IMovieRecommender
from src.application.services import RecommendationService, DataSyncService
from src.presentation.dependencies import (
    get_model,
    get_recommendation_service,
    get_data_sync_service,
    get_model_storage_service,
)


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _ = get_model()
        logger.info("Модель предзагружена при старте")
    except Exception as e:
        logger.warning(f"Не удалось предзагрузить модель: {e}")
    
    logger.info("API готова к работе")
    yield
    logger.info("Остановка сервера...")


app = FastAPI(
    title="Movie Recommender API",
    description="Вариант 10 ЛР №3: Система рекомендаций фильмов на базе ONNX",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/", response_model=HealthResponse, tags=["Health"])
def health_check(model: IMovieRecommender = Depends(get_model)):
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        model_loaded=model is not None
    )


@app.post("/api/v1/data/sync", response_model=SyncResponse, tags=["Data Management"])
def sync_data(request: SyncDataRequest, sync_service: DataSyncService = Depends(get_data_sync_service)):
    logger.info(f"Запрос синхронизации: {request.remote_path} → {request.local_path}")
    try:
        sync_service.sync_dataset(
            remote_path=request.remote_path,
            local_path=request.local_path,
            force=request.force
        )
        logger.info(f"Данные синхронизированы: {request.local_path}")
        return SyncResponse(
            status="success",
            message=f"Данные синхронизированы: {request.local_path}"
        )
    except Exception as e:
        logger.error(f"Ошибка синхронизации: {type(e).__name__}: {e}")
        return SyncResponse(
            status="error",
            message=f"Ошибка синхронизации: {str(e)}"
        )


@app.post("/api/v1/model/sync", response_model=SyncResponse, tags=["Data Management"])
def sync_model(force: bool = True, sync_service: DataSyncService = Depends(get_model_storage_service), model: IMovieRecommender = Depends(get_model)):
    logger.info(f"Запрос синхронизации модели (force={force})")
    try:
        sync_service.sync_dataset(
            remote_path="models/movie_recommender.onnx",
            local_path=os.getenv("MODEL_PATH", "models/movie_recommender.onnx"),
            force=force
        )
        get_model.cache_clear()
        get_model()
        logger.info("Модель синхронизирована и перезагружена")
        return SyncResponse(
            status="success",
            message="Модель синхронизирована и загружена"
        )
    except Exception as e:
        logger.error(f"Oшибка синхронизации модели: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/movies/predict_rating", response_model=PredictRatingResponse, tags=["Recommendations"])
def predict_rating(request: PredictRatingRequest, service: RecommendationService = Depends(get_recommendation_service)):
    logger.debug(f"Запрос предсказания: user={request.user_id}, movie={request.movie_id}")
    try:
        rating = service.predict_rating(
            user_id=request.user_id,
            movie_id=request.movie_id,
            year=request.year,
            genre=request.genre
        )
        logger.info(f"Предсказание: rating={rating:.2f}")
        return PredictRatingResponse(
            user_id=request.user_id,
            movie_id=request.movie_id,
            predicted_rating=round(rating, 2)
        )
    except Exception as e:
        logger.error(f"Ошибка предсказания: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка предсказания: {str(e)}")


@app.post("/api/v1/movies/recommend", response_model=List[Recommendation], tags=["Recommendations"])
def get_recommendations(request: RecommendRequest, service: RecommendationService = Depends(get_recommendation_service)):
    logger.info(f"Запрос рекомендаций: user={request.user_id}, top_n={request.top_n}")
    try:
        candidates = [
            {
                'movie_id': c.movie_id,
                'year': c.year,
                'genre': c.genre
            }
            for c in request.candidates
        ]

        recommendations = service.get_recommendations(
            user_id=request.user_id,
            candidate_movies=candidates,
            top_n=request.top_n
        )
        logger.info(f"Сгенерировано {len(recommendations)} рекомендаций")
        return recommendations
    except Exception as e:
        logger.error(f"Ошибка генерации рекомендаций: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации рекомендаций: {str(e)}")
