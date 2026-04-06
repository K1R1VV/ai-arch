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

### 2. Запуск хранилища

Запустим хранилище Minio

```bash
docker-compose up -d minio
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

### 7. Версионирование модели и загрука в хранилище

```bash
poetry run dvc add models/movie_recommender.onnx
poetry run dvc push -r models_storage
```

Для загрузки модели в удаленное хранилище воспользуемся скриптом:

```bash
poetry run python scripts/upload_model.py
```

### 8. Запуск инфраструктуры

Запустим хранилище Minio

```bash
docker-compose up -d api worker
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

Сервер запущен через докер, API доступно по адресу `http://localhost:8000`

## API Endpoints

### POST /api/v1/movies/predict_rating_async

Предсказать рейтинг

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/movies/predict_rating_async" ^
-H "Content-Type: application/json" ^
-d "{\"user_id\": 123, \"movie_id\": 456, \"year\": 2023, \"genre\": \"Sci-Fi\"}"
```

**Response:**

```json
{"task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
```

Получение статуса задачи

```bash
curl "http://127.0.0.1:8000/api/v1/movies/results/{task_id}"
```

---

### POST /api/v1/movies/recommend_for_user

Получить рекомендации для пользователя

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/movies/recommend_for_user" ^
-H "Content-Type: application/json" ^
-d "{\"user_id\": 1, \"candidates\": [{\"movie_id\": 101, \"year\": 2023, \"genre\": \"Action\"}, {\"movie_id\": 102, \"year\": 2022, \"genre\": \"Comedy\"}, {\"movie_id\": 103, \"year\": 2024, \"genre\": \"Drama\"}], \"top_n\": 2}"
```

**Response:**

```json
{"task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
```

Получение статуса задачи

```bash
curl "http://127.0.0.1:8000/api/v1/movies/results/{task_id}"
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
poetry run pytest tests/test_async.py -v
```

## Управление данными

DVC используется для версионирования данных. Основные команды:

- **Загрузить данные:** `poetry run dvc pull`
- **Проверить статус:** `poetry run dvc status`
- **Откатить до предыдущей версии:** `poetry run dvc checkout`

Данные версионируются автоматически при добавлении `.dvc` файлов в репозиторий.

