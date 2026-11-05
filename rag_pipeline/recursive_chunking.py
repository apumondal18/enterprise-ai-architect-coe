from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path

file_path = Path("./rag_pipeline/theart.txt")

text = file_path.read_text(encoding="utf-8")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200
)

chunks = splitter.create_documents(
    texts=[text],
    metadatas=[
        {
            "source": file_path.name
        }
    ]
)

print("Recursive Chunks:", len(chunks))

print("\nFirst Chunk:")
print(chunks[0].page_content)

print("\nMetadata:")
print(chunks[0].metadata)