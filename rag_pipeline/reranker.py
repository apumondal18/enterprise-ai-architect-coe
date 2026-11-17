import requests
import os
import time

from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("RERANKING_API_URL")


def rerank_documents(query, documents, top_k=5):

    if not BASE_URL:
        raise ValueError("RERANKING_API_URL is missing from .env")

    if not documents:
        return [], 0.0

    start_time = time.perf_counter()

    response = requests.post(
        f"{BASE_URL}/rerank",
        json={
            "query": query,
            "documents": documents
        },
        timeout=60
    )

    response.raise_for_status()

    rerank_latency = time.perf_counter() - start_time

    results = response.json()["results"]

    top_results = results[:top_k]

    return top_results, rerank_latency
