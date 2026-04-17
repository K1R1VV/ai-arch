import numpy as np
import onnxruntime as ort
from typing import List, Union
from src.domain.interfaces import IMovieRecommender
from src.domain.entities import Recommendation
from src.config.genre_encoding import encode_genre
import logging

logger = logging.getLogger(__name__)


class ONNXMovieRecommender(IMovieRecommender): 
    def __init__(self, model_path: str):
        self.session = ort.InferenceSession(model_path)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]
        logger.info(f"[ONNX] Модель загружена: {model_path}")

    def predict_rating(
        self, 
        user_id: int, 
        movie_id: int, 
        year: int = 2023, 
        genre_encoded: int = 0
    ) -> float:
        genre_encoded = int(encode_genre(genre_encoded) if isinstance(genre_encoded, str) else genre_encoded)
        
        input_array = np.array([[
            float(user_id), 
            float(movie_id), 
            float(year), 
            float(genre_encoded)
        ]], dtype=np.float32)
        
        results = self.session.run(self.output_names, {self.input_name: input_array})
        return max(1.0, min(5.0, float(results[0][0][0])))

    def recommend(
        self, 
        user_id: int, 
        candidate_movies: List[dict], 
        top_n: int = 3
    ) -> List[Recommendation]:
        scored = []
        for movie in candidate_movies:
            genre_val = movie.get('genre_encoded')
            if genre_val is None and 'genre' in movie:
                genre_val = encode_genre(movie['genre'])
            elif genre_val is None:
                genre_val = 0

            rating = self.predict_rating(
                user_id=user_id,
                movie_id=movie['movie_id'],
                year=movie.get('year', 2023),
                genre_encoded=genre_val
            )
            scored.append({
                'movie_id': movie['movie_id'],
                'predicted_rating': rating
            })

        scored.sort(key=lambda x: x['predicted_rating'], reverse=True)
        return [
            Recommendation(
                movie_id=m['movie_id'],
                predicted_score=round(m['predicted_rating'], 2),
                reason="Predicted by ONNX model"
            )
            for m in scored[:top_n]
        ]
    

class UninitializedRecommender(IMovieRecommender):  
    def __init__(self, error_message: str = "Model not initialized"):
        self.error_message = error_message
        self.is_loaded = False
        logger.warning(f"[ONNX] Модель не инициализирована: {error_message}")

    def predict_rating(self, user_id: int, movie_id: int, year: int = 2023, genre_encoded: int = 0) -> float:
        raise RuntimeError(self.error_message)

    def recommend(self, user_id: int, candidate_movies: List[dict], top_n: int = 3) -> List[Recommendation]:
        raise RuntimeError(self.error_message)