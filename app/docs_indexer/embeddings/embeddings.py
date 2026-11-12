"""
Load the embedding model based on the provided configuration.
"""

import torch
import logging
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer

from app.docs_indexer.config import Config

logger = logging.getLogger(__name__)

def load_embedding_model(config: Config) -> \
    tuple[SentenceTransformer, AutoTokenizer, str, torch.dtype]:
    """
    Load the embedding model based on the provided configuration.

    Args:
        config (Config): The configuration object containing model parameters.

    Returns:
        tuple[SentenceTransformer, AutoTokenizer, str, torch.dtype]: A tuple 
        containing the loaded embedding model, tokenizer, device, and model dtype.
    """
    device: str = "cuda" if torch.cuda.is_available() and config.device == "auto" \
        else config.device
    logger.info(f"Using device: {device}")

    dtype: str = config.model_dtype if config.model_dtype != "auto" \
        else "bfloat16" if torch.cuda.is_available() else "float32"

    model_dtype: torch.dtype = torch.bfloat16 if dtype == "bfloat16" else torch.float32
    logger.info(f"Using model dtype: {model_dtype}")

    model = SentenceTransformer(
        config.model_id,
        device=device,
        revision=config.model_revision,
        model_kwargs={
            "torch_dtype": model_dtype
        },
        config_kwargs={
            "vision_config": None,
            "audio_config": None
        },
    )
    logger.info(f"Loaded model: {config.model_id} (revision: {config.model_revision})")
    tokenizer = AutoTokenizer.from_pretrained(
        config.model_id,
        revision=config.model_revision
    )
    logger.info(f"Loaded tokenizer: {config.model_id} (revision: {config.model_revision})")

    logger.info(f"Returning...\nModel: {model},\nTokenizer: {tokenizer},\
                \nDevice: {device}, Model DType: {model_dtype}")
    
    return model, tokenizer, device, model_dtype
