from abc import ABC, abstractmethod
from typing import List
from src.domain.entities import Recommendation


class IMovieRecommender(ABC):
    @abstractmethod
    def predict_rating(self, user_id: int, movie_id: int, year: int = 2023, genre: str = 'Action') -> float:
        pass
    
    @abstractmethod
    def recommend(self, user_id: int, candidate_movies: List[dict], top_n: int = 3) -> List[Recommendation]:
        pass