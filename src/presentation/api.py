import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from src.infrastructure.storage import S3Storage
from src.application.services import DataSyncService, RecommendationService
from src.domain.entities import Recommendation

@asynccontextmanager
async def lifespan(app: FastAPI):
    s3_config = {
        "endpoint_url": os.getenv("MINIO_ENDPOINT"),
        "access_key": os.getenv("MINIO_ACCESS_KEY"),
        "secret_key": os.getenv("MINIO_SECRET_KEY"),
        "bucket": os.getenv("MINIO_BUCKET")
    }
    print("[Startup] Инициализация хранилища и синхронизация данных...")
    try:
        storage = S3Storage(**s3_config)
        sync_service = DataSyncService(storage=storage)
        sync_service.sync_dataset(
            remote_path="data/ratings.csv",
            local_path="data/ratings.csv"
        )
    except Exception as e:
        print(f"[Startup Error] Ошибка синхронизации: {e}")
    yield
    print("[Shutdown] Остановка сервера...")

app = FastAPI(title="Movie Recommender API", lifespan=lifespan)

class RequestModel(BaseModel):
    user_id: int

@app.get("/")
def root():
    return {"message": "API is running. Use POST /recommend"}

@app.post("/recommend", response_model=list[Recommendation])
def recommend(request: RequestModel):
    service = RecommendationService(data_path="data/ratings.csv")
    return service.get_recommendations(request.user_id)