import os
from uuid import uuid5, NAMESPACE_URL
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)


load_dotenv()
# Qdrant Cloud credentials
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

COLLECTION_NAME = "rag_documents"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 produces 384-dimensional vectors

#print(QDRANT_URL)
#print(QDRANT_API_KEY)

# Connect to Qdrant Cloud
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)


def create_collection():

    if not client.collection_exists(COLLECTION_NAME):

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE
            )
        )

        print(f"Collection '{COLLECTION_NAME}' created.")

    else:
        print(f"Collection '{COLLECTION_NAME}' already exists.")


def store_chunks(embedded_chunks, batch_size=100):

    points = []

    for index, item in enumerate(embedded_chunks):

        metadata = item["metadata"]

        # Generate a repeatable ID for this source and chunk position
        source = metadata.get("path", metadata.get("source", "unknown"))
        point_id = str(
            uuid5(NAMESPACE_URL, f"{source}:{index}")
        )

        points.append(
            PointStruct(
                id=point_id,
                vector=item["embedding"],
                payload={
                    "text": item["text"],
                    "metadata": metadata
                }
            )
        )

    # Upload points in batches
    for i in range(0, len(points), batch_size):

        batch = points[i:i + batch_size]

        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
            wait=True
        )

        print(f"Uploaded {min(i + batch_size, len(points))}/{len(points)} points")

    print("Qdrant storage completed.")
