import os, json, logging
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

os.environ['HF_HOME'] = os.path.abspath(os.path.join(os.path.dirname(__file__), 'hf_cache'))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QDRANT_HOST = "localhost"
COLLECTION_NAME = "chef_recipes"
DOCS_PATH = "./docs/recipes"
EMBEDDING_MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'

client = QdrantClient(host=QDRANT_HOST, port=6333)
model = SentenceTransformer(EMBEDDING_MODEL)

def load_recipes(path):
    recipes = []
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        sample = [{
            "title": "Курица с рисом по-домашнему",
            "ingredients": ["куриное филе", "рис", "лук", "морковь", "соль", "специи"],
            "cooking_time": "45 минут", "difficulty": "легко",
            "steps": "1. Отварите рис. 2. Обжарьте курицу с овощами. 3. Смешайте."
        }]
        with open(os.path.join(path, "sample.json"), "w", encoding="utf-8") as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
        return sample

    for f in os.listdir(path):
        if f.endswith(".json"):
            with open(os.path.join(path, f), 'r', encoding='utf-8') as file:
                data = json.load(file)
                recipes.extend(data if isinstance(data, list) else [data])
    return recipes

def main():
    try:
        if any(c.name == COLLECTION_NAME for c in client.get_collections().collections):
            client.delete_collection(COLLECTION_NAME)
        client.create_collection(COLLECTION_NAME, vectors_config=models.VectorParams(
            size=model.get_sentence_embedding_dimension(), distance=models.Distance.COSINE
        ))
        
        recipes = load_recipes(DOCS_PATH)
        if not recipes:
            logger.warning("Рецепты не найдены.")
            return

        points = []
        for i, r in enumerate(recipes):
            text_for_emb = f"{r.get('title')} {', '.join(r.get('ingredients',[]))} {r.get('steps')}"
            points.append(models.PointStruct(
                id=i,
                vector=model.encode(text_for_emb).tolist(),
                payload={
                    "title": r.get("title"), "ingredients": r.get("ingredients",[]),
                    "cooking_time": r.get("cooking_time"), "difficulty": r.get("difficulty"),
                    "steps": r.get("steps"), "text": text_for_emb
                }
            ))
        
        client.upload_points(COLLECTION_NAME, points=points, wait=True)
        logger.info(f"Индексация завершена! Загружено {len(points)} рецептов.")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

if __name__ == "__main__":
    main()