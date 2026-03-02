from src.domain.interfaces import IDataStorage
from src.domain.entities import Recommendation
from src.infrastructure.models import IMovieRecommender
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
    def __init__(self, data_path: str):
        self.model = IMovieRecommender(data_path)

    def get_recommendations(self, user_id: int) -> list[Recommendation]:
        return self.model.recommend(user_id)
    
    def check_data_quality(self) -> bool:
        if self.model.df.empty:
            return False
        if self.model.df['rating'].min() < 0 or self.model.df['rating'].max() > 5:
            return False
        return True