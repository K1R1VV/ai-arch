import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from src.infrastructure.onnx_model import ONNXMovieRecommender
from src.application.services import DataSyncService, RecommendationService
from src.infrastructure.storage import S3Storage
from src.domain.entities import Recommendation


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


class PredictRatingRequest(BaseModel):
    user_id: int = Field(..., example=123, description="ID пользователя")
    movie_id: int = Field(..., example=456, description="ID фильма")
    year: Optional[int] = Field(2023, description="Год выпуска фильма")
    genre: Optional[str] = Field("Action", description="Жанр фильма")


class PredictRatingResponse(BaseModel):
    user_id: int
    movie_id: int
    predicted_rating: float = Field(..., example=4.5, description="Предсказанная оценка [1.0-5.0]")


class MovieCandidate(BaseModel):
    movie_id: int
    year: Optional[int] = 2023
    genre: Optional[str] = "Action"


class RecommendRequest(BaseModel):
    user_id: int = Field(..., example=1, description="ID пользователя")
    candidates: List[MovieCandidate] = Field(..., description="Список кандидатов для рекомендации")
    top_n: Optional[int] = Field(3, ge=1, le=10, description="Количество рекомендаций")


class SyncDataRequest(BaseModel):
    remote_path: str = Field("data/ratings.csv", description="Путь на удаленном хранилище")
    local_path: str = Field("data/ratings.csv", description="Локальный путь")
    force: bool = Field(True, description="Перезаписать существующий файл") 


class SyncResponse(BaseModel):
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool = False
    model_path: Optional[str] = None


_model_instance: Optional[ONNXMovieRecommender] = None
_model_path = "models/movie_recommender.onnx"


def _get_s3_config(bucket: str = "datasets") -> dict:
    return {
        "endpoint_url": os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        "bucket": os.getenv(f"MINIO_BUCKET", bucket)
    }


def get_storage(bucket: str = "datasets") -> S3Storage:
    config = _get_s3_config(bucket=bucket)
    return S3Storage(**config)


def get_model() -> Optional[ONNXMovieRecommender]:
    global _model_instance
    return _model_instance


def _sync_model_from_storage() -> bool:
    try:
        storage = get_storage(bucket="models")
        sync_service = DataSyncService(storage=storage)
        sync_service.sync_dataset(
            remote_path="models/movie_recommender.onnx",
            local_path=_model_path,
            force=True
        )
        return True
    except Exception as e:
        logger.error(f"[Model Sync] Ошибка синхронизации: {e}")
        return False


def load_model() -> ONNXMovieRecommender:
    global _model_instance
    logger.info(f"[Model] Загрузка модели из {_model_path}...")
    _model_instance = ONNXMovieRecommender(_model_path)
    return _model_instance


async def _auto_load_model_on_startup():
    logger.info("[Startup] Инициализация модели...")
    
    try:
        if os.path.exists(_model_path):
            load_model()
            logger.info(f"[Startup] Модель загружена из {_model_path}")
            return
    except Exception as e:
       logger.error(f"[Startup] Ошибка загрузки локальной модели: {type(e).__name__}: {e}")

    try:
        logger.info(f"[Startup] Модель не найдена локально. Попытка синхронизации...")
        if _sync_model_from_storage():
            load_model()
            logger.info(f"[Startup] Модель синхронизирована и загружена")
            return
    except Exception as e:
        logger.error(f"[Startup] Ошибка синхронизации модели: {type(e).__name__}: {e}")
    
    logger.info(f"[Startup] Модель не загружена. Она будет загружена при первом запросе к /api/v1/model/sync")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _auto_load_model_on_startup()
    logger.info("[Startup] API готова к работе")
    
    yield

    logger.info("[Shutdown] Остановка сервера...")


app = FastAPI(
    title="Movie Recommender API",
    description="Вариант 10 ЛР №3: Система рекомендаций фильмов на базе ONNX",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/", response_model=HealthResponse, tags=["Health"])
def health_check():
    model = get_model()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        model_loaded=model is not None,
        model_path=_model_path if model else None
    )


@app.post("/api/v1/data/sync", response_model=SyncResponse, tags=["Data Management"])
def sync_data(request: SyncDataRequest):
    try:
        storage = get_storage(bucket="datasets")
        sync_service = DataSyncService(storage=storage)

        sync_service.sync_dataset(
            remote_path=request.remote_path,
            local_path=request.local_path,
            force=request.force
        )
        return SyncResponse(
            status="success",
            message=f"Данные синхронизированы: {request.local_path}"
        )
    except Exception as e:
        return SyncResponse(
            status="error",
            message=f"Ошибка синхронизации: {str(e)}"
        )


@app.post("/api/v1/model/sync", response_model=SyncResponse, tags=["Data Management"])
def sync_model():
    try:
        if _sync_model_from_storage():
            load_model()
            return SyncResponse(
                status="success",
                message="Модель синхронизирована и загружена"
            )
        else:
            raise HTTPException(status_code=500, detail="Не удалось синхронизировать модель")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/movies/predict_rating", response_model=PredictRatingResponse, tags=["Recommendations"])
def predict_rating(request: PredictRatingRequest):
    model = get_model()
    if not model:
        try:
            if os.path.exists(_model_path):
                load_model()
                model = get_model()
            else:
                _sync_model_from_storage()
                load_model()
                model = get_model()
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Модель не найдена: {str(e)}. Выполните синхронизацию: POST /api/v1/model/sync"
            )
        except PermissionError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Нет прав доступа к модели: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[API] Ошибка загрузки модели: {type(e).__name__}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Внутренняя ошибка загрузки модели: {type(e).__name__}"
            )
    
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Модель не загружена. Выполните синхронизацию: POST /api/v1/model/sync"
        )
    
    try:
        rating = model.predict_rating(
            user_id=request.user_id,
            movie_id=request.movie_id,
            year=request.year,
            genre=request.genre
        )
        return PredictRatingResponse(
            user_id=request.user_id,
            movie_id=request.movie_id,
            predicted_rating=round(rating, 2)
        )
    except Exception as e:
        logger.error(f"[API] Ошибка предсказания: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка предсказания: {str(e)}")


@app.post("/api/v1/movies/recommend", response_model=List[Recommendation], tags=["Recommendations"])
def get_recommendations(request: RecommendRequest):
    model = get_model()
    
    if not model:
        try:
            if os.path.exists(_model_path):
                load_model()
                model = get_model()
            else:
                _sync_model_from_storage()
                load_model()
                model = get_model()
        except FileNotFoundError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Модель не найдена: {str(e)}"
            )
        except Exception as e:
            logger.error(f"[API] Ошибка загрузки модели: {type(e).__name__}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Внутренняя ошибка загрузки модели: {type(e).__name__}"
            )
    
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Модель не загружена. Выполните синхронизацию: POST /api/v1/model/sync"
        )
    
    try:
        service = RecommendationService(model=model)
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
        return recommendations
    except Exception as e:
        logger.error(f"[API] Ошибка генерации рекомендаций: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации рекомендаций: {str(e)}")