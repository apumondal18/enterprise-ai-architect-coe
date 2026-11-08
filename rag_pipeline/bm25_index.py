
import json
from pathlib import Path
import bm25s

BM25_STORAGE = Path("./storage/bm25")


def build_bm25_index(chunks):

    BM25_STORAGE.mkdir(
        parents=True,
        exist_ok=True
    )

    # Extract chunk text
    corpus = [
        chunk.page_content
        for chunk in chunks
    ]

    # Keep chunk IDs in exactly the same order as corpus
    chunk_ids = [
        chunk.metadata["chunk_id"]
        for chunk in chunks
    ]

    # Validate input
    if len(corpus) != len(chunk_ids):
        raise ValueError("Corpus and chunk ID counts do not match.")

    if not corpus:
        raise ValueError("No chunks provided for BM25 indexing.")

    if any(not chunk_id for chunk_id in chunk_ids):
        raise ValueError("One or more chunks are missing chunk_id.")

    # Tokenize corpus
    tokenized_corpus = bm25s.tokenize(corpus)

    # Build BM25 index
    retriever = bm25s.BM25()

    retriever.index(tokenized_corpus)

    # Persist BM25 index
    retriever.save(str(BM25_STORAGE / "index"))

    # Persist chunk IDs
    with open(
        BM25_STORAGE / "chunk_ids.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(chunk_ids, f, ensure_ascii=False, indent=2)

    # Persist original chunk text
    with open(
        BM25_STORAGE / "corpus.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print("BM25 index successfully created!")
    print(f"Total indexed chunks: {len(corpus)}")
    print(f"Chunk IDs saved: {len(chunk_ids)}")
    print(f"Corpus entries saved: {len(corpus)}")

    return retriever
