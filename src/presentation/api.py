import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, BackgroundTasks, status
from celery.result import AsyncResult

from src.domain.entities import (
    Recommendation,
    PredictRatingRequest,
    PredictRatingResponse,
    MovieCandidate,
    RecommendRequest,
    HealthResponse,
    TaskResponse,
    TaskResultResponse
)

from src.domain.interfaces import IMovieRecommender
from src.application.services import RecommendationService
from src.presentation.dependencies import (
    get_model,
    get_service
)
from src.presentation.celery_app import celery_app
from src.presentation.tasks import recommend_for_user_task, predict_rating_task


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):   
    logger.info("API готова к работе")
    yield
    logger.info("Остановка сервера...")


app = FastAPI(
    title="Movie Recommender API",
    description="Вариант 10 ЛР №5: CI/CD и управление жизненным циклом модели",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/api/v1/movies/recommend_for_user", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Recommendations Async"])
def recommend_for_user_async(
    request: RecommendRequest,
    background_tasks: BackgroundTasks
):
    logger.info(f"Запрос асинхронных рекомендаций: user={request.user_id}")
    
    candidates_serialized = [
        {
            'movie_id': c.movie_id,
            'year': c.year,
            'genre': c.genre
        }
        for c in request.candidates
    ]
    
    task = recommend_for_user_task.delay(
        user_id=request.user_id,
        candidate_movies=candidates_serialized,
        top_n=request.top_n
    )
    
    logger.info(f"Задача создана: task_id={task.id}")
    return TaskResponse(task_id=task.id)


@app.get("/api/v1/movies/results/{task_id}", response_model=TaskResultResponse, tags=["Recommendations Async"])
def get_recommendation_results(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.ready():
        if task_result.successful():
            logger.info(f"Задача {task_id} выполнена успешно")
            return TaskResultResponse(
                task_id=task_id,
                status="SUCCESS",
                result=task_result.result
            )
        else:
            logger.error(f"Задача {task_id} завершилась с ошибкой: {task_result.result}")
            return TaskResultResponse(
                task_id=task_id,
                status="FAILURE",
                error=str(task_result.result)
            )
    
    logger.debug(f"Задача {task_id} в статусе: {task_result.status}")
    return TaskResultResponse(
        task_id=task_id,
        status=task_result.status
    )


@app.post("/api/v1/movies/predict_rating_async", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED, tags=["Recommendations Async"])
def predict_rating_async(
    request: PredictRatingRequest,
):
    logger.debug(f"Запрос асинхронного предсказания: user={request.user_id}, movie={request.movie_id}")
    
    task = predict_rating_task.delay(
        user_id=request.user_id,
        movie_id=request.movie_id,
        year=request.year,
        genre=request.genre
    )
    
    return TaskResponse(task_id=task.id)