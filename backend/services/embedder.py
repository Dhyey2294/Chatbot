import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"

import logging
import warnings
warnings.filterwarnings("ignore")

from huggingface_hub import login
from sentence_transformers import SentenceTransformer
from transformers.utils import logging as hf_logging
from huggingface_hub.utils import disable_progress_bars

# Suppress transformers and huggingface_hub logging/progress bars for cleaner startup
hf_logging.set_verbosity_error()
disable_progress_bars()
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

# Authenticate with HuggingFace Hub 
hf_token = os.getenv("HF_TOKEN")
if hf_token is not None and hf_token.strip() != "" and hf_token != "your_token_here":
    try:
        login(token=hf_token)
    except Exception as e:
        print(f"Warning: HuggingFace login failed: {e}")

# Load the model once at module level so it is ready when the server starts
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of text strings.

    Args:
        texts: A list of strings to embed.

    Returns:
        A list of embeddings, each represented as a list of floats.
    """
    embeddings = model.encode(texts)
    return embeddings.tolist()


def embed_single(text: str) -> list[float]:
    """
    Generate an embedding for a single text string.

    Args:
        text: The string to embed.

    Returns:
        A single embedding as a list of floats.
    """
    return embed_texts([text])[0]
