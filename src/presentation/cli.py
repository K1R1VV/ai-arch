import sys
from src.application.services import RecommendationService

def main():
    rec_service = RecommendationService(data_path="data/ratings.csv")
    user_id = 1
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
        except ValueError:
            print("Invalid user_id. Using default 1.")
            
    print(f"Running recommendations for User ID: {user_id}")
    results = rec_service.get_recommendations(user_id)

    if not results:
        print("No recommendations found.")
    else:
        for rec in results:
            print(f"Movie ID: {rec.movie_id}, Score: {rec.predicted_score}")


if __name__ == "__main__":
    main()