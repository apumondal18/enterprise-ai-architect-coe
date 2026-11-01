import pypdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_pdf_natively(pdf_path: str) -> list[Document]:
    documents = []
    reader = pypdf.PdfReader(pdf_path)
    
    # Loop through each page in the PDF file
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text.strip():  # Skip empty pages
            doc = Document(
                page_content=text,
                metadata={"source": pdf_path, "page": page_num + 1}
            )
            documents.append(doc)
            
    return documents

# Usage
docs = load_pdf_natively("./rag_pipeline/insurance-savings.pdf")


splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
chunks = splitter.split_documents(docs)

print(f"Manually loaded {len(docs)} pages into core Document objects.")
print(f"Split into {len(chunks)} chunks using RecursiveCharacterTextSplitter.")
print(chunks[0])
