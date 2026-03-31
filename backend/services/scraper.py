import asyncio
import io
import logging
import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import urljoin, urlparse

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
                if len(result.markdown) >= 100:
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
    for tag in soup.find_all(["script", "style", "nav", "header", "aside", "noscript", "svg", "button"]):
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
    Scrape multiple URLs concurrently and join their text content.

    Args:
        urls: List of URLs to scrape.

    Returns:
        All scraped texts joined by '\n\n---\n\n'. URLs that fail are skipped.
    """
    async def safe_scrape(url):
        try:
            return await scrape_url(url)
        except ValueError as e:
            logger.warning("Skipping URL due to error: %s", e)
            return None

    results = await asyncio.gather(*[safe_scrape(url) for url in urls])
    return "\n\n---\n\n".join(r for r in results if r)


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


async def discover_urls(base_url: str) -> List[str]:
    """
    Find up to 50 related URLs to scrape from a website.
    Tries sitemaps first, then falls back to link crawling.
    """
    logger.info("Discovering URLs for %s", base_url)
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    
    # 1. Sitemap detection
    sitemap_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/sitemap.xml"]
    for path in sitemap_paths:
        sitemap_url = urljoin(f"{parsed_base.scheme}://{base_domain}", path)
        try:
            logger.info("Checking sitemap: %s", sitemap_url)
            response = requests.get(sitemap_url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                urls = []
                root = ET.fromstring(response.content)
                
                # Sitemaps often have namespaces like {http://www.sitemaps.org/schemas/sitemap/0.9}
                ns = {'ns': root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}
                
                # Check for sitemap index or regular sitemap
                if 'sitemapindex' in root.tag:
                    logger.info("Sitemap index found at %s", sitemap_url)
                    for sitemap in root.findall('.//ns:sitemap', ns) if ns else root.findall('.//sitemap'):
                        loc = sitemap.find('ns:loc', ns) if ns else sitemap.find('loc')
                        if loc is not None and loc.text:
                            # Fetch child sitemap
                            try:
                                child_res = requests.get(loc.text, headers=HEADERS, timeout=10)
                                if child_res.status_code == 200:
                                    child_root = ET.fromstring(child_res.content)
                                    child_ns = {'ns': child_root.tag.split('}')[0].strip('{')} if '}' in child_root.tag else {}
                                    for url_tag in child_root.findall('.//ns:url', child_ns) if child_ns else child_root.findall('.//url'):
                                        loc_tag = url_tag.find('ns:loc', child_ns) if child_ns else url_tag.find('loc')
                                        if loc_tag is not None and loc_tag.text:
                                            if urlparse(loc_tag.text).netloc == base_domain:
                                                urls.append(loc_tag.text)
                                                if len(urls) >= 50:
                                                    break
                            except Exception:
                                continue
                        if len(urls) >= 50:
                            break
                else:
                    logger.info("Regular sitemap found at %s", sitemap_url)
                    for url_tag in root.findall('.//ns:url', ns) if ns else root.findall('.//url'):
                        loc = url_tag.find('ns:loc', ns) if ns else url_tag.find('loc')
                        if loc is not None and loc.text:
                            if urlparse(loc.text).netloc == base_domain:
                                urls.append(loc.text)
                                if len(urls) >= 50:
                                    break

                if urls:
                    # Deduplicate and limit
                    final_urls = list(dict.fromkeys(urls))[:50]
                    logger.info("Sitemap discovery successful: found %d URLs", len(final_urls))
                    return final_urls
        except Exception as e:
            logger.debug("Sitemap check failed for %s: %s", sitemap_url, e)
            continue

    # 2. Link crawling fallback
    logger.info("No sitemap found, falling back to link crawling for %s", base_url)
    try:
        response = requests.get(base_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        links = [base_url]
        excluded_exts = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.css', '.js', '.mp4', '.mp3'}
        
        for a in soup.find_all('a', href=True):
            url = urljoin(base_url, a['href'])
            parsed_url = urlparse(url)
            
            # Filter: same domain, no fragments, no excluded extensions
            if (parsed_url.netloc == base_domain and 
                not parsed_url.fragment and 
                not any(parsed_url.path.lower().endswith(ext) for ext in excluded_exts)):
                links.append(url)
            
            if len(set(links)) >= 50:
                break
        
        final_links = list(dict.fromkeys(links))[:50]
        logger.info("Link crawling discovery: found %d URLs", len(final_links))
        return final_links
    except Exception as e:
        logger.error("Link crawling failed for %s: %s", base_url, e)
        return [base_url]


async def scrape_website(base_url: str) -> str:
    """
    Main entry point for full website scraping.
    Discovers URLs and scrapes them all.
    If the URL is a specific deep page, it scrapes only that page.
    """
    parsed = urlparse(base_url)
    # If URL has a deep path (more than 1 segment), treat as a single page
    path_parts = [p for p in parsed.path.split('/') if p]
    if len(path_parts) >= 2:
        logger.info("Specific page URL detected, scraping single page: %s", base_url)
        return await scrape_url(base_url)

    # Otherwise do full website discovery
    urls = await discover_urls(base_url)
    logger.info("Starting scrape for %d discovered URLs from %s", len(urls), base_url)

    combined_content = await scrape_multiple_urls(urls)
    return combined_content
