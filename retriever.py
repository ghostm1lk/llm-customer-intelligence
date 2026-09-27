"""
retriever.py - the Knowledge Layer (RAG retrieval).

    1. Splits every policy document in data/kb/ into small chunks.
    2. Turns each chunk into an embedding (a list of numbers that captures its meaning)
       using the nomic-embed-text model in Ollama.
    3. Stores the chunks + embeddings in a Chroma vector database (folder: chroma_db/).
    4. For a customer message, finds the chunks whose meaning is closest.

Before running:
    ollama pull nomic-embed-text
    pip install chromadb

Rebuild the database and run the self-check (do this whenever data/kb/ changes):
    python retriever.py
"""

import os

import chromadb
import ollama


KB_DIR = "data/kb"
DB_DIR = "chroma_db"
COLLECTION_NAME = "policies"
EMBED_MODEL = "nomic-embed-text"


def load_chunks():
    """Read every .md file and split it into chunks (one chunk per line of content)."""
    chunks = []
    for filename in sorted(os.listdir(KB_DIR)):
        if not filename.endswith(".md"):
            continue
        with open(os.path.join(KB_DIR, filename)) as file:
            lines = file.read().split("\n")

        # The first line is the title, e.g. "# Duplicate Charges Policy (Nova Bank)".
        title = lines[0].replace("#", "").strip()

        for line in lines[1:]:
            line = line.strip()
            if len(line) < 20:
                continue  # skip empty lines and short sub-headings like "Phishing:"
            line = line.lstrip("- ")  # remove the bullet at the start
            chunk = {
                "text": title + ": " + line,
                "source": filename,
            }
            chunks.append(chunk)
    return chunks


def embed(texts):
    """Turn a list of texts into a list of embeddings (one list of numbers per text)."""
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    return response.embeddings


def get_collection():
    """Open (or create) the Chroma collection that stores our chunks."""
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # compare embeddings by angle (cosine distance)
    )
    return collection


def build_index():
    """Delete the old database contents and rebuild them from data/kb/."""
    client = chromadb.PersistentClient(path=DB_DIR)
    existing_names = []
    for collection in client.list_collections():
        existing_names.append(collection.name)
    if COLLECTION_NAME in existing_names:
        client.delete_collection(COLLECTION_NAME)

    collection = get_collection()
    chunks = load_chunks()

    ids = []
    texts = []
    metadatas = []
    for index in range(len(chunks)):
        ids.append("chunk_" + str(index))
        texts.append(chunks[index]["text"])
        metadatas.append({"source": chunks[index]["source"]})

    # nomic-embed-text expects this prefix on documents it stores.
    texts_to_embed = []
    for text in texts:
        texts_to_embed.append("search_document: " + text)

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embed(texts_to_embed),
        metadatas=metadatas,
    )
    print("Indexed", len(chunks), "chunks from", KB_DIR)


def retrieve(query, k=3):
    """Return the k chunks most similar to the query, best match first."""
    collection = get_collection()
    if collection.count() == 0:
        build_index()
        collection = get_collection()

    # nomic-embed-text expects this prefix on search queries.
    query_embedding = embed(["search_query: " + query])[0]
    results = collection.query(query_embeddings=[query_embedding], n_results=k)

    # Chroma returns lists of lists (one inner list per query); we sent one query -> [0].
    found = []
    for index in range(len(results["ids"][0])):
        item = {
            "text": results["documents"][0][index],
            "source": results["metadatas"][0][index]["source"],
            "distance": results["distances"][0][index],  # 0 = identical meaning
        }
        found.append(item)
    return found


if __name__ == "__main__":
    build_index()

    query = "I was charged twice for the same transaction"
    results = retrieve(query)
    print()
    print("Query:", query)
    for item in results:
        print("  ", round(item["distance"], 3), item["source"], "|", item["text"][:80])

    sources = []
    for item in results:
        sources.append(item["source"])
    assert "duplicate_charges.md" in sources, "Expected duplicate_charges.md in the results"
    print()
    print("Retriever self-check passed.")