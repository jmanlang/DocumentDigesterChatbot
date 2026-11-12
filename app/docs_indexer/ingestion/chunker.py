"""
Split a Markdown file into heading aware chunks.
"""
from typing import Generator

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


class MarkdownChunker:

    def __init__(self, tokenizer, target: int, overlap: int, max_tokens: int):
        """
        Creates a MarkdownChunker splitter with the given parameters.
        
        Args:
            tokenizer: The tokenizer to use for splitter.
            target (int): The chunk target size.
            overlap (int): The chunk overlap.
            max_tokens (int): The maximum number of tokens a chunk may be.
        """
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens

        self.headings = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#" * level, f"h{level}") for level in range(1,7)],
            strip_headers=False,
        )
        self.splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
            tokenizer=tokenizer,
            chunk_size=target,
            chunk_overlap=overlap,
        )

    def split(self, title: str, text: str) -> Generator[tuple[str, str]]:
        """
        Split a Markdown document into smaller, context-preserving passages.

        First, divides the document into sections based on Markdown headings,
        preserving their hierarchy as breadcrumbs. Each section is then split
        into smaller chunks using the configured text splitter.

        Args:
            title (str): The document title.

            text (str): The content of the document.

        Yields:
            tuple[str, str]: A tuple containing:
                - passage: The text chunk prefixed with the headings.
                - hierarchy: The hierarchical Markdown heading path.
        
        Raises:
            ValueError: If a formatted passage exceeds the configured maximum
            token limit of CHUNK_MAX_TOKENS.
        """

        # Split into Markdown heading sections
        for section in self.headings.split_text(text):
            # Preserve heading hierarchy as such:
            # Heading 1 > Heading 2
            hierarchy: str = " > ".join(section.metadata.values())

            # Split section text into text chunks
            for piece in self.splitter.split_text(section.page_content):
                passage: str = f"{hierarchy}\n\n{piece}" if hierarchy else piece
                formatted: str = f"title: {title} | text: {passage}"

                if len(self.tokenizer.encode(formatted, add_special_tokens=True)) > \
                    self.max_tokens:
                    raise ValueError(
                        f"Chunk exceeds CHUNK_MAX_TOKENS={self.max_tokens} for {title!r}; "
                        "reduce CHUNK_TARGET_TOKENS or shorten headings."
                        )

                yield passage, hierarchy
