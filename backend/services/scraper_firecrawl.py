import io
import logging
from typing import List
from firecrawl import FirecrawlApp

logger = logging.getLogger(__name__)

# Connect to your local Firecrawl instance
app = FirecrawlApp(api_key="test", api_url="http://localhost:3002")


async def scrape_url(url: str) -> str:
    """Scrape a single URL and return clean markdown text."""
    try:
        result = app.scrape(url, formats=["markdown"])
        markdown = result.markdown
        if not markdown or len(markdown) < 10:
            raise ValueError(f"Could not extract meaningful content from {url}")
        return markdown
    except Exception as e:
        raise ValueError(f"Firecrawl failed to scrape {url}: {e}")


async def scrape_multiple_urls(urls: List[str]) -> str:
    """Scrape multiple URLs and join their content."""
    results = []
    for url in urls:
        try:
            text = await scrape_url(url)
            results.append(text)
        except ValueError as e:
            logger.warning("Skipping URL: %s", e)
    return "\n\n---\n\n".join(results)


async def scrape_website(base_url: str) -> str:
    """
    Main entry point. Uses Firecrawl crawl for full sites,
    single scrape for deep/specific pages.
    """
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    path_parts = [p for p in parsed.path.split("/") if p]

    # Deep/specific page — scrape just that page
    if len(path_parts) >= 2:
        logger.info("Specific page detected, scraping single page: %s", base_url)
        return await scrape_url(base_url)

    # Full website — use Firecrawl crawl
    logger.info("Crawling full website: %s", base_url)
    try:
        result = app.crawl(
            base_url,
            limit=50,
            scrape_options={"formats": ["markdown"]}
        )
        pages = result.data
        if not pages:
            raise ValueError("Firecrawl returned no pages")

        contents = []
        for page in pages:
            md = page.markdown
            if md and len(md) > 100:
                contents.append(md)

        if not contents:
            raise ValueError("No meaningful content found")

        logger.info("Crawled %d pages from %s", len(contents), base_url)
        return "\n\n---\n\n".join(contents)

    except Exception as e:
        logger.warning("Crawl failed, falling back to single scrape: %s", e)
        return await scrape_url(base_url)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from a PDF file."""
    import fitz
    text_pages = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text_pages.append(page.get_text())
    return "\n".join(text_pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a Word (.docx) document."""
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_faq(faqs: List[dict]) -> str:
    """Format FAQ list into readable Q&A string."""
    entries = []
    for item in faqs:
        question = item.get("question", "").strip()
        answer = item.get("answer", "").strip()
        entries.append(f"Q: {question}\nA: {answer}")
    return "\n\n".join(entries)