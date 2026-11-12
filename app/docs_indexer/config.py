"""
Setup all variables in the .env file and validate them.
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Get the base directory of the project
BASE_DIR = Path(__file__).resolve().parents[2]

SOURCES = {
    "langchain_guides": "LANGCHAIN_GUIDES_DIR",
    "langchain_api": "LANGCHAIN_API_DIR",
    "docker": "DOCKER_DOCS_DIR",
    "git": "GIT_DOCS_DIR",
}

@dataclass
class Config:
    """
    Config class to initialize environment variables from .env file
    """
    model_id: str
    model_revision: str
    device: str
    model_dtype: str
    embedding_backend: str
    embedding_api_url: str
    embedding_api_model: str
    embedding_http_timeout: int
    tokenizer_id: str
    embedding_dimension: int
    embedding_batch_size: int
    normalize_embeddings: bool
    query_prompt_name: str
    chunk_target_tokens: int
    chunk_overlap_tokens: int
    chunk_max_tokens: int
    chroma_path: Path
    collection_name: str
    chroma_batch_size: int
    build_metadata_path: Path
    max_files: int
    roots: dict[str, Path]

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Config:
        """
        Load environment variables from a .env file and return a Config 
        instance.

        Args:
            env_file (Path | None): Optional path to the .env file. If not
            provided, it defaults to the .env file in the base directory.
        """
        path = env_file if env_file is not None else BASE_DIR / ".env"
        logger.info(f"ENV file loaded from: {path.as_uri()}")

        load_dotenv(dotenv_path=path, override=True)
        
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        logger.info("Loaded .env file...")

        config = cls(
            model_id=os.getenv("MODEL_ID", "unsloth/embeddinggemma-2"),
            model_revision=os.getenv("MODEL_REVISION", "main"),
            device=os.getenv("DEVICE", "auto"),
            model_dtype=os.getenv("MODEL_DTYPE", "auto"),
            embedding_backend=str(os.getenv("EMBEDDING_BACKEND", "sentence_transformers")),
            embedding_api_url=str(os.getenv("EMBEDDING_API_URL", "http://127.0.0.1:11434/api/embed")),
            embedding_api_model=str(os.getenv("EMBEDDING_API_MODEL", "embeddinggemma-2-GGUF")),
            embedding_http_timeout=int(os.getenv("EMBEDDING_HTTP_TIMEOUT", 180)),
            tokenizer_id=str(os.getenv("TOKENIZER_ID", "unsloth/embeddinggemma-2-GGUF")),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", 768)),
            embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", 16)),
            normalize_embeddings=os.getenv("NORMALIZE_EMBEDDINGS", "True").lower() == "true",
            query_prompt_name=os.getenv("QUERY_PROMPT_NAME", "default"),
            chunk_target_tokens=int(os.getenv("CHUNK_TARGET_TOKENS", 512)),
            chunk_overlap_tokens=int(os.getenv("CHUNK_OVERLAP_TOKENS", 50)),
            chunk_max_tokens=int(os.getenv("CHUNK_MAX_TOKENS", 1024)),
            chroma_path=BASE_DIR / os.getenv("CHROMA_PATH", "chroma_db"),
            collection_name=os.getenv("COLLECTION_NAME", "docs_collection"),
            chroma_batch_size=int(os.getenv("CHROMA_BATCH_SIZE", 32)),
            build_metadata_path=BASE_DIR / os.getenv(
                "BUILD_METADATA_PATH", "build_metadata.json"
            ),
            max_files=int(os.getenv("MAX_FILES", 0)),  # 0 means no limit
            roots={
                name: Path(val).resolve()
                for name, env_var in SOURCES.items()
                if (val := os.getenv(env_var)) is not None
            },
        )
        logger.info("Created configuration based on .env...")

        config.validate()
        logger.info("Validated .env...")

        return config

    def validate(self) -> None:
        """
        Validate the configuration values. Raises ValueError if any value is invalid.
        """
        logger.info("Validating .env values...")
        if self.embedding_backend not in {"llama_cpp", "ollama", "sentence_transformers"}:
            logger.error("EMBEDDING_BACKEND must be llama_cpp, ollama, or sentence_transformers")
            raise ValueError("EMBEDDING_BACKEND must be llama_cpp, ollama, or sentence_transformers")
        if self.embedding_backend in {"llama_cpp", "ollama"} and not self.embedding_api_url.startswith(("http://", "https://")):
            logger.error("EMBEDDING_API_URL must be a complete HTTP(S) URL")
            raise ValueError("EMBEDDING_API_URL must be a complete HTTP(S) URL")
        if self.embedding_dimension not in (128, 256, 512, 768):
            logger.error(f"Invalid embedding dimension: {self.embedding_dimension}. \
                         Must be one of 128, 256, 512, or 768.")
            raise ValueError("EMBEDDING_DIM must be 128, 256, 512, or 768")
        if not (0 <= self.chunk_overlap_tokens < self.chunk_target_tokens <= self.chunk_max_tokens <= 8192):
            logger.error("Require 0 <= overlap < target <= max <= 8192")
            raise ValueError("Require 0 <= overlap < target <= max <= 8192")
        if self.chunk_target_tokens < 80 or self.chunk_max_tokens < 100:
            logger.error("Chunk sizes are too small to preserve text and headings.")
            raise ValueError("Chunk sizes are too small to preserve text and headings")
        if self.model_dtype not in ("auto", "bfloat16", "float32"):
            logger.error("MODEL_DTYPE must be auto, bfloat16, or float32")
            raise ValueError("MODEL_DTYPE must be auto, bfloat16, or float32")
        if self.device not in ("auto", "cpu", "cuda"):
            logger.error("DEVICE must be auto, cpu, or cuda")
            raise ValueError("DEVICE must be auto, cpu, or cuda")
        if any(v < 1 for v in (self.embedding_batch_size, self.chroma_batch_size)):
            logger.error("Batch sizes must be positive")
            raise ValueError("Batch sizes must be positive")
        if self.max_files < 0:
            logger.error("MAX_FILES must be >= 0")
            raise ValueError("MAX_FILES must be >= 0")
