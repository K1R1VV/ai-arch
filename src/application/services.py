import logging
from src.domain.interfaces import IDataStorage, IMovieRecommender
from src.domain.entities import Recommendation
from typing import List
from pathlib import Path


logger = logging.getLogger(__name__)


class RecommendationService:   
    def __init__(self, model: IMovieRecommender):
        self.model = model

    def get_recommendations(self, user_id: int, candidate_movies: List[dict], top_n: int = 3) -> List[Recommendation]:
        return self.model.recommend(user_id, candidate_movies, top_n)
    
    def predict_rating(self, user_id: int, movie_id: int, year: int = 2023, genre: str = 'Action') -> float:
        return self.model.predict_rating(user_id, movie_id, year, genre)