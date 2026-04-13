import os
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import mlflow
import mlflow.onnx
from mlflow.tracking import MlflowClient


MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment("Movie Recommendation")


def generate_data(n=500, seed=42):
    np.random.seed(seed)
    df = pd.DataFrame({
        'user_id': np.random.randint(1, 100, n),
        'movie_id': np.random.randint(1, 200, n),
        'genre': np.random.choice(['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror'], n),
        'year': np.random.randint(1990, 2024, n)
    })
    signal = 2.0 + 0.5 * (df['user_id'] % 5) + 0.2 * (df['movie_id'] % 3)
    noise = np.random.normal(0, 0.4, n)
    df['rating'] = np.clip(signal + noise, 1.0, 5.0).round(2)
    return df


def train():
    df = generate_data()
    df['genre_encoded'] = LabelEncoder().fit_transform(df['genre'])
    
    numeric_features = ['user_id', 'movie_id', 'year', 'genre_encoded']
    X = df[numeric_features].astype(np.float32)
    y = df['rating'].values
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    params = {"n_estimators": 50, "max_depth": 5, "random_state": 42}
    
    with mlflow.start_run() as run:
        mlflow.log_params(params)
        model = RandomForestRegressor(**params)
        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        mlflow.log_metric("rmse", rmse)
        print(f"RMSE на тесте: {rmse:.4f}")

        initial_types = [
            ('float_input', FloatTensorType([None, len(numeric_features)])),
        ]
        
        try:
            onnx_model = convert_sklearn(
                model,
                initial_types=initial_types,
                target_opset=12,
                name="movie_recommender"
            )
        except Exception as e:
            print(f"Ошибка конвертации: {e}")
            print("Убедитесь: initial_types содержит ОДИН вход с shape [None, n_features]")
            return

        print("Регистрация модели в MLflow...")
        model_info = mlflow.onnx.log_model(
            onnx_model,
            artifact_path="model",
            registered_model_name="movie_recommender",
        )
        
        print("Назначение алиаса 'production'...")
        client = MlflowClient()
        client.set_registered_model_alias(
            name="movie_recommender",
            alias="production",
            version=model_info.registered_model_version
        )
        
        print(f"Модель зарегистрирована: версия {model_info.registered_model_version}")
        print(f"Run ID: {run.info.run_id}")
        print(f"MLflow UI: http://localhost:5000/#/experiments/{run.info.experiment_id}/runs/{run.info.run_id}")


if __name__ == "__main__":
    train()