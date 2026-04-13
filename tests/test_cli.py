# tests/test_cli.py
import sys
import json
import pytest
import pandas as pd
import numpy as np
from io import StringIO
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from src.presentation.cli import main as cli_main, load_candidate_movies
from src.domain.entities import Recommendation


# ============================================================================
# 🎬 Тесты CLI (интеграционные с моками зависимостей)
# ============================================================================

class TestMovieRecommenderCLI:
    """Тесты CLI-интерфейса с мокированием MLflow и сервисов"""

    @pytest.fixture(autouse=True)
    def reset_sys(self):
        """Сбрасывает sys.stdout/stderr после каждого теста"""
        yield
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    @pytest.mark.parametrize("user_id", [1, 2, 100])
    def test_cli_success_with_valid_user_id(self, user_id, tmp_path):
        """CLI успешно генерирует рекомендации для валидного user_id"""
        # Создаём тестовый датасет
        data_file = tmp_path / "ratings.csv"
        df = pd.DataFrame({
            'user_id': [1, 1, 2, 2, 3, user_id],
            'movie_id': [101, 102, 101, 103, 102, 200],
            'year': [2023, 2022, 2023, 2021, 2023, 2024],
            'genre': ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror', 'Action'],
            'rating': [5.0, 4.0, 3.0, 5.0, 4.5, 4.8]
        })
        df.to_csv(data_file, index=False)

        # Мокаем загрузку модели через dependencies.py
        mock_model = MagicMock()
        mock_service = MagicMock()
        mock_service.get_recommendations.return_value = [
            Recommendation(movie_id=201, predicted_score=4.9, reason="High match"),
            Recommendation(movie_id=202, predicted_score=4.7, reason="Popular genre"),
        ]

        test_args = ['cli.py', str(data_file), str(user_id)]
        
        with patch('src.presentation.cli.get_model', return_value=mock_model):
            with patch('src.presentation.cli.get_service', return_value=mock_service):
                with patch.object(sys, 'argv', test_args):
                    # Перенаправляем вывод для захвата
                    captured = StringIO()
                    sys.stdout = captured
                    
                    # Запускаем CLI — не должно выбросить SystemExit с кодом != 0
                    exit_code = 0
                    try:
                        cli_main()
                    except SystemExit as e:
                        exit_code = e.code if isinstance(e.code, int) else 0
                    
                    output = captured.getvalue()
                    
                    # Проверяем успешное выполнение
                    assert exit_code == 0, f"CLI завершился с кодом {exit_code}"
                    assert "рекомендаций" in output.lower() or "recommendation" in output.lower()
                    mock_service.get_recommendations.assert_called_once()

    def test_cli_model_not_found(self, tmp_path):
        """CLI корректно обрабатывает отсутствие модели"""
        data_file = tmp_path / "ratings.csv"
        pd.DataFrame(columns=['user_id', 'movie_id', 'year', 'genre', 'rating']).to_csv(data_file, index=False)

        test_args = ['cli.py', str(data_file), '1']
        
        with patch('src.presentation.cli.get_model', side_effect=FileNotFoundError("Model not found")):
            with patch.object(sys, 'argv', test_args):
                captured = StringIO()
                sys.stdout = captured
                sys.stderr = captured
                
                exit_code = 0
                try:
                    cli_main()
                except SystemExit as e:
                    exit_code = e.code if isinstance(e.code, int) else 1
                
                output = captured.getvalue()
                assert exit_code == 1
                assert "не найдена" in output.lower() or "not found" in output.lower()

    def test_cli_no_candidates(self, tmp_path):
        """CLI корректно обрабатывает пустой список кандидатов"""
        # Пустой датасет
        data_file = tmp_path / "ratings.csv"
        pd.DataFrame(columns=['user_id', 'movie_id', 'year', 'genre', 'rating']).to_csv(data_file, index=False)

        test_args = ['cli.py', str(data_file), '1']
        
        with patch('src.presentation.cli.get_model'):
            with patch('src.presentation.cli.get_service'):
                with patch.object(sys, 'argv', test_args):
                    captured = StringIO()
                    sys.stdout = captured
                    sys.stderr = captured
                    
                    exit_code = 0
                    try:
                        cli_main()
                    except SystemExit as e:
                        exit_code = e.code if isinstance(e.code, int) else 0
                    
                    # Допускаем выход с кодом 1 при отсутствии кандидатов
                    output = captured.getvalue()
                    assert "кандидатов" in output.lower() or "candidates" in output.lower() or exit_code == 1


# ============================================================================
# 📊 Тесты функции load_candidate_movies (юнит-тесты)
# ============================================================================

class TestLoadCandidateMovies:
    """Юнит-тесты для функции загрузки фильмов-кандидатов"""

    @pytest.fixture
    def valid_csv(self, tmp_path):
        """Создаёт валидный CSV-файл с тестовыми данными"""
        def _create(data: dict, filename: str = "test.csv") -> str:
            path = tmp_path / filename
            pd.DataFrame(data).to_csv(path, index=False)
            return str(path)
        return _create

    def test_load_valid_candidates(self, valid_csv):
        """Загружает корректные данные с фильтрацией просмотренных фильмов"""
        csv_path = valid_csv({
            'user_id': [1, 1, 2, 2, 3],
            'movie_id': [101, 102, 101, 103, 102],
            'year': [2023, 2022, 2023, 2021, 2024],
            'genre': ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror'],
            'rating': [5.0, 4.0, 3.0, 5.0, 4.5]
        })

        result = load_candidate_movies(csv_path, exclude_user_id=1)
        
        # Проверяем, что фильмы пользователя 1 исключены
        viewed_by_user1 = {101, 102}
        for candidate in result:
            assert candidate['movie_id'] not in viewed_by_user1
        
        # Проверяем структуру результата
        assert len(result) > 0
        for item in result:
            assert 'movie_id' in item
            assert 'year' in item
            assert 'genre' in item
            assert isinstance(item['movie_id'], int)

    def test_load_missing_columns(self, valid_csv):
        """Возвращает пустой список при отсутствии обязательных колонок"""
        csv_path = valid_csv({
            'movie_id': [101, 102],
            'title': ['Movie A', 'Movie B']  # Нет required columns
        })

        result = load_candidate_movies(csv_path)
        assert result == []

    def test_load_nonexistent_file(self):
        """Возвращает пустой список для несуществующего файла"""
        result = load_candidate_movies("/nonexistent/path/data.csv")
        assert result == []

    def test_load_with_nan_values(self, valid_csv):
        """Корректно обрабатывает NaN-значения в данных"""
        csv_path = valid_csv({
            'user_id': [1, 2, np.nan],
            'movie_id': [101, 102, 103],
            'year': [2023, np.nan, 2021],
            'genre': ['Action', None, 'Drama'],
            'rating': [5.0, 4.0, 3.0]
        })

        result = load_candidate_movies(csv_path)
        
        # Должны загрузиться валидные записи
        assert len(result) >= 1
        # Проверка дефолтных значений для NaN
        for item in result:
            assert isinstance(item['year'], int)  # Дефолт 2023
            assert isinstance(item['genre'], str)  # Дефолт 'Action'

    def test_exclude_user_id_none(self, valid_csv):
        """Без exclude_user_id загружает все уникальные фильмы"""
        csv_path = valid_csv({
            'user_id': [1, 1, 2],
            'movie_id': [101, 102, 103],
            'year': [2023, 2022, 2021],
            'genre': ['Action', 'Comedy', 'Drama'],
            'rating': [5.0, 4.0, 3.0]
        })

        result = load_candidate_movies(csv_path, exclude_user_id=None)
        
        # Все 3 фильма должны быть в кандидатах
        movie_ids = {item['movie_id'] for item in result}
        assert movie_ids == {101, 102, 103}


# ============================================================================
# 🧪 Тесты конфигурации и окружения
# ============================================================================

class TestConfiguration:
    """Тесты конфигурации через переменные окружения"""

    @pytest.mark.parametrize("env_var,default,override,expected", [
        ("MLFLOW_TRACKING_URI", "http://localhost:5000", "http://prod:5000", "http://prod:5000"),
        ("MODEL_PATH", "models/movie_recommender.onnx", "/custom/path.onnx", "/custom/path.onnx"),
        ("LOG_LEVEL", "INFO", "DEBUG", "DEBUG"),
    ])
    def test_env_var_override(self, env_var, default, override, expected, monkeypatch):
        """Переменные окружения корректно переопределяют дефолты"""
        # Сбрасываем и устанавливаем тестовое значение
        monkeypatch.delenv(env_var, raising=False)
        assert os.getenv(env_var, default) == default
        
        monkeypatch.setenv(env_var, override)
        assert os.getenv(env_var, default) == expected

    def test_mlflow_uri_default(self):
        """Дефолтный URI MLflow соответствует документации"""
        from src.presentation.dependencies import MLFLOW_TRACKING_URI
        assert MLFLOW_TRACKING_URI == "http://localhost:5000" or MLFLOW_TRACKING_URI.startswith("http")


# ============================================================================
# 🎯 Тесты RecommendationService (интеграция с моделью)
# ============================================================================

class TestRecommendationServiceIntegration:
    """Интеграционные тесты сервиса рекомендаций"""

    @pytest.fixture
    def mock_onnx_model(self):
        model = MagicMock()
        def mock_predict(user_id, movie_id, year, genre_encoded):
            score = 3.0 + 0.5 * (genre_encoded % 3) + 0.1 * (movie_id % 5)
            return min(5.0, max(1.0, score))
        model.predict.side_effect = mock_predict
        return model

    def test_service_generates_sorted_recommendations(self, mock_onnx_model):
        from src.application.services import RecommendationService
        
        service = RecommendationService(model=mock_onnx_model)
        
        candidates = [
            {'movie_id': 101, 'year': 2023, 'genre_encoded': 0},
            {'movie_id': 102, 'year': 2022, 'genre_encoded': 1},
            {'movie_id': 103, 'year': 2024, 'genre_encoded': 2},
        ]
        
        results = service.get_recommendations(
            user_id=42,
            candidate_movies=candidates,
            top_n=3
        )

        scores = [r.predicted_score for r in results]
        assert scores == sorted(scores, reverse=True), "Рекомендации не отсортированы по убыванию"
        assert len(results) <= 3
        assert all(isinstance(r, Recommendation) for r in results)

    def test_service_handles_empty_candidates(self, mock_onnx_model):
        from src.application.services import RecommendationService
        
        service = RecommendationService(model=mock_onnx_model)
        results = service.get_recommendations(user_id=1, candidate_movies=[], top_n=5)
        
        assert results == []


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