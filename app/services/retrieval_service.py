from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

CHROMA_DIR = "../../chroma_db"
COLLECTION = "docker_docs"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

def retrieve_relevant_embeddings(query_embeddings, top_k=5):
    vector_store = Chroma(
        collection_name=COLLECTION,
        persist_directory=CHROMA_DIR,
        embedding_function=None
    )

    results = vector_store.similarity_search_by_vector(
        embedding=query_embeddings.tolist(),
        k=top_k
    )

    relevant_chunks = []

    for document in results:
        relevant_chunks.append([{
            "text": document.page_content,
            "metadata": document.metadata
        }])

    return relevant_chunks