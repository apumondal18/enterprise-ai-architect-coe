import os
import requests
import json
import pypdf
import docx
import pandas as pd
import hashlib
import uuid
import bm25s

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from remote_embeddings import embed_documents
from bm25_index import build_bm25_index
from qdrant_store import create_collection, store_chunks
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter
)

# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

directory = Path(r"D:\AIdata")

supported_extensions = {".pdf", ".docx", ".txt", ".csv", ".md"}

all_chunks = []

# Initialize splitters once
recursive_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200
)

header_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[
        ("#", "Header_1"),
        ("##", "Header_2"),
        ("###", "Header_3")
    ]
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200
)


# --------------------------------------------------
# 2. File Discovery
# --------------------------------------------------

files = [
    file
    for file in directory.iterdir()
    if file.is_file() and file.suffix.lower() in supported_extensions
]

print(f"Total files detected: {len(files)}")


# --------------------------------------------------
# 3. Extraction and Chunking Functions
# --------------------------------------------------

def extract_pdf(file):

    pdf_reader = pypdf.PdfReader(file)

    extracted_text = ""

    for page in pdf_reader.pages:
        extracted_text += (page.extract_text() or "") + "\n"

    return recursive_splitter.create_documents(
        texts=[extracted_text],
        metadatas=[{
            "source": file.name,
            "path": str(file.resolve()),
            "file_type": ".pdf"
        }]
    )


def extract_docx(file):

    doc = docx.Document(file)

    extracted_text = "\n".join(
        para.text for para in doc.paragraphs
    )

    temp_chunks = header_splitter.split_text(extracted_text)

    final_chunks = []

    for section in temp_chunks:

        if len(section.page_content) <= 1500:

            section.metadata.update({
                "source": file.name,
                "path": str(file.resolve()),
                "file_type": ".docx"
            })

            final_chunks.append(section)

        else:

            sub_docs = text_splitter.split_documents([section])

            for sub_doc in sub_docs:

                sub_doc.metadata.update({
                    "source": file.name,
                    "path": str(file.resolve()),
                    "file_type": ".docx"
                })

                final_chunks.append(sub_doc)

    return final_chunks


def extract_txt(file):

    with open(file, "r", encoding="utf-8") as f:
        extracted_text = f.read()

    return recursive_splitter.create_documents(
        texts=[extracted_text],
        metadatas=[{
            "source": file.name,
            "path": str(file.resolve()),
            "file_type": ".txt"
        }]
    )


def extract_csv(file):

    df = pd.read_csv(file)

    rows_per_chunk = 20

    table_chunks = []

    for i in range(0, len(df), rows_per_chunk):

        chunk_df = df.iloc[i:i + rows_per_chunk]

        markdown_table = chunk_df.to_markdown(index=False)

        end_row = i + len(chunk_df) - 1

        page_content = (
            f"Data Table Snippet (Rows {i} to {end_row}):\n\n"
            f"{markdown_table}"
        )

        metadata = {
            "source": file.name,
            "path": str(file.resolve()),
            "file_type": ".csv",
            "start_row": i,
            "end_row": end_row
        }

        table_chunks.append(
            Document(
                page_content=page_content,
                metadata=metadata
            )
        )

    return table_chunks


def extract_md(file):

    with open(file, "r", encoding="utf-8") as f:
        extracted_text = f.read()

    temp_chunks = header_splitter.split_text(extracted_text)

    final_chunks = []

    for section in temp_chunks:

        if len(section.page_content) <= 1500:

            section.metadata.update({
                "source": file.name,
                "path": str(file.resolve()),
                "file_type": ".md"
            })

            final_chunks.append(section)

        else:

            sub_docs = text_splitter.split_documents([section])

            for sub_doc in sub_docs:

                sub_doc.metadata.update({
                    "source": file.name,
                    "path": str(file.resolve()),
                    "file_type": ".md"
                })

                final_chunks.append(sub_doc)

    return final_chunks



#Assign chunk IDs based on document ID and content hash
def assign_chunk_ids(file, chunks):

    document_id = uuid.uuid5(
        uuid.NAMESPACE_URL,
        str(file.resolve()).lower()
    )

    identified_chunks = []

    for index, chunk in enumerate(chunks):

        content_hash = hashlib.sha256(
            chunk.page_content.encode("utf-8")
        ).hexdigest()

        chunk_id = str(
            uuid.uuid5(
                document_id,
                f"{index}:{content_hash}"
            )
        )

        metadata = {
            **chunk.metadata,
            "document_id": str(document_id),
            "chunk_id": chunk_id,
            "chunk_index": index
        }

        identified_chunks.append(
            Document(
                id=chunk_id,
                page_content=chunk.page_content,
                metadata=metadata
            )
        )

    return identified_chunks

# --------------------------------------------------
# 4. Unified Ingestion Engine
# --------------------------------------------------

for file in files:

    try:

        extension = file.suffix.lower()

        if extension == ".pdf":
            chunks = extract_pdf(file)

        elif extension == ".docx":
            chunks = extract_docx(file)

        elif extension == ".txt":
            chunks = extract_txt(file)

        elif extension == ".csv":
            chunks = extract_csv(file)

        elif extension == ".md":
            chunks = extract_md(file)

        else:
            continue

        chunks = assign_chunk_ids(file, chunks)
        all_chunks.extend(chunks)

        print(
            f"Processed: {file.name} | "
            f"Chunks: {len(chunks)}"
        )

    except Exception as e:

        print(f"Error processing {file.name}: {e}")


# --------------------------------------------------
# 5. Final Validation
# --------------------------------------------------

print("\n========== INGESTION SUMMARY ==========")

print(f"Total files detected: {len(files)}")
print(f"Total chunks generated: {len(all_chunks)}")

if all_chunks:

    print("\nFirst chunk:")
    print(all_chunks[0])

    print("\nFirst chunk metadata:")
    print(all_chunks[0].metadata)

    print("\nAll chunks are Document objects:",
          all(isinstance(chunk, Document) for chunk in all_chunks))

'''
#Step 1: embedding generation
embedded_chunks = embed_documents(
    all_chunks,
    batch_size=500
)

print("\nEmbedding generation completed!")

print("Total embedded chunks:", len(embedded_chunks))

if embedded_chunks:
    print("Vector dimensions:", len(embedded_chunks[0]["embedding"]))
    print("First embedded document:")
    print(embedded_chunks[0])


# Step 2: Create Qdrant collection
create_collection()

# Step 3: Store vectors, text and metadata
store_chunks(
    embedded_chunks,
    batch_size=100
)
'''

def dense_pipeline(chunks):

    print("Starting dense indexing...")

    embedded_chunks = embed_documents(
        chunks,
        batch_size=1000
    )

    create_collection()

    store_chunks(
        embedded_chunks,
        batch_size=100
    )

    print("Dense indexing completed!")


def sparse_pipeline(chunks):

    print("Starting sparse indexing...")

    build_bm25_index(chunks)

    print("Sparse indexing completed!")


# Run both pipelines concurrently

with ThreadPoolExecutor(max_workers=2) as executor:

    dense_future = executor.submit(
        dense_pipeline,
        all_chunks
    )

    sparse_future = executor.submit(
        sparse_pipeline,
        all_chunks
    )

    dense_future.result()
    sparse_future.result()


print("\n========== INDEXING COMPLETED ==========")