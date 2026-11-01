import os
import warnings

# 1. Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 2. Import required libraries
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings

# 3. Initialize a local embedding model
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu",
                  "local_files_only": True},
    encode_kwargs={"normalize_embeddings": True}
)

# 4. Initialize the Semantic Chunker
splitter = SemanticChunker(embeddings)

# 5. Read your text file
with open("./rag_pipeline/theart.txt", "r", encoding="utf-8") as file:
    text = file.read()

# 6. Split the text into semantic chunks
chunks = splitter.split_text(text)

# 7. Display the results
print("Semantic Chunks:", len(chunks))

print(chunks[1])
