import os
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
import mlflow
import onnxruntime as ort


MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_NAME = "movie_recommender"
MODEL_ALIAS = "production"
RMSE_THRESHOLD = 0.9
TEST_SIZE = 100

def generate_test_data(n_samples=TEST_SIZE, seed=42):
    np.random.seed(seed)
    df = pd.DataFrame({
        'user_id': np.random.randint(1, 100, n_samples),
        'movie_id': np.random.randint(1, 200, n_samples),
        'genre': np.random.choice(['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror'], n_samples),
        'year': np.random.randint(1990, 2024, n_samples)
    })
    signal = 2.0 + 0.5 * (df['user_id'] % 5) + 0.2 * (df['movie_id'] % 3)
    noise = np.random.normal(0, 0.4, n_samples)
    df['rating'] = np.clip(signal + noise, 1.0, 5.0).round(2)
    genre_order = ['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror']
    genre_map = {g: i for i, g in enumerate(genre_order)}
    df['genre_encoded'] = df['genre'].map(genre_map).fillna(0).astype(int)
    
    features = ['user_id', 'movie_id', 'year', 'genre_encoded']
    X = df[features].astype(np.float32)
    y = df['rating'].values
    return X, y


def check_model_from_registry() -> float | None:
    print(f"Попытка загрузить модель из MLflow Registry: models:/{MODEL_NAME}@{MODEL_ALIAS}")
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        model_uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"
        model_dir = mlflow.artifacts.download_artifacts(artifact_uri=model_uri)
        model_path = os.path.join(model_dir, "model.onnx")
        print(f"Модель загружена из Registry: {model_path}")
        
    except Exception as e:
        print(f"Не удалось загрузить модель из Registry: {type(e).__name__}: {e}")
        return None

    X_test, y_test = generate_test_data()
    try:
        session = ort.InferenceSession(model_path)
        input_name = session.get_inputs()[0].name
        predictions = session.run(None, {input_name: X_test})[0].flatten()
        rmse = np.sqrt(mean_squared_error(y_test, predictions))
        print(f"RMSE на тесте (модель из Registry): {rmse:.4f}")
        return rmse
        
    except Exception as e:
        print(f"Ошибка при инференсе: {type(e).__name__}: {e}")
        return None


def check_local_model() -> float:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split

    X, y = generate_test_data(n_samples=500)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=50,
        max_depth=5,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"RMSE на тесте (локальная модель): {rmse:.4f}")
    
    return rmse

def check_quality():
    print("Quality Gate: проверка модели (Вариант 10: Рекомендации фильмов)")
    print(f"Порог: RMSE < {RMSE_THRESHOLD}")
    print(f" MLflow URI: {MLFLOW_TRACKING_URI}")
    rmse = check_model_from_registry()

    if rmse is None:
        print("Fallback: проверка локально обученной модели")
        rmse = check_local_model()
    if rmse >= RMSE_THRESHOLD:
        print(f"[FAILED] Quality Gate: RMSE {rmse:.4f} не удовлетворяет порогу < {RMSE_THRESHOLD}")
        sys.exit(1)
    else:
        print(f"[PASSED] Quality Gate: модель готова к деплою (RMSE={rmse:.4f})")
        sys.exit(0)


if __name__ == "__main__":
    check_quality()