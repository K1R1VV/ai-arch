# Clean Architecture AI Project

## Структура проекта

Проект организован в соответствии с принципами Чистой Архитектуры:

- **src/domain**: Сущности и интерфейсы. Ядро системы.
- **src/application**: Бизнес-логика (Use Cases).
- **src/infrastructure**: Реализация интерфейсов (Mock-модели, работа с БД/файлами).
- **src/presentation**: Точка входа (CLI).

## Запуск

1. Установка зависимостей:

   ```bash
   poetry install
   ```

2. Запуск CLI:

   ```bash
   poetry run python -m src.presentation.cli
   ```

3. Запуск тестов:
   ```bash
   poetry run pytest
   ```

### Для тестов использовать

```bash
poetry run python -m src.presentation.cli --age 45 --cholesterol 4.8 --heart-rate 72
```

#### или

```bash
   poetry run pytest tests/test_cli.py -v -s
```
