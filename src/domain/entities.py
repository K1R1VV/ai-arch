from pydantic import BaseModel
from typing import List, Optional

class Rating(BaseModel):
    user_id: int
    movie_id: int
    rating: float
    timestamp: Optional[int] = None

class Recommendation(BaseModel):
    movie_id: int
    predicted_score: float
    reason: str = "Based on collaborative filtering"

class UserHistory(BaseModel):
    user_id: int
    rated_movies: List[int]
    average_rating: float