import csv
import os
import re
import time
import statistics
from pathlib import Path

from query_pipeline import QueryPipeline


# --------------------------------------------------
# BENCHMARK CONFIGURATION
# --------------------------------------------------

QUERY_LIST = [
    "How many years did the Jesuits consider sufficient to shape a person's beliefs and character through education?",

    "What did Heine's English engineer's automaton demand after it was created?",

    "According to Lewis, what is the single rule that must be observed if the Public is treated like animals in a vast Zoo?",

    "Why did Lord Leverhulme famously attack his own portrait painted by an eminent English artist?",

    "According to Goethe's conversations with Eckermann, what preoccupied Schiller in his youth versus his maturity?"
]

RUNS = 10

RETRIEVAL_TOP_K = 30
RERANK_TOP_K = 5

CSV_OUTPUT = Path("./benchmark_results.csv")

# Cost per 1 million input tokens.
# Your current self-hosted embedding service has no
# per-token API charge, so this defaults to zero.
EMBEDDING_COST_PER_1M_TOKENS = float(
    os.getenv("EMBEDDING_COST_PER_1M_TOKENS", "0")
)


# --------------------------------------------------
# TOKENIZER
# --------------------------------------------------

def load_tokenizer():

    try:
        from transformers import AutoTokenizer

        tokenizer_name = os.getenv(
            "TOKENIZER_NAME",
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_name
        )

        print("Tokenizer loaded:", tokenizer_name)

        return tokenizer

    except Exception as error:

        print("Tokenizer unavailable:", error)
        print("Using approximate word/punctuation count.")

        return None


def count_tokens(text, tokenizer):

    if tokenizer:

        return len(
            tokenizer.encode(
                text,
                add_special_tokens=True
            )
        )

    # Approximation only; not an exact model-token count.
    return len(re.findall(r"\w+|[^\w\s]", text))


# --------------------------------------------------
# STATISTICS
# --------------------------------------------------

def percentile(values, percentage):

    if not values:
        return 0

    sorted_values = sorted(values)

    index = (len(sorted_values) - 1) * percentage

    lower = int(index)
    upper = min(lower + 1, len(sorted_values))

    fraction = index - lower

    return (
        sorted_values[lower] * (1 - fraction)
        + sorted_values[upper] * fraction
    )


def calculate_statistics(values):

    if not values:
        return {
            "average": 0,
            "p50": 0,
            "p95": 0,
            "minimum": 0,
            "maximum": 0
        }

    return {
        "average": statistics.mean(values),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "minimum": min(values),
        "maximum": max(values)
    }


# --------------------------------------------------
# BENCHMARK
# --------------------------------------------------

def run_benchmark():

    print("\n======================================")
    print("       RAG PIPELINE BENCHMARK")
    print("======================================")

    pipeline = QueryPipeline()

    tokenizer = load_tokenizer()

    measurements = []

    total_query_tokens = 0

    cache_hits = 0
    cache_misses = 0

    print("\nStarting benchmark...")
    print("Number of runs:", RUNS)

    benchmark_start = time.perf_counter()

    for run_number in range(1, RUNS + 1):

        query = QUERY_LIST[
            (run_number - 1) % len(QUERY_LIST)
        ]

        print("\n--------------------------------------")
        print(f"Benchmark Run: {run_number}/{RUNS}")
        print("--------------------------------------")

        query_tokens = count_tokens(query, tokenizer)

        start_time = time.perf_counter()

        output = pipeline.run(
            query=query,
            retrieval_top_k=RETRIEVAL_TOP_K,
            rerank_top_k=RERANK_TOP_K
        )

        wall_latency = time.perf_counter() - start_time

        # Use the pipeline's own total latency where available.
        total_latency = output.get(
            "total_latency",
            wall_latency
        )

        cache_hit = output.get("cache_hit", False)

        if cache_hit:
            cache_hits += 1
        else:
            cache_misses += 1

        total_query_tokens += query_tokens

        measurements.append({
            "run": run_number,
            "cache_hit": cache_hit,
            "query_tokens": query_tokens,
            "total_latency": total_latency,
            "wall_latency": wall_latency,
            "retrieval_latency": output.get(
                "retrieval_latency", 0
            ),
            "rerank_latency": output.get(
                "rerank_latency", 0
            ),
            "results_count": len(output.get("results", []))
        })

        print("\nRun metrics:")
        print("Cache hit:", cache_hit)
        print("Query tokens:", query_tokens)
        print("Total latency:", round(total_latency, 4), "sec")

    benchmark_wall_time = (
        time.perf_counter() - benchmark_start
    )

    # --------------------------------------------------
    # AGGREGATE METRICS
    # --------------------------------------------------

    latencies = [
        item["total_latency"]
        for item in measurements
    ]

    hit_latencies = [
        item["total_latency"]
        for item in measurements
        if item["cache_hit"]
    ]

    miss_latencies = [
        item["total_latency"]
        for item in measurements
        if not item["cache_hit"]
    ]

    retrieval_latencies = [
        item["retrieval_latency"]
        for item in measurements
        if item["retrieval_latency"] > 0
    ]

    rerank_latencies = [
        item["rerank_latency"]
        for item in measurements
        if item["rerank_latency"] > 0
    ]

    latency_stats = calculate_statistics(latencies)
    hit_stats = calculate_statistics(hit_latencies)
    miss_stats = calculate_statistics(miss_latencies)

    retrieval_stats = calculate_statistics(
        retrieval_latencies
    )

    rerank_stats = calculate_statistics(
        rerank_latencies
    )

    throughput = (
        RUNS / benchmark_wall_time
        if benchmark_wall_time > 0
        else 0
    )

    cache_hit_rate = (
        cache_hits / RUNS * 100
        if RUNS > 0
        else 0
    )

    estimated_embedding_cost = (
        total_query_tokens
        / 1_000_000
        * EMBEDDING_COST_PER_1M_TOKENS
    )

    # --------------------------------------------------
    # DISPLAY SUMMARY
    # --------------------------------------------------

    print("\n\n======================================")
    print("          BENCHMARK SUMMARY")
    print("======================================")

    print("\nLATENCY")
    print("Average:", round(latency_stats["average"], 4), "sec")
    print("P50:", round(latency_stats["p50"], 4), "sec")
    print("P95:", round(latency_stats["p95"], 4), "sec")
    print("Minimum:", round(latency_stats["minimum"], 4), "sec")
    print("Maximum:", round(latency_stats["maximum"], 4), "sec")

    print("\nCACHE PERFORMANCE")
    print("Cache hits:", cache_hits)
    print("Cache misses:", cache_misses)
    print("Cache hit rate:", round(cache_hit_rate, 2), "%")

    print(
        "Average cache-hit latency:",
        round(hit_stats["average"], 4),
        "sec"
    )

    print(
        "Average cache-miss latency:",
        round(miss_stats["average"], 4),
        "sec"
    )

    print("\nRETRIEVAL AND RERANKING")

    print(
        "Average retrieval latency:",
        round(retrieval_stats["average"], 4),
        "sec"
    )

    print(
        "Average reranking latency:",
        round(rerank_stats["average"], 4),
        "sec"
    )

    print("\nTHROUGHPUT")
    print("Total benchmark time:", round(benchmark_wall_time, 4), "sec")
    print("Queries per second:", round(throughput, 4))

    print("\nTOKEN USAGE")
    print("Total query tokens:", total_query_tokens)
    print("Tokenizer:", "Hugging Face" if tokenizer else "Approximate")

    print("\nESTIMATED EMBEDDING COST")
    print("Cost:", round(estimated_embedding_cost, 8))

    print("\n======================================")

    # --------------------------------------------------
    # EXPORT CSV
    # --------------------------------------------------

    with open(
        CSV_OUTPUT,
        "w",
        newline="",
        encoding="utf-8"
    ) as csv_file:

        fieldnames = measurements[0].keys()

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(measurements)

    print("\nDetailed results saved to:", CSV_OUTPUT)


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    run_benchmark()
