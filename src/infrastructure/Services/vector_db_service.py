import logging
from typing import List
from qdrant_client import QdrantClient, models
from src.Domain.Interfaces.i_vector_db_service import IVectorDbService

logger = logging.getLogger(__name__)

class VectorDbService(IVectorDbService):
    def __init__(self):
        self.client = QdrantClient(host="qdrant", port=6333, check_compatibility=False)
        self.collection_name = "chef_recipes"
        logger.info("VectorDbService initialized")

    def search(self, query_vector: List[float], limit: int) -> List[dict]:
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True
            ).points
            return [{"id": p.id, "score": p.score, "payload": p.payload} for p in results]
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            raise