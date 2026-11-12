import numpy as np

from app.docs_indexer.config import Config
from app.docs_indexer.embeddings.embeddings import EmbeddingClient, QUERY_PREFIXES

config = Config.from_env()
if (config.query_prompt_name in QUERY_PREFIXES):
    query_prefix = QUERY_PREFIXES[config.query_prompt_name]
else:
    raise ValueError(f"Unsupported QUERY_PROMPT_NAME: {config.query_prompt_name}")

embedding_client = EmbeddingClient(config)


def embed_query(question: str) -> np.ndarray:
    """Return one query vector with the configured task prefix and dimensions."""
    # The shared client accepts prepared text, so apply the query prefix once.
    return embedding_client.encode([query_prefix + question])[0]
