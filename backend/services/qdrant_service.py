import os
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv()

# Module-level client 
_host = os.getenv("QDRANT_HOST", "localhost")
_port = int(os.getenv("QDRANT_PORT", 6333))

client = QdrantClient(host=_host, port=_port)

# Vector dimension produced by all-MiniLM-L6-v2
_VECTOR_SIZE = 384

def _collection_name(bot_id: str) -> str:
    return f"bot_{bot_id}"

# Public API
def create_collection(bot_id: str) -> None:
    """
    Create a Qdrant collection for the given bot.
    If the collection already exists, this is a no-op.
    """
    name = _collection_name(bot_id)
    
    # Check if collection already exists to avoid redundant creation attempts
    if client.collection_exists(collection_name=name):
        return

    try:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
        )
    except UnexpectedResponse as exc:
        # Fallback: 409 Conflict means the collection already exists (race condition)
        if exc.status_code == 409:
            return
        raise


def upsert_chunks(
    bot_id: str,
    chunks: list,
    embeddings: list,
    images_list: list = None,
) -> None:
    """
    Upsert text chunks and their embeddings into the bot's collection.

    Args:
        bot_id:      Identifier of the bot (used to derive the collection name).
        chunks:      List of raw text chunks.
        embeddings:  Corresponding list of embedding vectors.
        images_list: Optional per-chunk list of image URLs. If omitted or shorter
                     than chunks, missing entries default to an empty list.
    """
    name = _collection_name(bot_id)
    if images_list is None:
        images_list = []
    points = [
        PointStruct(
            id=uuid.uuid4().hex,
            vector=embedding,
            payload={
                "text": chunk,
                "images": images_list[i] if i < len(images_list) else [],
            },
        )
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]
    client.upsert(collection_name=name, points=points)


def search_similar(
    bot_id: str,
    query_embedding: list,
    top_k: int = 4,
) -> list:
    """
    Return the top-k most similar scored points for the given query embedding.
    Each returned object has a .payload dict with 'text' and 'images' keys.

    Args:
        bot_id:          Identifier of the bot.
        query_embedding: Embedding vector of the query.
        top_k:           Number of results to return (default 4).

    Returns:
        A list of ScoredPoint objects from the matched points.
    """
    name = _collection_name(bot_id)
    results = client.query_points(
        collection_name=name,
        query=query_embedding,
        limit=top_k,
        with_payload=True,
    )
    return results.points


def delete_collection(bot_id: str) -> None:
    """
    Delete the Qdrant collection associated with the given bot.

    Args:
        bot_id: Identifier of the bot whose collection should be removed.
    """
    client.delete_collection(collection_name=_collection_name(bot_id))
