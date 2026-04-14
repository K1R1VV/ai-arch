import sys
import json
import os
import pytest
import pandas as pd
import numpy as np
import logging
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

from src.presentation.cli import main as cli_main, load_candidate_movies
from src.domain.entities import Recommendation
from src.config.genre_encoding import encode_genre


class TestMovieRecommenderCLI:
    @pytest.fixture(autouse=True)
    def reset_sys(self):
        yield
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    @pytest.mark.parametrize("user_id", [1, 2, 100])
    def test_cli_success_with_valid_user_id(self, user_id, tmp_path, caplog):
        mock_model = MagicMock()
        mock_service = MagicMock()
        mock_service.get_recommendations.return_value = [
            Recommendation(movie_id=201, predicted_score=4.9, reason="High match"),
            Recommendation(movie_id=202, predicted_score=4.7, reason="Popular genre"),
        ]

        test_args = ['cli.py', str(user_id)]
        
        with patch('src.presentation.cli.get_model', return_value=mock_model):
            with patch('src.presentation.cli.get_service', return_value=mock_service):
                with patch('src.presentation.cli.load_candidate_movies', return_value=[
                    {'movie_id': 201, 'year': 2024, 'genre_encoded': encode_genre('Action')},
                    {'movie_id': 202, 'year': 2023, 'genre_encoded': encode_genre('Comedy')},
                ]):
                    with patch.object(sys, 'argv', test_args):
                        with caplog.at_level(logging.INFO):
                            exit_code = 0
                            try:
                                cli_main()
                            except SystemExit as e:
                                exit_code = e.code if isinstance(e.code, int) else 0
                            
                            assert exit_code == 0, f"CLI завершился с кодом {exit_code}"
                            assert any("рекомендаций" in msg.lower() or "recommendation" in msg.lower() 
                                     for msg in caplog.messages)
                            mock_service.get_recommendations.assert_called_once()

    def test_cli_model_not_found(self, tmp_path, caplog):
        with patch('src.presentation.cli.get_model', side_effect=FileNotFoundError("Model not found")):
            with patch('src.presentation.cli.load_candidate_movies', return_value=[
                {'movie_id': 101, 'year': 2023, 'genre_encoded': 0}
            ]):
                with patch.object(sys, 'argv', ['cli.py', '1']):
                    with caplog.at_level(logging.ERROR):
                        with pytest.raises(SystemExit) as exc_info:
                            cli_main()
                        assert exc_info.value.code == 1
                        assert any("не найдена" in msg.lower() or "not found" in msg.lower() 
                                 for msg in caplog.messages)

    def test_cli_no_candidates(self, tmp_path, caplog):
        with patch('src.presentation.cli.get_model'):
            with patch('src.presentation.cli.get_service'):
                with patch('src.presentation.cli.load_candidate_movies', return_value=[]):
                    with patch.object(sys, 'argv', ['cli.py', '1']):
                        with caplog.at_level(logging.INFO):
                            with pytest.raises(SystemExit) as exc_info:
                                cli_main()
                            assert exc_info.value.code in [0, 1]
                            assert any("кандидатов" in msg.lower() or "candidates" in msg.lower() 
                                     for msg in caplog.messages) or exc_info.value.code == 1


class TestConfiguration:
    @pytest.mark.parametrize("env_var,default,override,expected", [
        ("MLFLOW_TRACKING_URI", "http://localhost:5000", "http://prod:5000", "http://prod:5000"),
        ("MODEL_PATH", "models/movie_recommender.onnx", "/custom/path.onnx", "/custom/path.onnx"),
        ("LOG_LEVEL", "INFO", "DEBUG", "DEBUG"),
    ])
    def test_env_var_override(self, env_var, default, override, expected, monkeypatch):
        monkeypatch.delenv(env_var, raising=False)
        assert os.getenv(env_var, default) == default
        monkeypatch.setenv(env_var, override)
        assert os.getenv(env_var, default) == expected

    def test_mlflow_uri_default(self):
        from src.presentation.dependencies import MLFLOW_TRACKING_URI
        assert MLFLOW_TRACKING_URI == "http://localhost:5000" or MLFLOW_TRACKING_URI.startswith("http")


class TestRecommendationServiceIntegration:
    @pytest.fixture
    def mock_onnx_model(self):
        model = MagicMock()
        def mock_predict(user_id, movie_id, year, genre_encoded):
            score = 3.0 + 0.5 * (genre_encoded % 3) + 0.1 * (movie_id % 5)
            return min(5.0, max(1.0, score))
        model.predict.side_effect = mock_predict
        model.recommend.return_value = []
        return model

    def test_service_generates_sorted_recommendations(self, mock_onnx_model):
        from src.application.services import RecommendationService
        service = RecommendationService(model=mock_onnx_model)
        
        mock_onnx_model.recommend.return_value = [
            Recommendation(movie_id=101, predicted_score=4.9, reason="High"),
            Recommendation(movie_id=102, predicted_score=4.7, reason="Medium"),
            Recommendation(movie_id=103, predicted_score=4.5, reason="Low"),
        ]
        
        candidates = [
            {'movie_id': 101, 'year': 2023, 'genre_encoded': 0},
            {'movie_id': 102, 'year': 2022, 'genre_encoded': 1},
            {'movie_id': 103, 'year': 2024, 'genre_encoded': 2},
        ]
        
        results = service.get_recommendations(user_id=42, candidate_movies=candidates, top_n=3)
        scores = [r.predicted_score for r in results]
        assert scores == sorted(scores, reverse=True)
        assert len(results) <= 3
        assert all(isinstance(r, Recommendation) for r in results)

    def test_service_handles_empty_candidates(self, mock_onnx_model):
        from src.application.services import RecommendationService
        mock_onnx_model.recommend.return_value = []  # 🔑 Явный возврат
        service = RecommendationService(model=mock_onnx_model)
        results = service.get_recommendations(user_id=1, candidate_movies=[], top_n=5)
        assert results == []
        mock_onnx_model.recommend.assert_called_once_with(1, [], 5)


def create_test_dataset(tmp_path, n_users=10, n_movies=50, seed=42) -> str:
    np.random.seed(seed)
    df = pd.DataFrame({
        'user_id': np.random.randint(1, n_users+1, 500),
        'movie_id': np.random.randint(1, n_movies+1, 500),
        'year': np.random.randint(1990, 2024, 500),
        'genre': np.random.choice(['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror'], 500),
        'rating': np.round(np.random.uniform(1.0, 5.0, 500), 2)
    })
    path = tmp_path / "test_ratings.csv"
    df.to_csv(path, index=False)
    return str(path)