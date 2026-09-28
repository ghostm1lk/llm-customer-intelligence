"""
retriever.py - the Knowledge Layer (RAG retrieval).

    1. Splits every policy document in data/kb/ into small chunks.
    2. Turns each chunk into an embedding (a list of numbers that captures its meaning).
    3. For a customer message, finds the chunks whose meaning is closest.

Two backends, chosen with the same LLM_PROVIDER setting as llm.py:

    LLM_PROVIDER=ollama (default)  nomic-embed-text in Ollama + Chroma vector database (folder chroma_db/)
    LLM_PROVIDER=groq              bge-small-en-v1.5 running inside this app (fastembed, CPU only)
                                   + a plain in-memory search. Groq has no embedding models, and
                                   71 chunks do not need a database; this keeps memory low on Render.

Before running (ollama):  ollama pull nomic-embed-text
Before running (groq):    nothing - the small model downloads automatically the first time

Rebuild the index and run the self-check (do this whenever data/kb/ changes):
    python retriever.py
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


def get_distance(item):
    """Used for sorting results: smaller distance = more similar."""
    return item["distance"]


# ================================================================ local: Ollama + Chroma

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


def build_chroma_index():
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
    print("Indexed", len(chunks), "chunks from", KB_DIR, "into Chroma")


def retrieve_chroma(query, k):
    """Return the k chunks most similar to the query, using Chroma."""
    collection = get_collection()
    if collection.count() == 0:
        build_chroma_index()
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


# ================================================================ hosted: fastembed, in memory

# Filled the first time they are needed, then reused for every request.
embedder = None
memory_index = None


def get_embedder():
    """Load the small embedding model once (downloads ~130 MB the very first time)."""
    global embedder  # "global" = change the variable defined outside this function
    if embedder is None:
        # threads=1: small hosting plans have a fraction of one CPU; more threads only compete.
        embedder = TextEmbedding(model_name=EMBED_MODEL, cache_dir=MODEL_CACHE_DIR, threads=1)
    return embedder


def build_memory_index():
    """Embed every chunk once and keep the vectors in memory."""
    global memory_index
    chunks = load_chunks()

    texts = []
    for chunk in chunks:
        texts.append(chunk["text"])

    # passage_embed = embeddings for stored documents (the model handles any prefixes itself).
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
    """0 = same direction (same meaning), up to 2 = opposite. Same scale as Chroma's cosine distance."""
    similarity = numpy.dot(vector_a, vector_b) / (numpy.linalg.norm(vector_a) * numpy.linalg.norm(vector_b))
    return 1 - float(similarity)


def retrieve_memory(query, k):
    """Return the k chunks most similar to the query, by comparing against every chunk."""
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

    # Sort from most to least similar and keep the first k.
    scored = sorted(scored, key=get_distance)
    return scored[:k]


# ================================================================ the functions other files use

def build_index():
    """(Re)build the search index for the active backend."""
    if PROVIDER == "groq":
        build_memory_index()
    else:
        build_chroma_index()


def retrieve(query, k=3):
    """Return the k chunks most similar to the query, best match first."""
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
