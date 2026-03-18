import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType


def create_training_data():
    np.random.seed(42)
    
    data = {
        'user_id': np.random.randint(1, 100, 500),
        'movie_id': np.random.randint(1, 200, 500),
        'genre': np.random.choice(['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror'], 500),
        'year': np.random.randint(1990, 2024, 500),
        'rating': np.random.uniform(1.0, 5.0, 500)
    }
    
    df = pd.DataFrame(data)
    return df


def train_and_convert():
    print("Обучение модели рекомендаций фильмов")

    df = create_training_data()

    X = df[['user_id', 'movie_id', 'year']]
    y = df['rating'].values
    
    genre = df[['genre']]
    preprocessor = ColumnTransformer(
        transformers=[
            ('genre', OneHotEncoder(handle_unknown='ignore'), ['genre'])
        ],
        remainder='passthrough'
    )
    
    model = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42))
    ])
    
    X_combined = pd.concat([X, genre], axis=1)
    model.fit(X_combined, y)

    test_sample = pd.DataFrame({
        'user_id': [1],
        'movie_id': [101],
        'year': [2023],
        'genre': ['Action']
    })
    test_pred = model.predict(test_sample)[0]
    print(f"Тестовое предсказание: user=1, movie=101 → rating={test_pred:.2f}")
    
    initial_type = [('float_input', FloatTensorType([None, 6]))]  # 3 числовых + 3 one-hot (упрощённо)
    
    simple_model = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
    simple_model.fit(X, y)
    
    initial_type = [('float_input', FloatTensorType([None, X.shape[1]]))]
    onnx_model = convert_sklearn(simple_model, initial_types=initial_type)

    output_dir = "models"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "movie_recommender.onnx")
    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    
    print(f"Модель успешно сохранена: {output_path}")
    print(f"Размер файла: {os.path.getsize(output_path) / 1024:.2f} KB")
    
    return output_path


if __name__ == "__main__":
    train_and_convert()