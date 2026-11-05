import os
# Hide the unstructured notice banner just in case other parts of your app call it
os.environ["UNSTRUCTURED_DISABLE_NOTICE"] = "1"

import docx
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# 1. Native DOCX loading preserving headings into Markdown format
def load_docx_text(file_path):
    doc = docx.Document(file_path)
    lines = []
    for p in doc.paragraphs:
        style = p.style.name
        if style == 'Heading 1': lines.append(f"# {p.text}")
        elif style == 'Heading 2': lines.append(f"## {p.text}")
        elif style == 'Heading 3': lines.append(f"### {p.text}")
        else: lines.append(p.text)
    return "\n\n".join(lines)

document_text = load_docx_text("D:\AIdata\JD_AWS Cloud Admin.docx")

# 2. Structural Split using LangChain's core text splitters
headers_to_split_on = [("#", "Header_1"), ("##", "Header_2"), ("###", "Header_3")]
markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
section_chunks = markdown_splitter.split_text(document_text)

# 3. Fallback Sub-splitting
final_chunks = []
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)

for section in section_chunks:
    if len(section.page_content) <= 1500:
        section.metadata["source"] = "D:\AIdata\JD_AWS Cloud Admin.docx"
        final_chunks.append(section)
    else:
        sub_docs = text_splitter.split_documents([section])
        for doc in sub_docs:
            doc.metadata["source"] = "D:\AIdata\JD_AWS Cloud Admin.docx"
            final_chunks.append(doc)

print(f"Successfully processed {len(final_chunks)} chunks warning-free!")
print(final_chunks[0])


print("2nd chunk:")
print(final_chunks[1])
