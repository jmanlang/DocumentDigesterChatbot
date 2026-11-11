"""
Helper functions for the docs_indexer module.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

def compute_sha256(text: str) -> str:
    """
    Compute the SHA256 hash of the given text. Used to detect changes in the
    content of documents and return unique Chroma IDs for each document.

    Args:
        text (str): The input text to hash.

    Returns:
        str: The SHA256 hash of the input text.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def save_json(path: Path, data: dict[str, Any]) -> None:
    """
    Save a dictionary as a JSON file.

    Args:
        path (Path): The path to the output JSON file.
        data (dict): The dictionary to save as JSON.
    """
    # Ensure the parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(data, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )