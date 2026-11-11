import re
from pathlib import Path

from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

# Configuration
RAW_FILE = Path("ingested_docs/Docker.md")
CHROMA_DIR = "./chroma_db"
COLLECTION = "docker_docs"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

MIN_CHUNK_CHARS = 150      # drop fragments smaller than this
MAX_CHUNK_CHARS = 1200     # hard cap — truncate anything bigger

SKIP_HEADERS = (
    "what's next",
    "next steps",
    "related information",
    "parent topic",
    "table of contents",
)



# Cleaning helpers
def strip_binary_blobs(text: str) -> str:
    """Remove table separators, base64 blobs, and other encoded junk."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()

        # Table separator rows like | --- | --- |
        if re.fullmatch(r"[\|\-\s:]+", stripped):
            continue

        # Very long lines with no whitespace (base64/hex blobs)
        if len(stripped) > 500 and " " not in stripped:
            continue

        # Data URIs
        if stripped.startswith("data:") or stripped.startswith("base64,"):
            continue

        lines.append(line)
    return "\n".join(lines)


def should_skip_heading(metadata: dict) -> bool:
    """Skip boilerplate sections by heading text."""
    parts = [
        metadata.get("h1", ""),
        metadata.get("h2", ""),
        metadata.get("h3", ""),
    ]
    heading = " ".join(p for p in parts if p).lower()
    return any(skip in heading for skip in SKIP_HEADERS)


# Phase 1: Parse pages
def parse_pages(raw_text: str):
    """Split the raw file into (url, body) page blocks and clean each."""
    pattern = r"----\s*\nurl:\s*(\S+)\s*\n----\s*\n(.*?)(?=----\s*\nurl:|$)"
    pages = []

    for url, body in re.findall(pattern, raw_text, flags=re.DOTALL):
        url = url.strip()

        body = strip_binary_blobs(body)
        body = re.sub(r"Table of contents\s*", "", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()

        if len(body) > 200:
            pages.append((url, body))

    return pages


# Phase 2: Semantic chunking
def chunk_pages(pages):
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
        ],
        strip_headers=False,
    )

    docs = []

    for url, body in pages:
        for hc in header_splitter.split_text(body):
            # Drop boilerplate sections
            if should_skip_heading(hc.metadata):
                continue

            text = hc.page_content.strip()

            # Drop fragments
            if len(text) < MIN_CHUNK_CHARS:
                continue

            # Truncate giant table rows / API schema dumps
            if len(text) > MAX_CHUNK_CHARS:
                text = text[:MAX_CHUNK_CHARS]

            docs.append(
                Document(
                    page_content=text,
                    metadata={"source_url": url, **hc.metadata},
                )
            )

    return docs


# Phase 3: Embed and store
def build_index(chunks):
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION,
    )
    return vectorstore



def main():
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Not found: {RAW_FILE.resolve()}")

    raw_text = RAW_FILE.read_text(encoding="utf-8")

    pages = parse_pages(raw_text)
    print(f"Parsed {len(pages)} doc pages from {RAW_FILE}")

    chunks = chunk_pages(pages)
    print(f"Created {len(chunks)} chunks")

    if not chunks:
        raise RuntimeError(
            "No chunks produced. Check Docker.md format and filters."
        )

    vectorstore = build_index(chunks)
    print(f"Indexed {vectorstore._collection.count()} vectors into {CHROMA_DIR}")

    # Sanity check
    print("\n=== Sanity check ===")
    results = vectorstore.similarity_search(
        "What does docker compose wait do?", k=3
    )
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source_url", "?")
        print(f"\n--- Result {i} | {source} ---")
        print(doc.page_content[:400])

    # Second check: verify provenance is populated
    print("\n=== Provenance check ===")
    empty_sources = sum(
        1 for d in chunks if not d.metadata.get("source_url")
    )
    if empty_sources:
        print(f"WARNING: {empty_sources} chunks missing source_url")
    else:
        print(f"OK: all {len(chunks)} chunks have source_url metadata")


if __name__ == "__main__":
    main()