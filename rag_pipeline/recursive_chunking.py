from langchain_text_splitters import RecursiveCharacterTextSplitter
text = open("./rag_pipeline/theart.txt", "r", encoding="utf-8").read()

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_text(text)

print("Recursive Chunks:", len(chunks))
print(chunks[0])