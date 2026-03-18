import pytest
import numpy as np
from unittest.mock import MagicMock, patch, mock_open
from src.infrastructure.onnx_model import ONNXMovieRecommender
from src.application.services import RecommendationService
from src.domain.entities import Recommendation


class TestONNXMovieRecommender:
    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.get_inputs.return_value = [MagicMock(name='float_input')]
        session.get_outputs.return_value = [MagicMock(name='variable')]
        session.run.return_value = [[4.2]]
        return session

    def test_model_initialization(self, mock_session):
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            
            assert model.session == mock_session
            assert model.input_name == 'float_input'
            mock_ort.assert_called_once_with("models/movie_recommender.onnx")

    def test_predict_rating(self, mock_session):
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            rating = model.predict_rating(user_id=1, movie_id=101, year=2023)
            
            assert isinstance(rating, float)
            assert 1.0 <= rating <= 5.0
            mock_session.run.assert_called_once()

    def test_predict_rating_clipping(self, mock_session):
        mock_session.run.return_value = [[10.0]]
        
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            rating = model.predict_rating(user_id=1, movie_id=101)
            
            assert rating == 5.0

    def test_recommend_returns_top_n(self, mock_session):
        mock_session.run.side_effect = [
            [[4.5]],
            [[3.2]],
            [[4.8]],
        ]
        
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_ort.return_value = mock_session
            
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            candidates = [
                {'movie_id': 101, 'year': 2023},
                {'movie_id': 102, 'year': 2022},
                {'movie_id': 103, 'year': 2024},
            ]
            recs = model.recommend(user_id=1, candidate_movies=candidates, top_n=2)
            
            assert len(recs) == 2
            assert all(isinstance(r, Recommendation) for r in recs)
            assert recs[0].predicted_score >= recs[1].predicted_score


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
        candidates = [{'movie_id': 101, 'year': 2023}]
        
        recs = service.get_recommendations(user_id=1, candidate_movies=candidates, top_n=2)
        
        assert len(recs) == 2
        mock_model.recommend.assert_called_once()

    def test_service_predict_rating(self, mock_model):
        service = RecommendationService(model=mock_model)
        rating = service.predict_rating(user_id=1, movie_id=101, year=2023)
        
        assert rating == 4.2
        mock_model.predict_rating.assert_called_once_with(1, 101, 2023)


class TestModelIntegration:
    def test_full_recommendation_workflow(self):
        with patch('src.infrastructure.onnx_model.ort.InferenceSession') as mock_ort:
            mock_session = MagicMock()
            mock_session.get_inputs.return_value = [MagicMock(name='float_input')]
            mock_session.get_outputs.return_value = [MagicMock(name='variable')]
            mock_session.run.side_effect = [[[4.5]], [[3.8]], [[4.2]]]
            mock_ort.return_value = mock_session
            
            model = ONNXMovieRecommender("models/movie_recommender.onnx")
            service = RecommendationService(model=model)
            
            candidates = [
                {'movie_id': 101, 'year': 2023},
                {'movie_id': 102, 'year': 2022},
                {'movie_id': 103, 'year': 2024},
            ]
            
            recs = service.get_recommendations(user_id=1, candidate_movies=candidates, top_n=3)
            
            assert len(recs) == 3
            assert recs[0].predicted_score == 4.5