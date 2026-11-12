"""
Unified interface to use either SentenceTransformer, Ollama, or llama.cpp 
for embedding creation.
"""

import numpy as np
import logging

from config import Config

# Task prefixes from Google's EmbeddingGemma 2 model card.
QUERY_PREFIXES = {
    "SearchQuery": "task: search result | query: ",
    "QuestionAnswering": "task: question answering | query: ",
    "CodeRetrieval": "task: code retrieval | query: ",
    "FactChecking": "task: fact checking | query: ",
}

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        if config.embedding_backend == "sentence_transformers":
            import torch
            from sentence_transformers import SentenceTransformer

            device: str = "cuda" if torch.cuda.is_available() and config.device == "auto" \
        else config.device
            logger.info(f"Using device: {device}")

            dtype: str = config.model_dtype if config.model_dtype != "auto" \
                else "bfloat16" if torch.cuda.is_available() else "float32"

            model_dtype: torch.dtype = torch.bfloat16 if dtype == "bfloat16" else torch.float32
            logger.info(f"Using model dtype: {model_dtype}")
            self.model = SentenceTransformer(
                config.model_id,
                revision=config.model_revision,
                device=device,
                model_kwargs={
                    "torch_dtype": dtype
                },
                config_kwargs={
                    "vision_config": None,
                    "audio_config": None
                },
            )

    def encode(self, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts using the configured embedding backend.

        Supports three embedding implementations:
            - SentenceTransformer: Generates embeddings locally using the loaded model.
            - Ollama: Sends HTTP requests to the Ollama embedding API.
            - llama.cpp: Sends HTTP requests to the OpenAI-compatible embeddings API.

        All generated embeddings are converted to NumPy float32 arrays.

        Args:
            texts (str): Texts for which to create embeddings.

        Returns:
            np.ndarray: A two-dimensional array of shape (number of input texts, \
            embedding_dimension), containing the generated embeddings as float32 values.

        Raises:
            requests.exceptions.RequestException: If an HTTP request fails.
            
            ValueError: If the embedding server returns an unexpected number
                of embeddings, invalid dimensions, or zero embeddings during
                normalization.
            
            ValueError: If the final embedding array has an unexpected shape
                or contains non-finite values.
        """
        if not texts:
            logging.info("No input texts. Returning empty embedding array...")
            return np.empty((0, self.config.embedding_dimension), dtype=np.float32)

        # If using SentenceTransformer...
        if (self.model is not None):
            logger.info("Using SentenceTransformer for embedding creation...")
            embeddings = self.model.encode(
                texts,
                prompt="",
                batch_size=self.config.embedding_batch_size,
                truncate_dim=self.config.embedding_dimension,
                normalize_embeddings=self.config.normalize_embeddings,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            embeddings = np.asarray(embeddings, dtype=np.float32)
        else:
            import requests

            batches = []
            logger.info(f"Processing in batches of size {self.config.embedding_batch_size}...")
            for start in range(0, len(texts), self.config.embedding_batch_size):
                # Extract current batch
                batch = texts[start:start + self.config.embedding_batch_size]
                if self.config.embedding_backend == "ollama":
                    logger.info("Using Ollama for batch processing...")
                    payload = {
                        "model": self.config.embedding_api_model,
                        "input": batch, 
                        "truncate": False
                    }
                else:
                    logger.info("Using llama.cpp for batch processing...")
                    payload = {
                        "model": self.config.embedding_api_model,
                        "input": batch,
                        "encoding_format": "float"
                    }

                logging.info("Sending off the batch to be processed...")
                response = requests.post(
                    self.config.embedding_api_url,
                    json=payload,
                    timeout=self.config.embedding_http_timeout
                )

                response.raise_for_status()
                data = response.json()
                logger.info("Got and parsed data from embedding model endpoint...")

                if self.config.embedding_backend == "ollama":
                    logger.info("Retrieving data according to ollama standard...")
                    result = data["embeddings"]
                else:
                    # The API may return entries out of order. The `index`
                    # field lets us reconstruct the input order reliably.
                    logger.info("Retrieving data according to llama.cpp standard...")
                    result = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]

                logger.info("Checking whether we have embeddings for the entire batch...")
                if len(result) != len(batch):
                    logger.error(f"Embedding server returned {len(result)} embeddings for {len(batch)} inputs")
                    raise ValueError(f"Embedding server returned {len(result)} embeddings for {len(batch)} inputs")

                logger.info("Appending accumulated embeddings...")
                batches.extend(result)

            logger.info("Converting all embeddings into numpy float32 array...")
            embeddings = np.asarray(batches, dtype=np.float32)

            logger.info("Ensuring the embedding server returned a 2D array: (number_of_inputs, \
                        embedding_dimensions)...")
            if embeddings.ndim != 2:
                logger.error(f"Expected a 2D embedding array, got shape {embeddings.shape}")
                raise ValueError(f"Expected a 2D embedding array, got shape {embeddings.shape}")

            logger.info("Checking whether returned embeddings have enough dimensions...")
            if embeddings.shape[-1] < self.config.embedding_dimension:
                raise ValueError(
                    f"Expected at least {self.config.embedding_dimension} dimensions, "
                    f"got {embeddings.shape[-1]}"
                )
            
            # Both servers typically return native 768-dimensional embeddings.
            logger.info("Truncating to configured dimension...")
            embeddings = embeddings[:, :self.config.embedding_dimension]
            if self.config.normalize_embeddings:
                logging.info("Normalizing embeddings...")
                norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
                if np.any(norm == 0):
                    logger.error("Embedding server returned a zero vector")
                    raise ValueError("Embedding server returned a zero vector")
                embeddings = embeddings / norm

        logger.info("Checking whether the number of embeddings and their dimensions \
                    are as configured and processed, and all embeddings are finite...")
        if embeddings.shape != (len(texts), self.config.embedding_dimension) \
            or not np.isfinite(embeddings).all():
            logger.error(f"Invalid embedding array: {embeddings.shape}")
            raise ValueError(f"Invalid embedding array: {embeddings.shape}")
        
        return embeddings.astype(np.float32, copy=False)
