import os
import csv
import math
import requests
from pathlib import Path
from dotenv import load_dotenv

from hybrid_retriever import HybridRetriever
from reranker import rerank_documents


load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================

EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL")

RETRIEVAL_TOP_K = 30
EVALUATION_TOP_K = 5

# Initial threshold. We'll calibrate it using observed scores.
SIMILARITY_THRESHOLD = 0.55

JUDGEMENT_FILE = Path("./retrieval_relevance_judgements.csv")
SUMMARY_FILE = Path("./retrieval_quality_summary.csv")


# ==========================================
# GROUND-TRUTH DATASET
# ==========================================

TEST_DATASET = [

    {
        "question": (
            "How many years did the Jesuits consider sufficient "
            "to shape a person's beliefs and character through education?"
        ),
        "ground_truth": (
            "The Jesuits considered the first six years of life to suffice."
        )
    },

    {
        "question": (
            "What did Heine's English engineer's automaton "
            "demand after it was created?"
        ),
        "ground_truth": (
            'It gnashed and growled in his ear, demanding, "Give me a soul!"'
        )
    },

    {
        "question": (
            "According to Lewis, what is the single rule that must "
            "be observed if the Public is treated like animals "
            "in a vast Zoo?"
        ),
        "ground_truth": (
            '"Do not irritate the animals."'
        )
    },

    {
        "question": (
            "Why did Lord Leverhulme famously attack his own portrait "
            "painted by an eminent English artist?"
        ),
        "ground_truth": (
            "His vandalism was intended to advertise an insolent "
            "contempt for the sacrosanct character of fine art "
            "compared to soap-making."
        )
    },

    {
        "question": (
            "According to Goethe's conversations with Eckermann, "
            "what preoccupied Schiller in his youth versus his maturity?"
        ),
        "ground_truth": (
            "In his youth, Schiller was preoccupied with physical "
            "liberty, whereas in his maturity, he wished for "
            "the liberty of the mind."
        )
    }
]


# ==========================================
# GENERATE EMBEDDINGS
# ==========================================

def generate_embeddings(texts):

    if not EMBEDDING_API_URL:
        raise ValueError("EMBEDDING_API_URL missing from .env")

    response = requests.post(
        f"{EMBEDDING_API_URL.rstrip('/')}/embed",
        json={"texts": texts},
        timeout=120
    )

    response.raise_for_status()

    embeddings = response.json()["embeddings"]

    if len(embeddings) != len(texts):
        raise ValueError(
            "Embedding count does not match input text count."
        )

    return embeddings


# ==========================================
# COSINE SIMILARITY
# ==========================================

def cosine_similarity(vector_a, vector_b):

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


# ==========================================
# AUTOMATIC RELEVANCE JUDGEMENT
# ==========================================

def evaluate_relevance(ground_truth, hybrid_results):

    # Embed ground truth and all candidate chunks together.
    texts = [ground_truth]

    texts.extend(
        result["text"]
        for result in hybrid_results
    )

    embeddings = generate_embeddings(texts)

    ground_truth_embedding = embeddings[0]
    chunk_embeddings = embeddings[1:]

    relevance = {}
    similarity_scores = {}

    for result, chunk_embedding in zip(
        hybrid_results,
        chunk_embeddings
    ):

        chunk_id = str(result["chunk_id"])

        similarity = cosine_similarity(
            ground_truth_embedding,
            chunk_embedding
        )

        similarity_scores[chunk_id] = similarity

        # Binary relevance judgement.
        relevance[chunk_id] = int(
            similarity >= SIMILARITY_THRESHOLD
        )

    return relevance, similarity_scores


# ==========================================
# METRIC CALCULATIONS
# ==========================================

def precision_at_k(ranked_ids, relevance, k):

    top_k = ranked_ids[:k]

    if not top_k:
        return 0.0

    relevant = sum(
        relevance.get(str(chunk_id), 0)
        for chunk_id in top_k
    )

    return relevant / k


def recall_at_k(ranked_ids, relevance, k):

    total_relevant = sum(relevance.values())

    if total_relevant == 0:
        return None

    relevant = sum(
        relevance.get(str(chunk_id), 0)
        for chunk_id in ranked_ids[:k]
    )

    return relevant / total_relevant


def mrr_at_k(ranked_ids, relevance, k):

    for rank, chunk_id in enumerate(
        ranked_ids[:k],
        start=1
    ):

        if relevance.get(str(chunk_id), 0) == 1:
            return 1 / rank

    return 0.0


def ndcg_at_k(ranked_ids, relevance, k):

    dcg = 0.0

    for rank, chunk_id in enumerate(
        ranked_ids[:k],
        start=1
    ):

        rel = relevance.get(str(chunk_id), 0)

        dcg += rel / math.log2(rank + 1)

    total_relevant = sum(relevance.values())

    ideal_relevances = [
        1
    ] * min(total_relevant, k)

    idcg = sum(
        rel / math.log2(rank + 1)
        for rank, rel in enumerate(
            ideal_relevances,
            start=1
        )
    )

    if idcg == 0:
        return 0.0

    return dcg / idcg


def evaluate_ranking(ranked_ids, relevance):

    return {
        "precision_at_5": precision_at_k(
            ranked_ids, relevance, EVALUATION_TOP_K
        ),

        "recall_at_5": recall_at_k(
            ranked_ids, relevance, EVALUATION_TOP_K
        ),

        "mrr_at_5": mrr_at_k(
            ranked_ids, relevance, EVALUATION_TOP_K
        ),

        "ndcg_at_5": ndcg_at_k(
            ranked_ids, relevance, EVALUATION_TOP_K
        )
    }


# ==========================================
# MAIN EVALUATION
# ==========================================

def main():

    hybrid = HybridRetriever(alpha=0.5, k=60)

    all_judgements = []
    all_summaries = []

    print("\n==========================================")
    print("     AUTOMATED RETRIEVAL EVALUATION")
    print("==========================================")

    print("Similarity threshold:", SIMILARITY_THRESHOLD)

    for question_number, item in enumerate(
        TEST_DATASET,
        start=1
    ):

        query = item["question"]
        ground_truth = item["ground_truth"]

        print("\n==========================================")
        print(f"QUESTION {question_number}")
        print("==========================================")

        # ----------------------------------
        # STEP 1: HYBRID RETRIEVAL
        # ----------------------------------

        hybrid_results = hybrid.search(
            query,
            top_k=RETRIEVAL_TOP_K
        )

        if not hybrid_results:
            print("No results. Skipping.")
            continue

        hybrid_ids = [
            str(result["chunk_id"])
            for result in hybrid_results
        ]

        # ----------------------------------
        # STEP 2: AUTOMATIC RELEVANCE
        # ----------------------------------

        relevance, similarity_scores = evaluate_relevance(
            ground_truth,
            hybrid_results
        )

        print("\nAUTOMATIC RELEVANCE JUDGEMENTS")

        for rank, result in enumerate(
            hybrid_results,
            start=1
        ):

            chunk_id = str(result["chunk_id"])

            similarity = similarity_scores[chunk_id]

            label = (
                "RELEVANT"
                if relevance[chunk_id]
                else "NOT RELEVANT"
            )

            print(
                f"Hybrid Rank {rank} | "
                f"Chunk: {chunk_id} | "
                f"Similarity: {similarity:.4f} | "
                f"{label}"
            )

            all_judgements.append({
                "question_number": question_number,
                "question": query,
                "chunk_id": chunk_id,
                "hybrid_rank": rank,
                "similarity": round(similarity, 4),
                "relevant": relevance[chunk_id],
                "chunk_text": result["text"]
            })

        # ----------------------------------
        # STEP 3: RERANKING
        # ----------------------------------

        documents = [
            {
                "chunk_id": result["chunk_id"],
                "text": result["text"]
            }
            for result in hybrid_results
        ]

        reranked_results, rerank_latency = rerank_documents(
            query=query,
            documents=documents,
            top_k=RETRIEVAL_TOP_K
        )

        reranked_ids = [
            str(result["chunk_id"])
            for result in reranked_results
        ]

        # ----------------------------------
        # STEP 4: METRIC COMPARISON
        # ----------------------------------

        hybrid_metrics = evaluate_ranking(
            hybrid_ids,
            relevance
        )

        reranked_metrics = evaluate_ranking(
            reranked_ids,
            relevance
        )

        print("\nRERANKING LATENCY:", round(rerank_latency, 4))

        print("\nRELEVANT CANDIDATES IN TOP 30:",
              sum(relevance.values()))

        print("\nMETRIC COMPARISON")

        for metric in hybrid_metrics:

            print(
                f"{metric}: "
                f"Hybrid = {hybrid_metrics[metric]} | "
                f"Reranked = {reranked_metrics[metric]}"
            )

        # ----------------------------------
        # STEP 5: SAVE SUMMARY
        # ----------------------------------

        summary = {
            "question_number": question_number,
            "question": query,
            "relevant_in_top30": sum(relevance.values())
        }

        for metric, value in hybrid_metrics.items():
            summary[f"hybrid_{metric}"] = value

        for metric, value in reranked_metrics.items():
            summary[f"reranked_{metric}"] = value

        all_summaries.append(summary)

    # ======================================
    # EXPORT CSV
    # ======================================

    if all_judgements:

        with open(
            JUDGEMENT_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=all_judgements[0].keys()
            )

            writer.writeheader()
            writer.writerows(all_judgements)

    if all_summaries:

        with open(
            SUMMARY_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=all_summaries[0].keys()
            )

            writer.writeheader()
            writer.writerows(all_summaries)

    print("\n==========================================")
    print("EVALUATION COMPLETED")
    print("==========================================")

    print("Relevance judgements:", JUDGEMENT_FILE)
    print("Quality summary:", SUMMARY_FILE)


if __name__ == "__main__":
    main()
