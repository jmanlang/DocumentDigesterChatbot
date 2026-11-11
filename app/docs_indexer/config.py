"""
Setup all variables in the .env file and validate them.
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

from utils import compute_sha256

# Get the base directory of the project
BASE_DIR = Path(__file__).resolve().parents[3]

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
    state_path: Path
    state_save_every: int
    build_metadata_path: Path
    prune_missing: bool
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
        load_dotenv(dotenv_path=path, override=True)
        config = cls(
            model_id=str(os.getenv("MODEL_ID")),
            model_revision=str(os.getenv("MODEL_REVISION")),
            device=str(os.getenv("DEVICE")),
            model_dtype=str(os.getenv("MODEL_DTYPE")),
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
            state_path=BASE_DIR / os.getenv("STATE_PATH", "state.json"),
            state_save_every=int(os.getenv("STATE_SAVE_EVERY", 100)),
            build_metadata_path=BASE_DIR / os.getenv(
                "BUILD_METADATA_PATH", "build_metadata.json"
            ),
            prune_missing=os.getenv("PRUNE_MISSING", "False").lower() == "true",
            max_files=int(os.getenv("MAX_FILES", 0)),  # 0 means no limit
            roots={
                name: Path(val).resolve()
                for name, env_var in SOURCES.items()
                if (val := os.getenv(env_var)) is not None
            },
        )

        config.validate()
        return config

    def validate(self) -> None:
        """
        Validate the configuration values. Raises ValueError if any value is invalid.
        """
        if self.embedding_dimension not in (128, 256, 512, 768):
            raise ValueError("EMBEDDING_DIM must be 128, 256, 512, or 768")
        if not (0 <= self.chunk_overlap_tokens < self.chunk_target_tokens <= self.chunk_max_tokens <= 8192):
            raise ValueError("Require 0 <= overlap < target <= max <= 8192")
        if self.chunk_target_tokens < 80 or self.chunk_max_tokens < 100:
            raise ValueError("Chunk sizes are too small to preserve text and headings")
        if self.model_dtype not in ("auto", "bfloat16", "float32"):
            raise ValueError("MODEL_DTYPE must be auto, bfloat16, or float32")
        if self.device not in ("auto", "cpu", "cuda"):
            raise ValueError("DEVICE must be auto, cpu, or cuda")
        if any(v < 1 for v in (self.embedding_batch_size, self.chroma_batch_size, self.state_save_every)):
            raise ValueError("Batch sizes and STATE_SAVE_EVERY must be positive")
        if self.max_files < 0:
            raise ValueError("MAX_FILES must be >= 0")