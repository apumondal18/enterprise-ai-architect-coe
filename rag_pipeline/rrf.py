
def reciprocal_rank_fusion(
    dense_results,
    bm25_results,
    alpha=0,
    k=60,
    top_k=5
):

    if not 0 <= alpha <= 1:
        raise ValueError("Alpha must be between 0 and 1")

    fused_results = {}

    # Dense ranking contribution
    for rank, result in enumerate(dense_results, start=1):

        chunk_id = result["chunk_id"]

        if chunk_id not in fused_results:
            fused_results[chunk_id] = {
                **result,
                "dense_rank": None,
                "bm25_rank": None,
                "rrf_score": 0.0
            }

        fused_results[chunk_id]["dense_rank"] = rank

        fused_results[chunk_id]["rrf_score"] += (
            alpha / (k + rank)
        )

    # BM25 ranking contribution
    for rank, result in enumerate(bm25_results, start=1):

        chunk_id = result["chunk_id"]

        if chunk_id not in fused_results:
            fused_results[chunk_id] = {
                **result,
                "dense_rank": None,
                "bm25_rank": None,
                "rrf_score": 0.0
            }

        fused_results[chunk_id]["bm25_rank"] = rank

        # Preserve dense text and metadata if already present
        if not fused_results[chunk_id].get("text"):
            fused_results[chunk_id]["text"] = result["text"]

        if not fused_results[chunk_id].get("metadata"):
            fused_results[chunk_id]["metadata"] = result.get(
                "metadata", {}
            )

        fused_results[chunk_id]["rrf_score"] += (
            (1 - alpha) / (k + rank)
        )

    # Sort by RRF score
    ranked_results = sorted(
        fused_results.values(),
        key=lambda x: x["rrf_score"],
        reverse=True
    )

    return ranked_results[:top_k]
