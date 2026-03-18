from src.domain.interfaces import IDataStorage
from src.domain.entities import Recommendation
from src.infrastructure.models import IMovieRecommender
from typing import List
from pathlib import Path

class DataSyncService:
    def __init__(self, storage: IDataStorage):
        self.storage = storage

    def sync_dataset(self, remote_path: str, local_path: str) -> None:
        local_file = Path(local_path)
        if not local_file.exists():
            print(f"[Sync] Файл {local_path} не найден. Запрашиваю синхронизацию...")
            local_file.parent.mkdir(parents=True, exist_ok=True)
            self.storage.download_file(remote_path, local_path)
        else:
            print(f"[Sync] Файл {local_path} уже существует. Пропускаю.")

class RecommendationService:
    def __init__(self, model: IMovieRecommender):
        self.model = model

    def get_recommendations(self, user_id: int, candidate_movies: List[dict], top_n: int = 3) -> list[Recommendation]:
        return self.model.recommend(user_id, candidate_movies, top_n)
    
    def check_data_quality(self) -> bool:
        if self.model.df.empty:
            return False
        if self.model.df['rating'].min() < 0 or self.model.df['rating'].max() > 5:
            return False
        return True
    
    def predict_rating(self, user_id: int, movie_id: int, year: int = 2023) -> float:
        return self.model.predict_rating(user_id, movie_id, year)