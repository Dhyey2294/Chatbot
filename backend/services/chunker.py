from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[str]:
    """
    Split input text into overlapping chunks using RecursiveCharacterTextSplitter.

    Args:
        text: The raw text to split.
        chunk_size: Maximum number of characters per chunk (default 500).
        chunk_overlap: Number of overlapping characters between chunks (default 50).

    Returns:
        A list of clean string chunks, each at least 30 characters long.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks = splitter.split_text(text)

    # Filter out noise/empty chunks shorter than 5 characters
    return [chunk for chunk in chunks if len(chunk) >= 5]
