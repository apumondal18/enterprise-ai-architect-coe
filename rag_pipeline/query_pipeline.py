import json
import time

from semantic_cache import SemanticCache
from hybrid_retriever import HybridRetriever
from reranker import rerank_documents


class QueryPipeline:

    def __init__(
        self,
        alpha=0.5,
        rrf_k=60,
        cache_threshold=0.92
    ):

        self.cache = SemanticCache()

        # Create index if it does not already exist
        self.cache.create_index()

        self.hybrid = HybridRetriever(
            alpha=alpha,
            k=rrf_k
        )

        self.cache_threshold = cache_threshold

        print("Query Pipeline initialized.")

    def display_results(self, results):

        print("\n========== TOP 5 RESULTS ==========")

        for rank, result in enumerate(results, start=1):

            print(f"\nRank: {rank}")
            print(f"Chunk ID: {result['chunk_id']}")
            print(f"Score: {result['score']:.4f}")
            print(f"Document: {result['document']}")

        print("\n===================================")

    def run(
        self,
        query,
        retrieval_top_k=30,
        rerank_top_k=5
    ):

        total_start = time.perf_counter()

        print("\n================================")
        print("QUERY:", query)
        print("================================")

        # Step 1: Clean expired cache entries
        deleted = self.cache.delete_expired()

        if deleted:
            print("Expired cache entries removed:", deleted)

        # Step 2: Generate query embedding
        embedding = self.cache.generate_embedding(query)

        # Step 3: Search semantic cache
        cached_result = self.cache.search(
            embedding,
            threshold=self.cache_threshold
        )

        if cached_result is not None:

            try:
                cached_results = json.loads(cached_result)
                self.display_results(cached_results)

                print("\nSEMANTIC CACHE HIT")
                print("Hybrid retrieval skipped.")
                print("Reranking skipped.")

                total_latency = (
                    time.perf_counter() - total_start
                )

                return {
                    "query": query,
                    "cache_hit": True,
                    "results": cached_results,
                    "total_latency": total_latency
                }

            except (json.JSONDecodeError, TypeError):

                print("Invalid cached data. Proceeding with retrieval.")

        # Step 4: Cache miss - run hybrid retrieval
        print("\nSEMANTIC CACHE MISS")
        print("Running hybrid retrieval...")

        retrieval_start = time.perf_counter()

        hybrid_results = self.hybrid.search(
            query,
            top_k=retrieval_top_k
        )

        retrieval_latency = (
            time.perf_counter() - retrieval_start
        )

        if not hybrid_results:

            print("No results found.")

            return {
                "query": query,
                "cache_hit": False,
                "results": [],
                "total_latency": (
                    time.perf_counter() - total_start
                )
            }

        # Step 5: Prepare documents for reranking
        documents = []

        for result in hybrid_results:

            documents.append({
                "chunk_id": result["chunk_id"],
                "text": result["text"]
            })

        # Step 6: Rerank
        print("Running reranking API...")

        top_results, rerank_latency = rerank_documents(
            query=query,
            documents=documents,
            top_k=rerank_top_k
        )

        self.display_results(top_results)
        # Step 7: Store top results in semantic cache
        serialized_results = json.dumps(top_results)

        cache_id = self.cache.store(
            query=query,
            embedding=embedding,
            answer=serialized_results
        )

        total_latency = (
            time.perf_counter() - total_start
        )

        print("\nCACHE ENTRY:", cache_id)
        print("Retrieval latency:", round(retrieval_latency, 4))
        print("Reranking latency:", round(rerank_latency, 4))
        print("Total latency:", round(total_latency, 4))

        return {
            "query": query,
            "cache_hit": False,
            "results": top_results,
            "retrieval_latency": retrieval_latency,
            "rerank_latency": rerank_latency,
            "total_latency": total_latency
        }


# Execute only when this file is run directly
if __name__ == "__main__":

    pipeline = QueryPipeline()

    query = (
        "Why does Lewis compare J.M. Barrie's Peter Pan "
        "to Harriet Beecher Stowe's Uncle Tom's Cabin?"
    )

    output = pipeline.run(query)

    print("\n========== FINAL RESULTS ==========")

    print("Cache hit:", output["cache_hit"])

    for rank, result in enumerate(
        output["results"],
        start=1
    ):

        print(f"\nRank: {rank}")
        print(f"Score: {result['score']:.4f}")
        print(f"Chunk ID: {result['chunk_id']}")
        print(f"Document: {result['document']}")
