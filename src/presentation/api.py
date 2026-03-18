import os
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from src.infrastructure.onnx_model import ONNXMovieRecommender
from src.application.services import DataSyncService
from src.infrastructure.storage import S3Storage
from src.domain.entities import Recommendation


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] API инициализирована.")
    yield
    print("[Shutdown] Остановка сервера...")

app = FastAPI(title="Movie Recommender API", lifespan=lifespan)


class RequestModel(BaseModel):
    user_id: int


class SyncDataRequest(BaseModel):
    remote_path: str = "data/ratings.csv"
    local_path: str = "data/ratings.csv"


class SyncDataResponse(BaseModel):
    status: str
    message: str


class RecommendRequest(BaseModel):
    user_id: int = Field(..., example=1, description="ID пользователя")
    top_n: Optional[int] = Field(3, ge=1, le=10, description="Количество рекомендаций")


class PredictRequest(BaseModel):
    user_id: int = Field(..., example=1, description="ID пользователя")
    movie_id: int = Field(..., example=101, description="ID фильма")
    year: Optional[int] = Field(2023, description="Год выпуска фильма")


class MovieCandidate(BaseModel):
    movie_id: int
    year: Optional[int] = 2023


class RecommendWithCandidatesRequest(BaseModel):
    user_id: int
    candidates: List[MovieCandidate]
    top_n: Optional[int] = 3


class SyncResponse(BaseModel):
    status: str
    message: str
    files_synced: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool = False


_model_instance = None

def get_model() -> Optional[ONNXMovieRecommender]:
    global _model_instance
    return _model_instance

def load_model() -> ONNXMovieRecommender:
    global _model_instance
    model_path = "models/movie_recommender.onnx"
    print(f"[Model] Загрузка модели из {model_path}...")
    _model_instance = ONNXMovieRecommender(model_path)
    return _model_instance


@app.get("/", response_model=HealthResponse, tags=["Health"])
def health_check():
    model_loaded = get_model() is not None
    return HealthResponse(
        status="healthy",
        version="3.0.0",
        model_loaded=model_loaded
    )


@app.post("/api/v1/data/sync", response_model=SyncDataResponse)
def sync_data(request: SyncDataRequest):
    """Синхронизирует данные с MinIO вручную"""
    try:
        s3_config = {
            "endpoint_url": os.getenv("MINIO_ENDPOINT"),
            "access_key": os.getenv("MINIO_ACCESS_KEY"),
            "secret_key": os.getenv("MINIO_SECRET_KEY"),
            "bucket": os.getenv("MINIO_BUCKET", "datasets")
        }
        storage = S3Storage(**s3_config)
        sync_service = DataSyncService(storage=storage)
        sync_service.sync_dataset(
            remote_path=request.remote_path,
            local_path=request.local_path
        )
        return SyncDataResponse(
            status="success",
            message=f"Данные синхронизированы: {request.local_path}"
        )
    except Exception as e:
        return SyncDataResponse(
            status="error",
            message=f"Ошибка синхронизации: {str(e)}"
        )


@app.post("/api/v1/model/sync", response_model=SyncResponse, tags=["Data Management"])
def sync_model():
    """Синхронизировать модель с удалённым хранилищем (MinIO)."""
    try:
        s3_config = {
            "endpoint_url": os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
            "access_key": os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            "secret_key": os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        }
        storage = S3Storage(bucket="models", **s3_config)
        sync_service = DataSyncService(storage=storage)
        sync_service.sync_dataset(
            remote_path="movie_recommender.onnx",
            local_path="models/movie_recommender.onnx"
        )
        load_model()
        return SyncResponse(status="success", message="Модель синхронизирована и загружена")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/predict", tags=["Recommendations"])
def predict_rating(request: PredictRequest):
    model = get_model()
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Модель не загружена. Выполните синхронизацию: POST /api/v1/model/sync"
        )
    
    try:
        rating = model.predict_rating(
            user_id=request.user_id,
            movie_id=request.movie_id,
            year=request.year
        )
        return {
            "user_id": request.user_id,
            "movie_id": request.movie_id,
            "predicted_rating": rating
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка предсказания: {str(e)}")


@app.post("/api/v1/recommend", response_model=List[Recommendation], tags=["Recommendations"])
def get_recommendations(request: RecommendWithCandidatesRequest):
    model = get_model()
    if not model:
        raise HTTPException(
            status_code=503,
            detail="Модель не загружена. Выполните синхронизацию: POST /api/v1/model/sync"
        )
    
    try:
        candidates = [{'movie_id': c.movie_id, 'year': c.year} for c in request.candidates]
        recommendations = model.recommend(
            user_id=request.user_id,
            candidate_movies=candidates,
            top_n=request.top_n
        )
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации рекомендаций: {str(e)}")