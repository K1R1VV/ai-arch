from pydantic import BaseModel
from typing import List, Optional
from pydantic import BaseModel, Field


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

class PredictRatingRequest(BaseModel):
    user_id: int = Field(..., examples=[123])
    movie_id: int = Field(..., examples=[456])
    year: Optional[int] = Field(2023)
    genre: Optional[str] = Field("Action")


class PredictRatingResponse(BaseModel):
    user_id: int
    movie_id: int
    predicted_rating: float = Field(..., examples=[4.5])


class MovieCandidate(BaseModel):
    movie_id: int
    year: Optional[int] = 2023
    genre: Optional[str] = "Action"


class RecommendRequest(BaseModel):
    user_id: int = Field(..., examples=[1])
    candidates: List[MovieCandidate] = Field(...)
    top_n: Optional[int] = Field(3, ge=1, le=10)


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool = False


class TaskResponse(BaseModel):
    task_id: str


class TaskResultResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None