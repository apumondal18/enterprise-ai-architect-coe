from langchain_text_splitters import TokenTextSplitter
text = open("./rag_pipeline/theart.txt", "r", encoding="utf-8").read()

splitter = TokenTextSplitter(chunk_size=256, chunk_overlap=32)
chunks = splitter.split_text(text)

print("Token-based Chunks:", len(chunks))
print(chunks[0])