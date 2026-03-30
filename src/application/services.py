import logging
from src.domain.interfaces import IDataStorage, IMovieRecommender
from src.domain.entities import Recommendation
from typing import List
from pathlib import Path


logger = logging.getLogger(__name__)


class DataSyncService:   
    def __init__(self, storage: IDataStorage):
        self.storage = storage

    def sync_dataset(self, remote_path: str, local_path: str, force: bool = False) -> None:
        local_file = Path(local_path)
        
        if local_file.exists() and not force:
            logger.info(f"[Sync] Файл {local_path} уже существует. Пропускаю (используйте force=True для обновления).")
            return
        
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"[Sync] Загрузка файла: {remote_path} → {local_path}")
        self.storage.download_file(remote_path, local_path)
        logger.info(f"[Sync] Файл успешно синхронизирован: {local_path}")


class RecommendationService:   
    def __init__(self, model: IMovieRecommender):
        self.model = model

    def get_recommendations(self, user_id: int, candidate_movies: List[dict], top_n: int = 3) -> List[Recommendation]:
        return self.model.recommend(user_id, candidate_movies, top_n)
    
    def predict_rating(self, user_id: int, movie_id: int, year: int = 2023, genre: str = 'Action') -> float:
        return self.model.predict_rating(user_id, movie_id, year, genre)