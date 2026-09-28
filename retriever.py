"""
policy search over data/kb/ (the rag part).

same LLM_PROVIDER switch as llm.py:
    ollama  nomic-embed-text + chroma, stored in chroma_db/
    groq    bge-small-en-v1.5 via fastembed with a plain in-memory search.
            groq has no embedding models, and 71 chunks don't need a database.

rebuild + self-check (rerun after editing data/kb/): python retriever.py
"""

import os


KB_DIR = "data/kb"
PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

if PROVIDER == "groq":
    import numpy
    from fastembed import TextEmbedding
    EMBED_MODEL = "BAAI/bge-small-en-v1.5"
    MODEL_CACHE_DIR = os.getenv("FASTEMBED_CACHE", "models_cache")
else:
    import chromadb
    import ollama
    EMBED_MODEL = "nomic-embed-text"
    DB_DIR = "chroma_db"
    COLLECTION_NAME = "policies"


def load_chunks():
    """one chunk per line, prefixed with the document title for context."""
    chunks = []
    for filename in sorted(os.listdir(KB_DIR)):
        if not filename.endswith(".md"):
            continue
        with open(os.path.join(KB_DIR, filename)) as file:
            lines = file.read().split("\n")

        title = lines[0].replace("#", "").strip()

        for line in lines[1:]:
            line = line.strip()
            if len(line) < 20:
                continue  # blank lines and sub-headings like "Phishing:"
            line = line.lstrip("- ")
            chunk = {
                "text": title + ": " + line,
                "source": filename,
            }
            chunks.append(chunk)
    return chunks


def get_distance(item):
    return item["distance"]


# ---- local: ollama + chroma

def embed(texts):
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    return response.embeddings


def get_collection():
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def build_chroma_index():
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

    # nomic-embed-text was trained with these task prefixes
    texts_to_embed = []
    for text in texts:
        texts_to_embed.append("search_document: " + text)

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embed(texts_to_embed),
        metadatas=metadatas,
    )
    print("Indexed", len(chunks), "chunks from", KB_DIR, "into Chroma")


def retrieve_chroma(query, k):
    collection = get_collection()
    if collection.count() == 0:
        build_chroma_index()
        collection = get_collection()

    query_embedding = embed(["search_query: " + query])[0]
    results = collection.query(query_embeddings=[query_embedding], n_results=k)

    # chroma returns one list per query, we only sent one
    found = []
    for index in range(len(results["ids"][0])):
        item = {
            "text": results["documents"][0][index],
            "source": results["metadatas"][0][index]["source"],
            "distance": results["distances"][0][index],
        }
        found.append(item)
    return found


# ---- hosted: fastembed, in memory

# loaded on first use, then reused
embedder = None
memory_index = None


def get_embedder():
    global embedder
    if embedder is None:
        # render's free plan has 0.1 cpu, extra threads just fight each other
        embedder = TextEmbedding(model_name=EMBED_MODEL, cache_dir=MODEL_CACHE_DIR, threads=1)
    return embedder


def build_memory_index():
    global memory_index
    chunks = load_chunks()

    texts = []
    for chunk in chunks:
        texts.append(chunk["text"])

    vectors = list(get_embedder().passage_embed(texts))

    memory_index = []
    for index in range(len(chunks)):
        memory_index.append({
            "text": chunks[index]["text"],
            "source": chunks[index]["source"],
            "vector": vectors[index],
        })
    print("Indexed", len(memory_index), "chunks from", KB_DIR, "in memory")


def cosine_distance(vector_a, vector_b):
    """same 0..2 scale as chroma's cosine distance, lower = closer."""
    similarity = numpy.dot(vector_a, vector_b) / (numpy.linalg.norm(vector_a) * numpy.linalg.norm(vector_b))
    return 1 - float(similarity)


def retrieve_memory(query, k):
    if memory_index is None:
        build_memory_index()

    query_vector = list(get_embedder().query_embed([query]))[0]

    scored = []
    for item in memory_index:
        scored.append({
            "text": item["text"],
            "source": item["source"],
            "distance": cosine_distance(query_vector, item["vector"]),
        })

    scored = sorted(scored, key=get_distance)
    return scored[:k]


# ---- used by the rest of the app

def build_index():
    if PROVIDER == "groq":
        build_memory_index()
    else:
        build_chroma_index()


def retrieve(query, k=3):
    if PROVIDER == "groq":
        return retrieve_memory(query, k)
    return retrieve_chroma(query, k)


if __name__ == "__main__":
    print("Provider:", PROVIDER, "| Embedding model:", EMBED_MODEL)
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
