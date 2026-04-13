import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_squared_error


def check_quality():
    print("Запуск Quality Gate: проверка RMSE...")
    np.random.seed(42)
    df = pd.DataFrame({
        'user_id': np.random.randint(1, 100, 500),
        'movie_id': np.random.randint(1, 200, 500),
        'genre': np.random.choice(['Action', 'Comedy', 'Drama', 'Sci-Fi', 'Horror'], 500),
        'year': np.random.randint(1990, 2024, 500)
    })
    signal = 2.0 + 0.5 * (df['user_id'] % 5) + 0.2 * (df['movie_id'] % 3)
    noise = np.random.normal(0, 0.4, 500)
    df['rating'] = np.clip(signal + noise, 1.0, 5.0).round(2)
    
    df['genre_encoded'] = LabelEncoder().fit_transform(df['genre'])
    features = ['user_id', 'movie_id', 'year', 'genre_encoded']
    X = df[features].astype(np.float32)
    y = df['rating'].values
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    print(f"Текущий RMSE: {rmse:.4f}")
    
    if rmse >= 0.9:
        print(f"[ERROR] Quality Gate FAILED: RMSE {rmse:.4f} не удовлетворяет порогу < 0.9")
        sys.exit(1)
    else:
        print("[SUCCESS] Quality Gate PASSED!")
        sys.exit(0)


if __name__ == "__main__":
    check_quality()