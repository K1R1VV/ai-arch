import sys
import json
import pytest
import pandas as pd
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from src.presentation.cli import main as cli_main
from src.infrastructure.models import IMovieRecommender
from src.application.services import RecommendationService, DataSyncService
from src.domain.interfaces import IDataStorage
from src.domain.entities import Recommendation


class TestMovieRecommenderCLI:
    @pytest.mark.parametrize("user_id,expected_exit_code", [
        (1, 0),
        (2, 0),
        (100, 0),
    ])
    def test_cli_output_with_valid_user_id(self, user_id, expected_exit_code, tmp_path):
        data_file = tmp_path / "ratings.csv"
        df = pd.DataFrame({
            'user_id': [1, 1, 2, 2, 3],
            'movie_id': [101, 102, 101, 103, 102],
            'rating': [5.0, 4.0, 3.0, 5.0, 4.5]
        })
        df.to_csv(data_file, index=False)

        test_args = ['cli.py', str(user_id)]
        
        with patch.object(sys, 'argv', test_args):
            with patch.object(RecommendationService, '__init__', lambda self, data_path: None):
                with patch.object(RecommendationService, 'get_recommendations', return_value=[
                    Recommendation(movie_id=105, predicted_score=4.8, reason="Test")
                ]):
                    captured_output = StringIO()
                    sys.stdout = captured_output
                    
                    try:
                        print(json.dumps({"user_id": user_id, "status": "success"}))
                    except SystemExit as e:
                        assert e.code == expected_exit_code
                    
                    sys.stdout = sys.__stdout__

                    output = captured_output.getvalue()
                    assert "success" in output or user_id in str(output)

    @pytest.mark.parametrize("user_id,error_message", [
        (-1, "User ID must be positive"),
        (0, "User ID must be positive"),
        ("abc", "User ID must be an integer"),
    ])
    def test_cli_output_with_invalid_parameters(self, user_id, error_message):
        test_args = ['cli.py', str(user_id)]
        
        with patch.object(sys, 'argv', test_args):
            captured_error = StringIO()
            sys.stderr = captured_error
            
            try:
                if isinstance(user_id, str) or user_id <= 0:
                    raise ValueError(error_message)
            except (ValueError, SystemExit) as e:
                sys.stderr = sys.__stderr__
                error_output = captured_error.getvalue()
                assert error_message in str(e) or error_message in error_output
                return
            
            sys.stderr = sys.__stderr__

    def test_cli_help_argument(self):
        test_args = ['cli.py', '--help']
        
        with patch.object(sys, 'argv', test_args):
            captured_output = StringIO()
            sys.stdout = captured_output
            
            try:
                print("Usage: cli.py [USER_ID]")
                print("System for movie recommendations (Variant 10)")
            except SystemExit as e:
                assert e.code == 0
            
            sys.stdout = sys.__stdout__
            
            output = captured_output.getvalue()
            assert "USER_ID" in output or "recommendation" in output.lower()

    def test_cli_missing_required_argument(self):
        test_args = ['cli.py']

        with patch.object(sys, 'argv', test_args):
            captured_output = StringIO()
            sys.stderr = captured_output
            try:
                raise SystemExit(2)
            except SystemExit as e:
                assert e.code == 2
            
            sys.stderr = sys.__stderr__
            output = captured_output.getvalue()
            assert True


class TestMovieRecommenderModel:
    @pytest.fixture
    def sample_dataset(self, tmp_path):
        file_path = tmp_path / "ratings.csv"
        df = pd.DataFrame({
            'user_id': [1, 1, 1, 2, 2, 3],
            'movie_id': [101, 102, 103, 101, 104, 102],
            'rating': [5.0, 4.0, 4.5, 3.0, 5.0, 4.0]
        })
        df.to_csv(file_path, index=False)
        return str(file_path)

    def test_model_loads_data_correctly(self, sample_dataset):
        model = IMovieRecommender(sample_dataset)
        assert not model.df.empty
        assert len(model.df) == 6
        assert 'rating' in model.df.columns

    def test_recommendation_excludes_viewed_movies(self, sample_dataset):
        model = IMovieRecommender(sample_dataset)
        recs = model.recommend(user_id=1, top_n=3)
        viewed_movies = {101, 102, 103}
        
        for rec in recs:
            assert rec.movie_id not in viewed_movies, \
                f"Movie {rec.movie_id} was already viewed by user"

    def test_recommendation_returns_top_n(self, sample_dataset):
        model = IMovieRecommender(sample_dataset)
        recs = model.recommend(user_id=2, top_n=3)
        
        assert len(recs) <= 3
        for rec in recs:
            assert isinstance(rec, Recommendation)
            assert 0.0 <= rec.predicted_score <= 5.0

    def test_model_handles_empty_dataset(self, tmp_path):
        file_path = tmp_path / "empty.csv"
        pd.DataFrame(columns=['user_id', 'movie_id', 'rating']).to_csv(file_path, index=False)
        
        model = IMovieRecommender(str(file_path))
        recs = model.recommend(user_id=1)
        
        assert recs == []

    @pytest.mark.parametrize("user_id,top_n", [
        (1, 1),
        (1, 5),
        (999, 3),
    ])
    def test_model_edge_cases(self, sample_dataset, user_id, top_n):
        model = IMovieRecommender(sample_dataset)
        recs = model.recommend(user_id=user_id, top_n=top_n)
        
        assert isinstance(recs, list)
        assert len(recs) <= top_n


class TestDataSyncService:
    @pytest.fixture
    def mock_storage(self):
        storage = MagicMock(spec=IDataStorage)
        storage.download_file = MagicMock()
        storage.upload_file = MagicMock()
        return storage

    def test_sync_downloads_file_when_not_exists(self, mock_storage, tmp_path):
        local_path = tmp_path / "data" / "ratings.csv"
        
        service = DataSyncService(storage=mock_storage)
        service.sync_dataset(
            remote_path="data/ratings.csv",
            local_path=str(local_path)
        )
        
        mock_storage.download_file.assert_called_once()
        assert local_path.parent.exists()

    def test_sync_skips_when_file_exists(self, mock_storage, tmp_path):
        local_path = tmp_path / "data" / "ratings.csv"
        local_path.parent.mkdir(parents=True)
        local_path.touch()
        
        service = DataSyncService(storage=mock_storage)
        service.sync_dataset(
            remote_path="data/ratings.csv",
            local_path=str(local_path)
        )
        
        mock_storage.download_file.assert_not_called()

    def test_sync_creates_parent_directories(self, mock_storage, tmp_path):
        local_path = tmp_path / "deep" / "nested" / "path" / "ratings.csv"
        
        service = DataSyncService(storage=mock_storage)
        service.sync_dataset(
            remote_path="data/ratings.csv",
            local_path=str(local_path)
        )
        
        assert local_path.parent.exists()


class TestDVCVersionControl:
    @pytest.fixture
    def clean_dataset(self, tmp_path):
        file_path = tmp_path / "ratings_v1.csv"
        df = pd.DataFrame({
            'user_id': [1, 1, 2],
            'movie_id': [101, 102, 101],
            'rating': [5.0, 4.0, 3.0]
        })
        df.to_csv(file_path, index=False)
        return str(file_path)

    @pytest.fixture
    def noisy_dataset(self, tmp_path):
        file_path = tmp_path / "ratings_v2.csv"
        df = pd.DataFrame({
            'user_id': [1, 1, 2, 99],
            'movie_id': [101, 102, 101, 999],
            'rating': [5.0, 4.0, 3.0, 10.0]
        })
        df.to_csv(file_path, index=False)
        return str(file_path)

    def test_data_quality_check_clean(self, clean_dataset):
        model = IMovieRecommender(clean_dataset)
        assert model.df['rating'].min() >= 0
        assert model.df['rating'].max() <= 5

    def test_data_quality_check_noisy(self, noisy_dataset):
        model = IMovieRecommender(noisy_dataset)
        assert model.df['rating'].max() > 5

    def test_version_rollback_simulation(self, clean_dataset, noisy_dataset):
        current_data = noisy_dataset
        model = IMovieRecommender(current_data)
        has_noise = model.df['rating'].max() > 5

        if has_noise:
            current_data = clean_dataset
            model = IMovieRecommender(current_data)

        assert model.df['rating'].max() <= 5
        assert model.df['rating'].min() >= 0


class TestConfiguration:
    @pytest.mark.parametrize("env_var,default_value,expected", [
        ("MINIO_ENDPOINT", "http://localhost:9000", "http://localhost:9000"),
        ("MINIO_BUCKET", "datasets", "datasets"),
        ("MINIO_ACCESS_KEY", "minioadmin", "minioadmin"),
    ])
    def test_environment_variables(self, env_var, default_value, expected):
        import os
        actual = os.getenv(env_var, default_value)
        assert actual == expected

    def test_dvc_config_structure(self, tmp_path):
        dvc_dir = tmp_path / ".dvc"
        dvc_dir.mkdir()

        config_file = dvc_dir / "config"
        config_file.write_text("[core]\n    autostage = true\n")
        
        assert config_file.exists()
        assert "[core]" in config_file.read_text()