import pandas as pd
from pathlib import Path
from typing import List
from src.domain.entities import Rating, Recommendation

class IMovieRecommender:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.df: pd.DataFrame = pd.DataFrame()
        self._load_data()

    def _load_data(self) -> None:
        path = Path(self.data_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {self.data_path}")
        
        self.df = pd.read_csv(path)
        if self.df['rating'].min() < 0 or self.df['rating'].max() > 5:
            print("[Warning] Detected potential noisy data in ratings (out of 0-5 range)")

    def get_user_history(self, user_id: int) -> List[int]:
        user_data = self.df[self.df['user_id'] == user_id]
        return user_data['movie_id'].tolist()

    def recommend(self, user_id: int, top_n: int = 3) -> List[Recommendation]:
        if self.df.empty:
            return []

        viewed_movies = set(self.get_user_history(user_id))
    
        candidates = self.df[~self.df['movie_id'].isin(viewed_movies)]
        
        if candidates.empty:
            candidates = self.df

        agg = candidates.groupby('movie_id')['rating'].mean().reset_index()
        agg.columns = ['movie_id', 'predicted_score']

        agg = agg.sort_values(by='predicted_score', ascending=False).head(top_n)
        
        results = []
        for _, row in agg.iterrows():
            results.append(Recommendation(
                movie_id=int(row['movie_id']),
                predicted_score=round(float(row['predicted_score']), 2),
                reason="Top rated by community"
            ))
            
        return results