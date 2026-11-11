import torch
from sentence_transformers import SentenceTransformer

device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = (
    torch.bfloat16
)

text_model = SentenceTransformer(
    "unsloth/embeddinggemma-2",
    device = device,
    model_kwargs = {"torch_dtype": dtype},
    config_kwargs = {"vision_config": None, "audio_config": None},
)

def embed_query(question: str):
    return text_model.encode(
        question,
        prompt_name="SearchQuery",
        truncate_dim=768,
        normalize_embeddings=True,
    )
# query = "How do I reset my password?"
# documents = [
#     "Select Forgot password on the sign-in page to receive a reset link.",
#     "Update your billing details from the account settings page.",
#     "Enable two-factor authentication to protect your account.",
# ]
# embedding_dim = 768

# query_embedding = text_model.encode(
#     [query],
#     prompt_name = "SearchQuery",
#     truncate_dim = embedding_dim,
#     normalize_embeddings = True,
# )
# document_embeddings = text_model.encode(
#     documents,
#     prompt_name = "Document",
#     truncate_dim = embedding_dim,
#     normalize_embeddings = True,
# )

# scores = text_model.similarity(query_embedding, document_embeddings)[0]
# for idx in scores.argsort(descending = True).tolist():
#     print(f"{scores[idx].item():.4f} | {documents[idx]}")