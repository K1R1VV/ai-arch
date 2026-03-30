from abc import ABC, abstractmethod
from typing import List
from src.domain.entities import Recommendation


class IDataStorage(ABC):
    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> None:
        pass

    @abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> None:
        pass


class IMovieRecommender(ABC):
    @abstractmethod
    def predict_rating(self, user_id: int, movie_id: int, year: int = 2023, genre: str = 'Action') -> float:
        pass
    
    @abstractmethod
    def recommend(self, user_id: int, candidate_movies: List[dict], top_n: int = 3) -> List[Recommendation]:
        pass