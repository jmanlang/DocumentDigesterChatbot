"""
Module for reading and processing markdown files for embedding.
"""

import re
import logging
from pathlib import Path
from collections.abc import Iterator

from config import Config

logger = logging.getLogger(__name__)

def markdown_files_to_embed(config: Config) -> Iterator[tuple[str, Path, str]]:
    """
    Iterate over markdown files in the specified roots and yield their content.

    Args:
        config (Config): The configuration object containing root directories.

    Yields:
        tuple[str, Path, str]: A tuple containing the source name, file path, 
        and relative path of each markdown file.
    """
    for source, root in config.roots.items():
        if not root.is_dir():
            logger.error(f"Missing documentation directory for \
                                    source '{source}': {root}")
            raise FileNotFoundError(f"Missing documentation directory for \
                                    source '{source}': {root}")

        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() in (".md"):
                relative = path.relative_to(root)

                logger.info(f"Yielding: Source: {source},\n\
                            File path: {path},\n\
                            Relative path: {relative.as_posix()}")
                yield source, path, relative.as_posix()

def read_markdown_file(path: Path) -> tuple[str, str]:
    """
    Read a markdown file and return its title and content. If a heading couldn't
    be derived, the name of the file is used instead.

    Args:
        path (Path): The path to the markdown file.

    Returns:
        tuple[str, str]: A tuple containing the title and content of the markdown file:
            - title: The title of the Markdown file.
            - text: The content of the Markdown file.
    """
    # Read the file content
    logger.info("Read file content...")
    text = path.read_text(encoding="utf-8", errors="ignore")

    # Convert to Unix line endings
    logger.info("Convert to Unix line endings...")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove YAML front matter if present
    logger.info("Remove YAML front matter if present...")
    text = re.sub(r"\A---\n.*?\n---\s*\n", "", text, flags=re.DOTALL).strip()

    # Extract the title from the first markdown heading or use the filename as a fallback
    logger.info("Extracting title...")
    match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    title = match.group(1).strip() if match else path.stem.replace("_", " ").replace("-", " ")

    return title[:180], text
    

                
