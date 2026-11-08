
from dotenv import load_dotenv
from pathlib import Path
from qdrant_client import QdrantClient
import requests
import os

# Load environment variables
load_dotenv()

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL")

print(QDRANT_URL)
print(QDRANT_API_KEY)
print(EMBEDDING_API_URL)

COLLECTION_NAME = "rag_documents_v2"

# Connect to Qdrant
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)


def generate_query_embedding(query):

    response = requests.post(
        f"{EMBEDDING_API_URL}/embed",
        json={"texts": [query]},
        timeout=120
    )

    response.raise_for_status()

    embeddings = response.json()["embeddings"]

    return embeddings[0]


def retrieve_chunks(query, limit=5):

    # Step 1: Generate query embedding
    query_vector = generate_query_embedding(query)

    # Step 2: Search Qdrant
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True
    )

    retrieved_chunks = []

    # Step 3: Collect results
    for index, point in enumerate(results.points, start=1):

        payload = point.payload or {}
        metadata = payload.get("metadata", {})

        # Get the common chunk ID
        chunk_id = metadata.get("chunk_id") or payload.get("chunk_id")

        if chunk_id is None:
            raise ValueError(
                f"chunk_id missing in Qdrant payload for point {point.id}. "
                "Add chunk_id to the Qdrant payload."
            )

        chunk = {
            "chunk_id": str(chunk_id),
            "text": payload.get("text", ""),
            "metadata": metadata,
            "dense_score": float(point.score),
            "dense_rank": index
        }

        retrieved_chunks.append(chunk)

        # Display results
        print(f"\n{'=' * 60}")
        print(f"RESULT {index}")
        print(f"Similarity score: {point.score:.4f}")
        print(f"Chunk ID: {chunk_id}")
        print("\nChunk text:")
        print(payload.get("text", ""))
        print("\nMetadata:")
        print(metadata)

    return retrieved_chunks

if __name__ == "__main__":

    user_query = input("Enter your search query: ")

    retrieve_chunks(user_query, limit=5)
