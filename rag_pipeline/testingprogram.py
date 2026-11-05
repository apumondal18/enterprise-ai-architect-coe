
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

COLLECTION_NAME = "rag_documents"

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

    # Step 3: Display results
    for index, point in enumerate(results.points, start=1):

        print(f"\n{'=' * 60}")
        print(f"RESULT {index}")
        print(f"Similarity score: {point.score:.4f}")

        print("\nChunk text:")
        print(point.payload.get("text", ""))

        print("\nMetadata:")
        print(point.payload.get("metadata", {}))


if __name__ == "__main__":

    user_query = input("Enter your search query: ")

    retrieve_chunks(user_query, limit=5)
