
from dense_retriever import retrieve_chunks
from sparse_retrieval import search_sparse
from rrf import reciprocal_rank_fusion

import bm25s
import json
from pathlib import Path


class HybridRetriever:

    def __init__(self, alpha=0.5, k=60):

        self.alpha = alpha
        self.k = k

        # Load BM25 index only once
        self.BM25_STORAGE = Path("./storage/bm25")

        self.retriever = bm25s.BM25.load(
            str(self.BM25_STORAGE / "index"),
            load_corpus=True
        )

        # Load chunk IDs
        with open(
            self.BM25_STORAGE / "chunk_ids.json",
            "r",
            encoding="utf-8"
        ) as f:
            self.chunk_ids = json.load(f)

        self.corpus = self.retriever.corpus

        print("Hybrid Retriever initialized.")

    def search(self, user_query, top_k=5):

        # Step 1: Dense retrieval
        dense_results = retrieve_chunks(
            user_query,
            limit=top_k
        )

        # Step 2: Sparse retrieval
        sparse_results = search_sparse(
            self.retriever,
            user_query,
            top_k=top_k
        )

        # Step 3: RRF fusion
        hybrid_results = reciprocal_rank_fusion(
            dense_results=dense_results,
            bm25_results=sparse_results,
            alpha=self.alpha,
            k=self.k,
            top_k=top_k
        )

        # Step 4: Return final results
        return hybrid_results


# Initialise once
hybrid = HybridRetriever(alpha=0.5, k=60)

# Search
results = hybrid.search(
    "why does Lewis compare J.M. Barrie's Peter Pan to Harriet Beecher Stowe's Uncle Tom's Cabin?",
    top_k=10
)

# Display final results

for rank, result in enumerate(results, start=1):

    print(f"\nFinal Rank: {rank}")
    print(f"Chunk ID: {result['chunk_id']}")
    print(f"RRF Score: {result['rrf_score']:.6f}")
    print(f"Dense Rank: {result['dense_rank']}")
    print(f"BM25 Rank: {result['bm25_rank']}")
    print(f"Text: {result['text'][:500]}")
