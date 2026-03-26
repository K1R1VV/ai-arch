import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType, StringTensorType


def load_or_create_data(DATA_FILE):
    if os.path.exists(DATA_FILE):
        print(f"Загрузка данных из {DATA_FILE}...")
        try:
            df = pd.read_csv(DATA_FILE)
            required_cols = ['user_id', 'movie_id', 'genre', 'year', 'rating']
            if not all(col in df.columns for col in required_cols):
                raise ValueError("В файле отсутствуют необходимые колонки.")
            return df
        except Exception as e:
            print(f"Ошибка чтения {DATA_FILE}: {e}. Генерация случайных данных...")
    
    print("Файл ratings.csv не найден. Генерация случайных данных...")
    np.random.seed(42)
    data = {
        'user_id': np.random.randint(1, 100, 500),
        'movie_id': np.random.randint(1, 200, 500),
        'genre': np.random.choice(['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror'], 500),
        'year': np.random.randint(1990, 2024, 500),
        'rating': np.random.uniform(1.0, 5.0, 500)
    }
    df = pd.DataFrame(data)
    df.to_csv(DATA_FILE, index=False)
    print(f"Случайные данные сохранены в {DATA_FILE}")
    return df

def train_and_convert(DATA_FILE):
    print("Обучение модели рекомендаций фильмов")
    df = load_or_create_data(DATA_FILE=DATA_FILE)

    numeric_features = ['user_id', 'movie_id', 'year']
    categorical_features = ['genre']
    
    X = df[numeric_features + categorical_features]
    y = df['rating'].values
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ],
        remainder='passthrough'
    )
    
    model = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42))
    ])
    
    model.fit(X, y)

    test_data = pd.DataFrame({
        'user_id': [1],
        'movie_id': [101],
        'year': [2023],
        'genre': ['Action']
    })
    sklearn_pred = model.predict(test_data)[0]
    print(f"Предсказание Sklearn: rating={sklearn_pred:.2f}")

    print("Конвертация модели в ONNX...")

    initial_types = [
        ('user_id', FloatTensorType([None, 1])),
        ('movie_id', FloatTensorType([None, 1])),
        ('year', FloatTensorType([None, 1])),
        ('genre', StringTensorType([None, 1]))
    ]
    
    try:
        onnx_model = convert_sklearn(model, initial_types=initial_types)
    except Exception as e:
        print(f"Ошибка конвертации: {e}")
        print("Убедитесь, что установлены свежие версии: pip install -U skl2onnx onnx")
        return None

    output_dir = "models"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "movie_recommender.onnx")
    
    with open(output_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    
    print(f"Модель успешно сохранена: {output_path}")
    print(f"Размер файла: {os.path.getsize(output_path) / 1024:.2f} KB")
    
    try:
        import onnxruntime as ort
        
        session = ort.InferenceSession(output_path)

        input_feed = {
            'user_id': np.array([[1]], dtype=np.float32),
            'movie_id': np.array([[101]], dtype=np.float32),
            'year': np.array([[2023]], dtype=np.float32),
            'genre': np.array([['Action']], dtype=np.str_)
        }
        
        onnx_pred_raw = session.run(None, input_feed)[0][0]
        onnx_pred = onnx_pred_raw.item()
        print(f"Предсказание ONNX: rating={onnx_pred:.2f}")
        print(f"Совпадение предсказаний: {np.isclose(sklearn_pred, onnx_pred)}")
        
    except ImportError:
        print("onnxruntime не установлен. Пропускаем тест.")
    except Exception as e:
        print(f"Ошибка при тестировании ONNX: {e}")

    return output_path

if __name__ == "__main__":
    train_and_convert('data/ratings.csv')