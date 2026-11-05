import requests

BASE_URL = "http://44.210.239.115:5889"

# Check server health
response = requests.get(
    f"{BASE_URL}/health",
    timeout=10,
)
response.raise_for_status()

print("Health:", response.json())

with open("./rag_pipeline/theart.txt", "r", encoding="utf-8") as file:
    text_content = file.read()


paragraphs = [
    paragraph.strip()
    for paragraph in text_content.split("\n\n")
    if paragraph.strip()
]

print("Number of paragraphs:", len(paragraphs))
print("Type:", type(paragraphs))
print("First paragraph:", repr(paragraphs[0]) if paragraphs else "No paragraphs")

# Generate embeddings
response = requests.post(
    f"{BASE_URL}/embed",
    json={
        "texts": paragraphs
    },
    timeout=600,
)

print("Status code:", response.status_code)
##print("Response body:", response.text)

'''
try:
    print("Error details:", response.json())
except ValueError:
    print("Response text:", response.text)
'''
response.raise_for_status()

result = response.json()


print("Embedding dimension:", result["dim"])
print("Number of vectors:", len(result["embeddings"]))
print("Vector length:", len(result["embeddings"][0]))
