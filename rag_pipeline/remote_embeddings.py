import requests
import os
from dotenv import load_dotenv

load_dotenv()
BASE_URL = os.getenv("EMBEDDING_API_URL")


def generate_embeddings(texts, batch_size=50):

    if not texts:
        return []

    all_embeddings = []

    for i in range(0, len(texts), batch_size):

        batch = texts[i:i + batch_size]

        response = requests.post(
            f"{BASE_URL}/embed",
            json={
                "texts": batch
            },
            timeout=120
        )

        response.raise_for_status()

        result = response.json()

        batch_embeddings = result["embeddings"]

        if len(batch_embeddings) != len(batch):
            raise ValueError(
                "Number of embeddings does not match number of input texts"
            )

        all_embeddings.extend(batch_embeddings)

        print(
            f"Generated embeddings: "
            f"{min(i + batch_size, len(texts))}/{len(texts)}"
        )

    return all_embeddings


def embed_documents(documents, batch_size=50):

    # Extract text from LangChain Document objects
    texts = [
        document.page_content
        for document in documents
    ]

    # Generate embeddings through remote API
    embeddings = generate_embeddings(
        texts,
        batch_size=batch_size
    )

    # Combine vectors with their original text and metadata
    embedded_documents = []

    for document, embedding in zip(documents, embeddings):

        embedded_documents.append({
            "text": document.page_content,
            "metadata": document.metadata,
            "embedding": embedding
        })

    return embedded_documents
