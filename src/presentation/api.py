import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from src.application.services import DataSyncService, RecommendationService
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

@app.get("/")
def root():
    return {"message": "API is running. Use POST /recommend"}

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

@app.post("/recommend", response_model=list[Recommendation])
def recommend(request: RequestModel):
    service = RecommendationService(data_path="data/ratings.csv")
    return service.get_recommendations(request.user_id)