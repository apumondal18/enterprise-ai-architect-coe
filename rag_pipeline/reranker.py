import requests
import os
import time
from dotenv import load_dotenv
from hybrid_retriever import HybridRetriever

load_dotenv()
BASE_URL = os.getenv("RERANKING_API_URL")
documents = []

hr01=HybridRetriever()


query = "Why does Lewis compare J.M. Barrie's Peter Pan to Harriet Beecher Stowe's Uncle Tom's Cabin?"

hr_results=hr01.search(query,30)

if hr_results is None or len(hr_results)==0:
    exit("No results found from hybrid retrieval.")

for rank, result in enumerate(hr_results, start=1):
    documents.append({
        "chunk_id": result['chunk_id'],
        "text": result['text']
    })


#print(documents)

'''
documents = [
    "Hybrid retrieval combines semantic vector search and keyword-based search.",
    "BM25 is a sparse retrieval algorithm based on term frequency and inverse document frequency.",
    "Dense retrieval uses embeddings to find semantically similar documents.",
    "A cross encoder evaluates the relevance of a query and document together.",
    "The capital of France is Paris."
]
'''

start_time = time.perf_counter()
response = requests.post(
    f"{BASE_URL}/rerank",
    json={
        "query": query,
        "documents": documents
    },
    timeout=60
)

rerank_latency = time.perf_counter() - start_time
response.raise_for_status()

results = response.json()["results"]
top_results = results[:5]

for rank, result in enumerate(top_results, start=1):
    print(f"\nRank: {rank}")
    print(f"Score: {result['score']:.4f}")
    print(f"Chunk ID: {result['chunk_id']}")
    print(f"Document: {result['document']}")

print(f"\nReranking API latency: {rerank_latency:.4f} seconds")