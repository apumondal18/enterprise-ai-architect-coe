import bm25s
import json

MAPPING_FILE = "./storage/bm25/chunk_ids.json"

with open(MAPPING_FILE, "r", encoding="utf-8") as f:
    chunk_ids = json.load(f)

with open("./storage/bm25/corpus.json", "r", encoding="utf-8") as f:
    corpus = json.load(f)

# Change this to the directory where you saved your BM25 indexs
INDEX_DIR = "./storage/bm25/index"

TOP_K = 5


def load_sparse_index():
    print("Loading BM25 sparse index...")

    retriever = bm25s.BM25.load(
        INDEX_DIR,
        mmap=True,
        load_corpus=True
    )

    print("BM25 index loaded successfully.")
    return retriever


def search_sparse(retriever, query, top_k=TOP_K):

    print(f"\nQuery: {query}")
    print("-" * 80)

    query_tokens = bm25s.tokenize(query)

    results, scores = retriever.retrieve(
        query_tokens,
        k=top_k
    )

    if results.shape[1] == 0:
        print("No results found.")
        return []

    retrieved_chunks = []

    for i in range(results.shape[1]):

        document = results[0, i]
        score = float(scores[0, i])

        # Convert corpus position to chunk ID
        corpus_position = int(document)

        chunk_id = chunk_ids[corpus_position]
        chunk_text = corpus[corpus_position]

        chunk = {
            "chunk_id": str(chunk_id),
            "text": chunk_text,
            "metadata": {},
            "bm25_score": score,
            "bm25_rank": i + 1
        }

        retrieved_chunks.append(chunk)

        print(f"\nRank: {i + 1}")
        print(f"BM25 Score: {score:.4f}")
        print(f"Corpus Position: {corpus_position}")
        print(f"Chunk ID: {chunk_id}")
        print(f"Chunk Text: {chunk_text[:500]}...")

        print("-" * 80)

    return retrieved_chunks



if __name__ == "__main__":
    retriever = load_sparse_index()

    print("\nBM25 Sparse Retrieval Test")
    print("Enter 'exit' to quit.")

    while True:
        query = input("\nEnter your search query: ").strip()

        if query.lower() == "exit":
            break

        if not query:
            print("Please enter a valid query.")
            continue

        search_sparse(retriever, query)
