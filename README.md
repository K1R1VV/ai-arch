# Лабораторная работа №2: Вариант 10 (Система рекомендаций фильмов)

## Описание

Проект реализует систему рекомендаций фильмов с использованием Clean Architecture.
Данные версионируются через DVC и хранятся в S3-совместимом хранилище MinIO.

## Стек

- Python 3.10+
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

### 4. Инициализация и настройка dvc:

```bash
   poetry run dvc init
   poetry run dvc remote add -d storage s3://datasets
   poetry run dvc remote modify storage endpointurl http://localhost:9000
   poetry run dvc remote modify storage access_key_id minioadmin
   poetry run dvc remote modify storage secret_access_key minioadmin
```

### 5. Инициализация MinIO (только первый раз)

Если в MinIO ещё нет данных, загрузите их:

```bash
poetry run python scripts/init_minio.py
```

Это создаст бакет `datasets` и загрузит демо-данные `data/ratings.csv`.

### 6. Подготовка данных

Скачайте данные из MinIO в локальный проект:

```bash
poetry run python scripts/setup_data.py
```

Эта команда выполнит `dvc pull` и загрузит данные в папку `data/`

Или вручную через DVC:

```bash
poetry run dvc pull
```

### 7. Запуск приложения

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

### POST /recommend

Получить рекомендации для пользователя

**Request:**

```json
{
  "user_id": 1
}
```

**Response:**

```json
[
  {
    "movie_id": 105,
    "predicted_score": 4.8,
    "reason": "Based on your ratings"
  }
]
```

### POST /api/v1/data/sync

Синхронизировать данные с MinIO (опционально)

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
  "message": "Данные синхронизированы: data/ratings.csv"
}
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
```

## Управление данными

DVC используется для версионирования данных. Основные команды:

- **Загрузить данные:** `poetry run dvc pull`
- **Проверить статус:** `poetry run dvc status`
- **Откатить до предыдущей версии:** `poetry run dvc checkout`

Данные версионируются автоматически при добавлении `.dvc` файлов в репозиторий.

