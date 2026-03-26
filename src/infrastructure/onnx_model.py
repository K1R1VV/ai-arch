import numpy as np
import onnxruntime as ort
from typing import List
from src.domain.interfaces import IMovieRecommender
from src.domain.entities import Recommendation


class ONNXMovieRecommender(IMovieRecommender): 
    def __init__(self, model_path: str):
        self.session = ort.InferenceSession(model_path)

        self.input_names = [input.name for input in self.session.get_inputs()]
        self.output_names = [output.name for output in self.session.get_outputs()]
        
        print(f"[ONNX] Модель загружена: {model_path}")
        print(f"[ONNX] Входы: {self.input_names}, Выход: {self.output_names}")

    def predict_rating(self, user_id: int, movie_id: int, year: int = 2023, genre: str = 'Action') -> float:
        input_feed = {
            'user_id': np.array([[float(user_id)]], dtype=np.float32),
            'movie_id': np.array([[float(movie_id)]], dtype=np.float32),
            'year': np.array([[float(year)]], dtype=np.float32),
            'genre': np.array([[genre]], dtype=np.str_)
        }
        
        results = self.session.run(self.output_names, input_feed)
        output_value = results[0][0]

        if isinstance(output_value, np.ndarray):
            predicted_rating = float(output_value.item())
        else:
            predicted_rating = float(output_value)

        return max(1.0, min(5.0, predicted_rating))

    def recommend(self, user_id: int, candidate_movies: List[dict], top_n: int = 3) -> List[Recommendation]:
        scored_movies = []
        
        for movie in candidate_movies:
            rating = self.predict_rating(
                user_id=user_id,
                movie_id=movie['movie_id'],
                year=movie.get('year', 2023),
                genre=movie.get('genre', 'Action')
            )
            scored_movies.append({
                'movie_id': movie['movie_id'],
                'predicted_rating': rating
            })

        scored_movies.sort(key=lambda x: x['predicted_rating'], reverse=True)
        top_movies = scored_movies[:top_n]

        recommendations = []
        for movie in top_movies:
            recommendations.append(Recommendation(
                movie_id=movie['movie_id'],
                predicted_score=round(movie['predicted_rating'], 2),
                reason="Predicted by ONNX model"
            ))
        
        return recommendations