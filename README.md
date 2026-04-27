# Лабораторная работа №6: Вариант 10 (Кулинарный RAG-ассистент)

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

После создания .env файла необходимо заполнить ключи

### 2. Установка зависимостей

```bash
uv venv venv
venv\Scripts\activate
uv pip install -r requirements.txt
```


### 3. Запуск сервиса

```bash
docker-compose up -d qdrant
```

### 4. Индексация

```bash
uv indexer.py
```

### 5. Запуск сервиса

```bash
docker-compose up -d
```

**FastAPI сервер (рекомендации через HTTP API):**

Сервер запущен через докер, API доступно по адресу `http://localhost:8000`

## API Endpoints

### POST /qa

Предсказать рейтинг

```bash
curl -X POST "http://127.0.0.1:8000/qa" -H "Content-Type: application/json" -d "{\"question\": \"Что можно быстро приготовить из курицы и риса? Сложность легкая\"}"
```

**Response:**

```json
{ "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890" }
```

## Запуск тестов

```bash
uv run pytest tests/ -v
```

Для запуска с дополнительной информацией:

```bash
uv run pytest tests/ -v -s
```
