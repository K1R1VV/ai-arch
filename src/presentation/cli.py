import sys
import pandas as pd
from pathlib import Path
from src.application.services import RecommendationService
from src.infrastructure.onnx_model import ONNXMovieRecommender


def load_candidate_movies(data_path: str, exclude_user_id: int = None) -> list[dict]:
    path = Path(data_path)
    if not path.exists():
        print(f"[CLI] Warning: {data_path} not found. Using empty candidate list.")
        return []
    
    try:
        df = pd.read_csv(path)
        if exclude_user_id is not None:
            viewed = set(df[df['user_id'] == exclude_user_id]['movie_id'].tolist())
            candidates_df = df[~df['movie_id'].isin(viewed)]
        else:
            candidates_df = df
        
        unique_movies = candidates_df['movie_id'].unique()
        candidates = []
        for mid in unique_movies:
            year = 2023
            movie_rows = df[df['movie_id'] == mid]
            if 'year' in movie_rows.columns and not movie_rows['year'].isna().all():
                year = int(movie_rows['year'].dropna().iloc[0])
            
            candidates.append({'movie_id': int(mid), 'year': year})
        
        print(f"[CLI] Загружено {len(candidates)} фильмов-кандидатов")
        return candidates
    except Exception as e:
        print(f"[CLI] Error loading candidates: {e}")
        return []


def main():
    data_path = "data/ratings.csv"
    model_path = "models/movie_recommender.onnx"
    
    if not Path(model_path).exists():
        print(f"[CLI] ERROR: Модель не найдена: {model_path}")
        print("[CLI] Выполните синхронизацию модели:")
        print("  poetry run python scripts/setup_data.py")
        print("  poetry run dvc pull")
        print("  Или через API: POST /api/v1/model/sync")
        sys.exit(1)
    try:
        print(f"[CLI] Загрузка ONNX модели: {model_path}")
        model = ONNXMovieRecommender(model_path=model_path)
    except Exception as e:
        print(f"[CLI] ERROR: Не удалось загрузить модель: {e}")
        sys.exit(1)
    
    rec_service = RecommendationService(model=model)
    
    user_id = 1
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
        except ValueError:
            print("[CLI] Invalid user_id. Using default 1.")
    
    print(f"\n[CLI] Генерация рекомендаций для User ID: {user_id}")

    candidates = load_candidate_movies(data_path, exclude_user_id=user_id)
    if not candidates:
        print("[CLI] ERROR: Нет фильмов-кандидатов для рекомендации")
        sys.exit(1)

    try:
        results = rec_service.get_recommendations(
            user_id=user_id,
            candidate_movies=candidates,
            top_n=3
        )
    except Exception as e:
        print(f"[CLI] ERROR при генерации рекомендаций: {e}")
        sys.exit(1)
    
    if not results:
        print("[CLI] No recommendations found for this user.")
    else:
        print(f"[CLI] Топ-{len(results)} рекомендаций:")
        for i, rec in enumerate(results, 1):
            print(f"{i}. Movie ID: {rec.movie_id:4d} | "
                  f"Score: {rec.predicted_score:.2f} | "
                  f"Reason: {rec.reason}")

if __name__ == "__main__":
    main()