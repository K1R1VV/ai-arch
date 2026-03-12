#!/usr/bin/env python
import subprocess
import sys
from pathlib import Path
import pandas as pd


def run_dvc_pull():
    print("[Setup] Запуск синхронизации данных через DVC...")
    print("[Setup] Выполняю команду: dvc pull")
    
    try:
        result = subprocess.run(
            ["dvc", "pull"],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("[Setup] Данные успешно загружены")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print("[Setup] Ошибка при загрузке данных:")
            if result.stderr:
                print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("[Setup] Ошибка: DVC не найден. Установите DVC выполнив: pip install dvc")
        return False
    except Exception as e:
        print(f"[Setup] Неожиданная ошибка: {e}")
        return False


def check_data_directory():
    data_dir = Path("data")
    if not data_dir.exists():
        print(f"[Setup] Создаю директорию: data/")
        data_dir.mkdir(parents=True, exist_ok=True)
    return True


def main():
    print("Подготовка данных для проекта")
    
    if not check_data_directory():
        sys.exit(1)
    
    success = run_dvc_pull()
    
    if success:
        print("Подготовка завершена успешно!")
        print("Теперь вы можете запустить приложение:")
        print("poetry run python -m src.presentation.cli <user_id>")
        print("poetry run uvicorn src.presentation.api:app --reload")
        sys.exit(0)
    else:
        print("Ошибка при подготовке данных")
        sys.exit(1)


if __name__ == "__main__":
    main()
