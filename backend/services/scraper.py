import io
import logging
from typing import List

import requests
from bs4 import BeautifulSoup

from crawl4ai import AsyncWebCrawler

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


async def scrape_url(url: str) -> str:
    """
    Fetch a web page and return clean plain text.
    Uses crawl4ai as primary (for JS rendering) and BeautifulSoup as fallback.

    Args:
        url: The URL to scrape.

    Returns:
        Cleaned plain text extracted from the page.

    Raises:
        ValueError: If the URL is unreachable, blocked, or contains no content.
    """
    # 1. Primary: Use crawl4ai for JS rendering
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            if result.success and result.markdown:
                # Minimum character threshold for a "real" page content
                if len(result.markdown) >= 500:
                    return result.markdown
                else:
                    logger.info(
                        "crawl4ai content too short (%d chars). Falling back to BeautifulSoup.",
                        len(result.markdown),
                    )
            else:
                logger.warning("crawl4ai failed for %s. Falling back to BeautifulSoup.", url)
    except Exception as e:
        logger.error("Error with crawl4ai for %s: %s. Falling back to BeautifulSoup.", url, e)

    # 2. Fallback: Use BeautifulSoup (robust for static sites or simple HTML)
    return _scrape_url_bs4(url)


def _scrape_url_bs4(url: str) -> str:
    """
    Fallback method using requests + BeautifulSoup.

    Args:
        url: The URL to scrape.

    Returns:
        Cleaned plain text extracted from the page body.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code in [401, 403]:
            raise ValueError(
                "This website is blocking automated access. Please try a different URL."
            )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise ValueError(f"Could not connect to URL '{url}': {e}") from e
    except requests.exceptions.Timeout as e:
        raise ValueError("The website took too long to respond. Please try again.") from e
    except requests.exceptions.HTTPError as e:
        raise ValueError(
            f"HTTP error {response.status_code} for URL '{url}': {e}"
        ) from e
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch URL '{url}': {e}") from e

    # Use lxml if available, otherwise fallback to html.parser
    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception:
        soup = BeautifulSoup(response.text, "html.parser")

    # 1. Remove standard boilerplate tags
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "button"]):
        tag.decompose()

    # 2. More aggressive boilerplate removal (selectors for cookie banners, popups, etc.)
    noise_selectors = [
        '[class*="cookie"]', '[id*="cookie"]',
        '[class*="consent"]', '[id*="consent"]',
        '[class*="banner"]', '[id*="banner"]',
        '[class*="popup"]', '[id*="popup"]',
        '[class*="modal"]', '[id*="modal"]',
        '[class*="gdpr"]', '[id*="gdpr"]',
        '[class*="overlay"]', '[id*="overlay"]',
        '[class*="policy"]', '[id*="policy"]',
        '#onetrust-banner-sdk', '.optanon-alert-box-wrapper', # Common third-party cookie solutions
    ]
    for selector in noise_selectors:
        try:
            for tag in soup.select(selector):
                tag.decompose()
        except Exception:
            pass

    # 3. Extract text more aggressively from meaningful tags
    content_root = soup.find("body") or soup
    
    # We use a newline separator to keep structural separation, then clean up
    text = content_root.get_text(separator="\n", strip=True)
    
    # 4. Clean up whitespace while preserving meaningful breaks
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean_text = "\n".join(lines)

    if len(clean_text) < 100:
        clean_text = " ".join(content_root.get_text(separator=" ").split())

    if not clean_text or len(clean_text) < 10:
        raise ValueError(
            "Could not extract any meaningful content from this website. Please try a different URL."
        )

    return clean_text


async def scrape_multiple_urls(urls: List[str]) -> str:
    """
    Scrape multiple URLs asynchronously and join their text content.

    Args:
        urls: List of URLs to scrape.

    Returns:
        All scraped texts joined by '\\n\\n---\\n\\n'. URLs that fail are skipped.
    """
    results = []
    for url in urls:
        try:
            text = await scrape_url(url)
            results.append(text)
        except ValueError as e:
            logger.warning("Skipping URL due to error: %s", e)

    return "\n\n---\n\n".join(results)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract plain text from a PDF file given its raw bytes.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        All pages' text joined as a single string.
    """
    import fitz  # pymupdf

    text_pages = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text_pages.append(page.get_text())

    return "\n".join(text_pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extract plain text from a Word (.docx) document given its raw bytes.

    Args:
        file_bytes: Raw bytes of the .docx file.

    Returns:
        All paragraphs joined as a single string.
    """
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_faq(faqs: List[dict]) -> str:
    """
    Format a list of FAQ dicts into a readable Q&A string.

    Args:
        faqs: List of dicts with 'question' and 'answer' keys.

    Returns:
        Formatted string with each entry as 'Q: ...\\nA: ...\\n\\n'.
    """
    entries = []
    for item in faqs:
        question = item.get("question", "").strip()
        answer = item.get("answer", "").strip()
        entries.append(f"Q: {question}\nA: {answer}")

    return "\n\n".join(entries)
