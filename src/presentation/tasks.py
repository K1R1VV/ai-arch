from src.application.services import RecommendationService
from src.presentation.dependencies import get_model
from src.presentation.celery_app import celery_app
from src.config.genre_encoding import encode_genre
import logging

logger = logging.getLogger(__name__)


service = RecommendationService(model=get_model())


@celery_app.task(name="recommend_for_user_task")
def recommend_for_user_task(user_id: int, candidate_movies: list, top_n: int = 3) -> dict:
    logger.info(f"[Celery] Задача рекомендаций: user={user_id}, movies={len(candidate_movies)}")

    encoded_candidates = []
    for c in candidate_movies:
        genre_str = c.get("genre", "Action")
        encoded_candidates.append({
            "movie_id": c["movie_id"],
            "year": c.get("year", 2023),
            "genre_encoded": encode_genre(genre_str)
        })

    recommendations = service.get_recommendations(user_id, encoded_candidates, top_n)

    result = {
        "recommendations": [
            {
                "movie_id": rec.movie_id,
                "predicted_score": rec.predicted_score,
                "reason": rec.reason
            }
            for rec in recommendations
        ]
    }
    
    return result 


@celery_app.task(name="predict_rating_task")
def predict_rating_task(user_id: int, movie_id: int, year: int = 2023, genre: str = "Action"):
    logger.info(f"[Celery] Предсказание рейтинга: user={user_id}, movie={movie_id}")

    genre_encoded = encode_genre(genre)
    score = service.predict_rating(user_id, movie_id, year, genre_encoded)
    
    return {
        "user_id": user_id,
        "movie_id": movie_id,
        "predicted_rating": round(score, 2)
    }