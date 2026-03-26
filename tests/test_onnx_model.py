import pytest
import numpy as np
from unittest.mock import MagicMock, patch, call
from src.infrastructure.onnx_model import ONNXMovieRecommender
from src.application.services import RecommendationService
from src.domain.entities import Recommendation


@pytest.fixture
def mock_session():
    session = MagicMock()
    
    mock_inputs = [MagicMock(name=n) for n in ['user_id', 'movie_id', 'year', 'genre']]
    for i, name in enumerate(['user_id', 'movie_id', 'year', 'genre']):
        mock_inputs[i].name = name
    session.get_inputs.return_value = mock_inputs
    
    mock_output = MagicMock()
    mock_output.name = 'variable'
    session.get_outputs.return_value = [mock_output]
    
    session.run.return_value = [[4.2]]
    return session


class TestONNXMovieRecommender:
    def test_model_initialization(self, mock_session):
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            
            assert model.session == mock_session
            assert model.input_names == ['user_id', 'movie_id', 'year', 'genre']
            assert model.output_names == ['variable']
            mock_ort.assert_called_once_with("models/movie_recommender.onnx")

    def test_predict_rating(self, mock_session):
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            rating = model.predict_rating(user_id=1, movie_id=101, year=2023, genre="Sci-Fi")
            
            assert isinstance(rating, float)
            assert 1.0 <= rating <= 5.0
            
            mock_session.run.assert_called_once()
            input_feed = mock_session.run.call_args[0][1]
            
            assert 'user_id' in input_feed
            assert 'movie_id' in input_feed
            assert 'year' in input_feed
            assert 'genre' in input_feed
            assert input_feed['genre'].dtype.kind in ['U', 'S'] or np.issubdtype(input_feed['genre'].dtype, np.str_)

    def test_predict_rating_default_genre(self, mock_session):
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            model.predict_rating(user_id=1, movie_id=101, year=2023)
            
            input_feed = mock_session.run.call_args[0][1]
            assert input_feed['genre'][0][0] == "Action"

    def test_predict_rating_clipping(self, mock_session):
        mock_session.run.return_value = [[10.0]]
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            assert model.predict_rating(user_id=1, movie_id=101, genre="Horror") == 5.0

    def test_predict_rating_lower_clipping(self, mock_session):
        mock_session.run.return_value = [[-1.0]]
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            assert model.predict_rating(user_id=1, movie_id=101, genre="Drama") == 1.0

    def test_recommend_returns_top_n(self, mock_session):
        mock_session.run.side_effect = [[[4.5]], [[3.2]], [[4.8]]]
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            candidates = [
                {'movie_id': 101, 'year': 2023, 'genre': 'Action'},
                {'movie_id': 102, 'year': 2022, 'genre': 'Comedy'},
                {'movie_id': 103, 'year': 2024, 'genre': 'Drama'},
            ]
            recs = model.recommend(user_id=1, candidate_movies=candidates, top_n=2)
            assert len(recs) == 2
            assert recs[0].predicted_score >= recs[1].predicted_score
            assert recs[0].predicted_score == 4.8

    def test_recommend_missing_genre_uses_default(self, mock_session):
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            model.recommend(user_id=1, candidate_movies=[{'movie_id': 101, 'year': 2023}], top_n=1)
            input_feed = mock_session.run.call_args[0][1]
            assert input_feed['genre'][0][0] == "Action"


class TestRecommendationService:
    @pytest.fixture
    def mock_model(self):
        model = MagicMock()
        model.recommend.return_value = [
            Recommendation(movie_id=101, predicted_score=4.5, reason="Test"),
            Recommendation(movie_id=102, predicted_score=4.0, reason="Test"),
        ]
        model.predict_rating.return_value = 4.2
        return model

    def test_service_get_recommendations(self, mock_model):
        service = RecommendationService(model=mock_model)
        candidates = [{'movie_id': 101, 'year': 2023, 'genre': 'Action'}]
        recs = service.get_recommendations(user_id=1, candidate_movies=candidates, top_n=2)
        assert len(recs) == 2
        mock_model.recommend.assert_called_once()
        call_args = mock_model.recommend.call_args
        passed_candidates = call_args[0][1] if call_args[0] else call_args[1]['candidate_movies']
        assert 'genre' in passed_candidates[0]

    def test_service_predict_rating(self, mock_model):
        service = RecommendationService(model=mock_model)
        rating = service.predict_rating(user_id=1, movie_id=101, year=2023, genre="Comedy")
        assert rating == 4.2
        mock_model.predict_rating.assert_called_once_with(1, 101, 2023, "Comedy")

    def test_service_predict_rating_default_genre(self, mock_model):
        service = RecommendationService(model=mock_model)
        rating = service.predict_rating(user_id=1, movie_id=101)
        assert rating == 4.2
        mock_model.predict_rating.assert_called_once_with(1, 101, 2023, "Action")


class TestModelIntegration:
    def test_full_recommendation_workflow(self, mock_session):
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            service = RecommendationService(model=model)
            candidates = [
                {'movie_id': 101, 'year': 2023, 'genre': 'Action'},
                {'movie_id': 102, 'year': 2022, 'genre': 'Comedy'},
                {'movie_id': 103, 'year': 2024, 'genre': 'Drama'},
            ]
            mock_session.run.side_effect = [[[4.5]], [[3.8]], [[4.2]]]
            recs = service.get_recommendations(user_id=1, candidate_movies=candidates, top_n=3)
            assert len(recs) == 3
            assert recs[0].predicted_score == 4.5

    def test_input_feed_structure(self, mock_session):
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            model.predict_rating(user_id=42, movie_id=777, year=2024, genre="Thriller")
            input_feed = mock_session.run.call_args[0][1]
            
            assert set(input_feed.keys()) == {'user_id', 'movie_id', 'year', 'genre'}
            assert input_feed['user_id'].shape == (1, 1) and input_feed['user_id'].dtype == np.float32
            assert input_feed['movie_id'].shape == (1, 1) and input_feed['movie_id'].dtype == np.float32
            assert input_feed['year'].shape == (1, 1) and input_feed['year'].dtype == np.float32
            assert input_feed['genre'].shape == (1, 1)
            assert input_feed['genre'].dtype.kind in ['U', 'S'] or np.issubdtype(input_feed['genre'].dtype, np.str_)
            assert input_feed['genre'][0][0] == "Thriller"