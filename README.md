[![Movie Recommender CI/CD](https://github.com/K1R1VV/ai-arch/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/K1R1VV/ai-arch/actions/workflows/ci.yml)

# Лабораторная работа №5: Вариант 10 (Система рекомендаций фильмов)

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

### 2. Установка зависимостей

```bash
poetry install
```

### 3. Запуск сервиса

Запустим всю систему

```bash
docker-compose up -d --build
```

### 4. Обучение модели

Для справки: в качестве алгоритма используется RandomForestRegressor, поэтому embedding_size не логируется

```bash
poetry run python scripts/train_model.py
```

**FastAPI сервер (рекомендации через HTTP API):**

Сервер запущен через докер, API доступно по адресу `http://localhost:8000`

## API Endpoints

### POST /api/v1/movies/predict_rating_async

Если при запросах в ответ приходит

```json
{
  "error": "service_unavailable",
  "detail": "Model is not initialized. Please train and register a model first.",
  "hint": "Run: poetry run python scripts/train_model.py",
  "mlflow_ui": "http://mlflow:5000"
}
```

Необходимо выполнить запрос:

```bash
curl -X POST "http://127.0.0.1:8000/admin/reload-model"
```

Предсказать рейтинг

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/movies/predict_rating_async" -H "Content-Type: application/json" -d "{\"user_id\": 123, \"movie_id\": 456, \"year\": 2023, \"genre\": \"Sci-Fi\"}"
```

**Response:**

```json
{ "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" }
```

Получение статуса задачи

```bash
curl "http://127.0.0.1:8000/api/v1/movies/results/{task_id}"
```

**Response:**

```json
{
  "task_id": "9b55e844-e26f-4fae-a389-fc0d6914c1f0",
  "status": "SUCCESS",
  "result": {
    "user_id": 123,
    "movie_id": 456,
    "predicted_rating": 3.41
  },
  "error": null
}
```

---

### POST /api/v1/movies/recommend_for_user

Получить рекомендации для пользователя

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/movies/recommend_for_user" -H "Content-Type: application/json" -d "{\"user_id\": 1, \"candidates\": [{\"movie_id\": 101, \"year\": 2023, \"genre\": \"Action\"}, {\"movie_id\": 102, \"year\": 2022, \"genre\": \"Comedy\"}, {\"movie_id\": 103, \"year\": 2024, \"genre\": \"Drama\"}], \"top_n\": 2}"
```

**Response:**

```json
{ "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" }
```

Получение статуса задачи

```bash
curl "http://127.0.0.1:8000/api/v1/movies/results/{task_id}"
```

**Response:**

```json
{
  "task_id": "3de9f630-031b-4866-b1c2-79a956c8b908",
  "status": "SUCCESS",
  "result": {
    "user_id": 1,
    "recommendations": [
      {
        "movie_id": 103,
        "predicted_score": 2.94,
        "reason": "Predicted by ONNX model"
      },
      {
        "movie_id": 102,
        "predicted_score": 2.78,
        "reason": "Predicted by ONNX model"
      }
    ]
  },
  "error": null
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
poetry run pytest tests/test_async.py -v
```

## Управление данными

DVC используется для версионирования данных. Основные команды:

- **Загрузить данные:** `poetry run dvc pull`
- **Проверить статус:** `poetry run dvc status`
- **Откатить до предыдущей версии:** `poetry run dvc checkout`

Данные версионируются автоматически при добавлении `.dvc` файлов в репозиторий.

## Model Registry

Для управления версиями модели используется [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html).

- Модель регистрируется под именем `movie_recommender`
- Для production-использования назначается алиас `production`:

```bash
  models:/movie_recommender@production
```

## Полный цикл: проверка и переключение модели на Production (GitHub)

### 1 Настройка GitHub Secrets

Перейдите в репозиторий - **Settings** - **Secrets and variables** - **Actions** - **New repository secret**:

| Secret                | Описание                                        | Пример                         |
| --------------------- | ----------------------------------------------- | ------------------------------ |
| `MLFLOW_TRACKING_URI` | Адрес внешнего MLflow-сервера                   | `http://<your-mlflow-ip>:5000` |
| `MLFLOW_USERNAME`     | Логин для MLflow (если включена аутентификация) | `admin`                        |
| `MLFLOW_PASSWORD`     | Пароль для MLflow                               | `***`                          |

---

### 2 Развёртывание внешнего MLflow-сервера

MLflow должен быть доступен **и из GitHub Actions, и из production-окружения**.

```bash
mkdir -p ~/mlflow/{artifacts,db}

docker run -d \
  --name mlflow-prod \
  -p 5000:5000 \
  -v ~/mlflow/artifacts:/mlflow/artifacts \
  -v ~/mlflow/db:/mlflow/db \
  --restart unless-stopped \
  ghcr.io/mlflow/mlflow:v2.11.3 \
  mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri sqlite:////mlflow/db/mlflow.db \
    --artifacts-destination file:///mlflow/artifacts \
    --serve-artifacts
```

### 3 Коммит и пуш в ветку main

```bash
git add .
git commit -m "feat: подготовка к production-деплою"
git push origin main
```

### 4 Проверка пайплайна в гитхаб

Все стадии должны пройти успешно

### 5 Проверка MLflow и переключение модели на Production

1. Откройте веб-интерфейс: http://<your-mlflow-ip>:5000
2. Перейдите в Experiments - Movie Recommendation
3. Найдите последний run с метрикой rmse < 0.9
4. Перейдите в Models - movie_recommender
5. Выберите последнюю версию - секция Aliases
6. Нажмите Edit - добавьте алиас production - Save

### 6 Обновление production-системы

1. Обновите переменные окружения (если изменился адрес MLflow)

```bash
echo "MLFLOW_TRACKING_URI=http://<your-mlflow-ip>:5000" > .env
```

2. Скачайте production compose-файл (если ещё не создан)

```bash
curl -O https://raw.githubusercontent.com/K1R1VV/ai-arch/main/docker-compose.prod.yml
```

3. Обновите систему — образы скачаются из GHCR автоматически

```bash
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

4. Проверьте, что воркер загрузил новую модель

```bash
docker-compose -f docker-compose.prod.yml logs worker | grep "Модель скачана из MLflow"
```
