from src.presentation.celery_app import celery_app
from src.presentation.dependencies import get_model, get_recommendation_service
from src.domain.entities import Recommendation


model = get_model()
service = get_recommendation_service(model=model)


@celery_app.task(name="recommend_for_user", bind=True)
def recommend_for_user_task(self, user_id: int, candidate_movies: list[dict], top_n: int = 3) -> dict:
    try:
        recommendations = service.get_recommendations(
            user_id=user_id,
            candidate_movies=candidate_movies,
            top_n=top_n
        )

        return {
            "user_id": user_id,
            "recommendations": [
                {
                    "movie_id": rec.movie_id,
                    "predicted_score": rec.predicted_score,
                    "reason": rec.reason
                }
                for rec in recommendations
            ]
        }
        
    except Exception as e:
        raise e


@celery_app.task(name="predict_rating", bind=True)
def predict_rating_task(self, user_id: int, movie_id: int, year: int = 2023, genre: str = "Action") -> dict:
    try:       
        rating = service.predict_rating(
            user_id=user_id,
            movie_id=movie_id,
            year=year,
            genre=genre
        )
        
        return {
            "user_id": user_id,
            "movie_id": movie_id,
            "predicted_rating": round(rating, 2)
        }
        
    except Exception as e:
        raise e