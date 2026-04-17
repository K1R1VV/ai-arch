import time
import pytest
import httpx


API_URL = "http://localhost:8000"
MAX_WAIT_SECONDS = 60
POLL_INTERVAL_SECONDS = 1

RECOMMEND_PAYLOAD = {
    "user_id": 1,
    "candidates": [
        {"movie_id": 101, "year": 2023, "genre": "Action"},
        {"movie_id": 102, "year": 2022, "genre": "Comedy"},
        {"movie_id": 103, "year": 2024, "genre": "Drama"}
    ],
    "top_n": 2
}

PREDICT_RATING_PAYLOAD = {
    "user_id": 123,
    "movie_id": 456,
    "year": 2023,
    "genre": "Sci-Fi"
}

def wait_for_task_completion(
    api_url: str,
    task_id: str,
    max_wait: int = MAX_WAIT_SECONDS,
    poll_interval: float = POLL_INTERVAL_SECONDS
) -> dict:
    start_time = time.time()
    
    with httpx.Client(timeout=30.0) as client:
        while time.time() - start_time < max_wait:
            response = client.get(f"{api_url}/api/v1/movies/results/{task_id}")
            response.raise_for_status()
            
            result_data = response.json()
            status = result_data.get("status")
            elapsed = time.time() - start_time
            
            if status == "SUCCESS":
                return result_data
            elif status == "FAILURE":
                error_msg = result_data.get("error", "Unknown error")
                raise RuntimeError(f"Задача завершилась с ошибкой: {error_msg}")

            time.sleep(poll_interval)

    raise AssertionError(
        f"Таймаут ожидания задачи {task_id} ({max_wait}s). "
        f"Последний статус: {result_data.get('status')}"
    )


class TestAsyncRecommendations:
    @pytest.mark.asyncio_integration
    def test_recommend_for_user_creates_task(self):
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{API_URL}/api/v1/movies/recommend_for_user",
                json=RECOMMEND_PAYLOAD
            )

            assert response.status_code == 202, f"Ожидался 202, получен {response.status_code}"
            data = response.json()
            assert "task_id" in data, "Ответ должен содержать task_id"
            
            task_id = data["task_id"]
            assert isinstance(task_id, str), "task_id должен быть строкой"
            assert len(task_id) > 0, "task_id не может быть пустым"

            print(f"Создана задача: {task_id}")

    
    @pytest.mark.asyncio_integration
    def test_get_results_for_invalid_task_id(self):
        invalid_task_id = "00000000-0000-0000-0000-000000000000"
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{API_URL}/api/v1/movies/results/{invalid_task_id}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == invalid_task_id
            assert data["status"] in ["PENDING", "NOT_FOUND"]


class TestAsyncPredictRating:
    @pytest.mark.asyncio_integration
    def test_predict_rating_async_creates_task(self):
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{API_URL}/api/v1/movies/predict_rating_async",
                json=PREDICT_RATING_PAYLOAD
            )
            
            assert response.status_code == 202
            data = response.json()
            assert "task_id" in data
            assert isinstance(data["task_id"], str)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio_integration: mark test as async integration test (requires running services)"
    )