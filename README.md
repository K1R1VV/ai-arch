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
0. **Создание .env файла:**

Линукс
```bash
   cp .env.example .env
```

CMD (Windows)
```bash
   copy .env.example .env
```

1. **Запуск инфраструктуры:**

```bash
   docker-compose up -d
```

2. **Установка зависимостей:**

```bash
   poetry install
```

3. **Настройка DVC и загрузка данных:**

```bash
   poetry run dvc init
   poetry run dvc remote add -d storage s3://datasets
   poetry run dvc remote modify storage endpointurl http://localhost:9000
   poetry run dvc remote modify storage access_key_id minioadmin
   poetry run dvc remote modify storage secret_access_key minioadmin

   # Загрузка демо-данных в MinIO
   poetry run python scripts/init_minio.py
```

4. **Коммит чистых данных:**

```bash
   poetry run dvc add data/ratings.csv
   git add data/ratings.csv.dvc .gitignore
   git commit -m "v1.0: Clean dataset initialization"
   poetry run dvc push
```

5. **Имитация "Шумных" данных (Версия 2.0):**
Для линукс
```bash
    # 1. Добавляем шумные данные в файл
   echo "99,999,10.0" >> data/ratings.csv
   echo "98,998,-5.0" >> data/ratings.csv
```

Для CMD
```bash
   # 1. Добавляем шумные данные в файл
   echo 99,999,10.0 >> data/ratings.csv
   echo 98,998,-5.0 >> data/ratings.csv
```

```bash
    # 2. Фиксируем новую версию
    poetry run dvc add data/ratings.csv
    git add data/ratings.csv.dvc
    git commit -m "v2.0: Added noisy data (simulation)"
    poetry run dvc push
```

6. **Запуск для теста:**

```bash
   poetry run python -m src.presentation.cli 1  
```

#### Вместо <user_id> можно подставить другой user_id 

```bash
   poetry run python -m src.presentation.cli <user_id> #CLI
```

7. **Откат к чистой версии:**

```bash
    # 1. Смотрим историю коммитов
   git log --oneline
```

```bash
   # 2. Откатываем Git к предыдущему коммиту (замените HASH на хеш коммита v1.0)
   git checkout <HASH_COMMIT_V1.0>
```

```bash
   # 3. Восстанавливаем версию файла данных согласно этому коммиту
   poetry run dvc checkout
```
Для линукс
```bash
   # 4. Проверяем файл (шумных строк 99,999 и 98,998 больше нет)
   cat data/ratings.csv
```

Для CMD
```bash
   type data\ratings.csv
```

```bash
    # 5. Запускаем приложение (теперь без предупреждений)
   poetry run python -m src.presentation.cli 1
```
#### Вместо <user_id> можно подставить другой user_id 

```bash
   poetry run python -m src.presentation.cli <user_id> #CLI
```

7. **Возврат в основную ветку:**

```bash
   git checkout main
   poetry run dvc checkout
```

8. **Общий запуск:**

```bash
   poetry run python -m src.presentation.cli <user_id> #CLI
```

```bash
   poetry run uvicorn src.presentation.api:app --reload #API
```


8. **Запуск тестов:**

```bash
   poetry run pytest tests/test_cli.py -v -s
```