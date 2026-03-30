# Лабораторная работа №2: Вариант 10 (Система рекомендаций фильмов)

## Описание

Проект реализует систему рекомендаций фильмов с использованием Clean Architecture.
Данные версионируются через DVC и хранятся в S3-совместимом хранилище MinIO.

## Стек

- Python 3.11+
- Poetry
- Docker & Docker Compose (MinIO)
- DVC (Data Version Control)
- FastAPI

## Быстрый старт

### 1. Создание .env файла

**Линукс/macOS:**

```bash
cp .env.example .env
```

**Windows (CMD):**

```bash
copy .env.example .env
```

### 2. Запуск инфраструктуры

```bash
docker-compose up -d
```

MinIO будет доступен по адресу `http://localhost:9000` с учетными данными из `.env`.

### 3. Установка зависимостей

```bash
poetry install
```

### 4. Настройка dvc:

Настройка удаленного хранилища для моделей (если еще не настроено) 
```bash
  poetry run dvc remote add -d models_storage s3://models
  poetry run dvc remote modify models_storage endpointurl http://localhost:9000
  poetry run dvc remote modify models_storage access_key_id minioadmin
  poetry run dvc remote modify models_storage secret_access_key minioadmin
```

### 5. Инициализация MinIO

Инициализация бакетов (datasets и models) и загрузка демо-данных:

```bash
poetry run python scripts/init_minio.py
```

### 6. Обучение модели

```bash
poetry run python scripts/train_model.py
```

### 7. Версионирование модели

```bash
poetry run dvc add models/movie_recommender.onnx
poetry run dvc push -r models_storage
```

### 8. Запуск приложения

**CLI для получения рекомендаций:**

```bash
poetry run python -m src.presentation.cli <user_id>
```

Пример:

```bash
poetry run python -m src.presentation.cli 1
```

**FastAPI сервер (рекомендации через HTTP API):**

```bash
poetry run uvicorn src.presentation.api:app --reload
```

API будет доступен по адресу `http://localhost:8000`

## API Endpoints

### GET /

Проверка работоспособности API

```bash
curl -X GET "http://127.0.0.1:8000/" -H "accept: application/json"
```

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "model_loaded": true,
  "model_path": "models/movie_recommender.onnx"
}
```

---

### POST /api/v1/data/sync

Синхронизировать данные с MinIO

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/data/sync" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"remote_path\": \"data/ratings.csv\", \"local_path\": \"data/ratings.csv\"}"
```

**Request:**

```json
{
  "remote_path": "data/ratings.csv",
  "local_path": "data/ratings.csv"
}
```

**Response:**

```json
{
  "status": "success",
  "message": "Данные синхронизированы: data/ratings.csv",
}
```

---

### POST /api/v1/model/sync

Синхронизировать и загрузить модель

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/model/sync" -H "accept: application/json"
```

**Response:**

```json
{
  "status": "success",
  "message": "Модель синхронизирована и загружена",
  "files_synced": null
}
```

---

### POST /api/v1/movies/predict_rating

Предсказать рейтинг для пары пользователь/фильм

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/movies/predict_rating" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"user_id\": 123, \"movie_id\": 456, \"year\": 2023, \"genre\": \"Sci-Fi\"}"
```

**Request:**

```json
{
  "user_id": 123,
  "movie_id": 456,
  "year": 2023,
  "genre": "Sci-Fi"
}
```

**Response:**

```json
{
  "user_id": 123,
  "movie_id": 456,
  "predicted_rating": 3.03
}
```

---

### POST /api/v1/movies/recommend

Получить рекомендации из списка кандидатов

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/movies/recommend" -H "Content-Type: application/json" -d "{\"user_id\": 1, \"candidates\": [{\"movie_id\": 101, \"year\": 2023, \"genre\": \"Action\"}, {\"movie_id\": 102, \"year\": 2022, \"genre\": \"Comedy\"}, {\"movie_id\": 103, \"year\": 2024, \"genre\": \"Drama\"}], \"top_n\": 3}"
```

**Request:**

```json
{
  "user_id": 1,
  "candidates": [
    {"movie_id": 101, "year": 2023, "genre": "Action"},
    {"movie_id": 102, "year": 2022, "genre": "Comedy"},
    {"movie_id": 103, "year": 2024, "genre": "Drama"}
  ],
  "top_n": 3
}
```

**Response:**

```json
[
  {
    "movie_id": 101,
    "predicted_score": 4.8,
    "reason": "ONNX prediction for genre=Action"
  },
  {
    "movie_id": 103,
    "predicted_score": 4.3,
    "reason": "ONNX prediction for genre=Drama"
  },
  {
    "movie_id": 102,
    "predicted_score": 3.9,
    "reason": "ONNX prediction for genre=Comedy"
  }
]
```

## Запуск тестов

```bash
poetry run pytest tests/ -v
```

Для запуска с дополнительной информацией:

```bash
poetry run pytest tests/ -v -s
```

Запуск конкретного тестового файла:

```bash
poetry run pytest tests/test_cli.py -v
poetry run pytest tests/test_storage_and_sync.py -v
poetry run pytest tests/test_onnx_model.py -v
```

## Управление данными

DVC используется для версионирования данных. Основные команды:

- **Загрузить данные:** `poetry run dvc pull`
- **Проверить статус:** `poetry run dvc status`
- **Откатить до предыдущей версии:** `poetry run dvc checkout`

Данные версионируются автоматически при добавлении `.dvc` файлов в репозиторий.

