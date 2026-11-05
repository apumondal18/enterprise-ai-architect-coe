import pandas as pd
from langchain_core.documents import Document

# Sample processing for 100 rows
df = pd.read_csv(r"D:\AIdata\Insurance claims data.csv")
#row_chunks = []

# Grouping into blocks of 10 rows (10 total chunks for a 100-row file)
rows_per_chunk = 20
table_chunks = []

for i in range(0, len(df), rows_per_chunk):
    chunk_df = df.iloc[i : i + rows_per_chunk]
    
    # Render the sub-dataframe as a clean markdown table
    markdown_table = chunk_df.to_markdown(index=False)
    
    page_content = f"Data Table Snippet (Rows {i} to {i + len(chunk_df) - 1}):\n\n{markdown_table}"
    metadata = {"start_row": i, "end_row": i + len(chunk_df) - 1}
    
    table_chunks.append(Document(page_content=page_content, metadata=metadata))

print(f"Generated {len(table_chunks)} grouped table chunks.")

print(table_chunks[0])
