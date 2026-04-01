import asyncio
import io
import logging
import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup



logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _normalize_url(u: str) -> str:
    """Strip query params and fragments to deduplicate URLs by path."""
    return urlparse(u)._replace(query="", fragment="").geturl()


async def _fetch_with_retry(client, url, retries=3, delay=1):
    """Fetch a URL with retries on connection error or 5xx response."""
    for attempt in range(retries):
        try:
            response = await client.get(url, headers=HEADERS, timeout=15)
            if response.status_code < 500:
                return response
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        if attempt < retries - 1:
            await asyncio.sleep(delay)
    return None


async def scrape_url(url: str) -> str:
    """
    Fetch a web page and return clean plain text.
    Primary: httpx + BeautifulSoup.
    Fallback: Playwright headless Chromium (for JS-rendered sites).
    """
    result = await _scrape_url_bs4(url)

    if len(result) < 500:
        logger.info(
            "BeautifulSoup returned only %d chars for %s — trying Playwright fallback",
            len(result),
            url,
        )
        try:
            playwright_result = await _scrape_url_playwright(url)
            if len(playwright_result) > len(result):
                logger.info(
                    "Playwright returned better content (%d chars), using it",
                    len(playwright_result),
                )
                return playwright_result
            else:
                logger.info("Playwright did not improve result, keeping BeautifulSoup output")
        except Exception as e:
            logger.warning("Playwright fallback failed for %s: %s", url, e)

    return result


async def _scrape_url_bs4(url: str) -> str:
    """
    Fallback method using httpx + BeautifulSoup.

    Args:
        url: The URL to scrape.

    Returns:
        Cleaned plain text extracted from the page body.
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await _fetch_with_retry(client, url)
            if not response:
                raise ValueError(f"Failed to fetch content from {url} after retries.")

            if response.status_code in [401, 403]:
                raise ValueError(
                    "This website is blocking automated access. Please try a different URL."
                )
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ValueError(
            f"HTTP error {response.status_code} for URL '{url}': {e}"
        ) from e
    except Exception as e:
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

    # 3. Extract text from meaningful tags
    content_root = soup.find("body") or soup
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


async def _scrape_url_playwright(url: str) -> str:
    """
    Fallback scraper using Playwright headless Chromium.
    Used when BeautifulSoup returns too little content (JS-rendered sites).
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ValueError(
            "Playwright is not installed. Run: pip install playwright && python -m playwright install chromium"
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers(
                {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    )
                }
            )
            await page.goto(url, wait_until="networkidle", timeout=30000)
            # Wait a bit extra for lazy-loaded content
            await page.wait_for_timeout(2000)
            html = await page.content()
        finally:
            await browser.close()

    # Parse the JS-rendered HTML with BeautifulSoup
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(
        ["script", "style", "nav", "header", "aside", "noscript", "svg", "button"]
    ):
        tag.decompose()

    noise_selectors = [
        '[class*="cookie"]',
        '[id*="cookie"]',
        '[class*="consent"]',
        '[id*="consent"]',
        '[class*="banner"]',
        '[id*="banner"]',
        '[class*="popup"]',
        '[id*="popup"]',
        '[class*="modal"]',
        '[id*="modal"]',
        '[class*="gdpr"]',
        '[id*="gdpr"]',
        '[class*="overlay"]',
        '[id*="overlay"]',
        '[class*="policy"]',
        '[id*="policy"]',
        "#onetrust-banner-sdk",
        ".optanon-alert-box-wrapper",
    ]
    for selector in noise_selectors:
        try:
            for tag in soup.select(selector):
                tag.decompose()
        except Exception:
            pass

    content_root = soup.find("body") or soup
    text = content_root.get_text(separator="\n", strip=True)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    clean_text = "\n".join(lines)

    if len(clean_text) < 100:
        clean_text = " ".join(content_root.get_text(separator=" ").split())

    if not clean_text or len(clean_text) < 10:
        raise ValueError("Playwright could not extract meaningful content from this URL.")

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
    Find up to 100 related URLs to scrape from a website.
    Tries sitemaps first, then falls back to link crawling.
    """
    logger.info("Discovering URLs for %s", base_url)
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    urls = []

    async def fetch_sitemap_urls(sitemap_url: str, client: httpx.AsyncClient, depth: int = 0):
        if depth > 2:
            return
        try:
            logger.info("Checking sitemap: %s (depth %d)", sitemap_url, depth)
            response = await _fetch_with_retry(client, sitemap_url)
            if not response or response.status_code != 200:
                return

            root = ET.fromstring(response.content)
            ns = {"ns": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}

            if "sitemapindex" in root.tag:
                logger.info("Sitemap index found at %s", sitemap_url)
                child_sitemap_locs = []
                for sitemap in (root.findall(".//ns:sitemap", ns) if ns else root.findall(".//sitemap")):
                    loc = sitemap.find("ns:loc", ns) if ns else sitemap.find("loc")
                    if loc is not None and loc.text:
                        child_sitemap_locs.append(loc.text)

                # Prioritize order: pages > blogs > collections > products
                def sitemap_priority(loc_url: str) -> int:
                    if "pages" in loc_url: return 0
                    if "blogs" in loc_url: return 1
                    if "collections" in loc_url: return 2
                    if "products" in loc_url: return 3
                    return 2

                child_sitemap_locs.sort(key=sitemap_priority)
                for child_loc in child_sitemap_locs:
                    await fetch_sitemap_urls(child_loc, client, depth + 1)
            else:
                # Regular sitemap
                for url_tag in (root.findall(".//ns:url", ns) if ns else root.findall(".//url")):
                    loc = url_tag.find("ns:loc", ns) if ns else url_tag.find("loc")
                    if loc is not None and loc.text:
                        if urlparse(loc.text).netloc == base_domain:
                            urls.append(loc.text)
        except Exception as e:
            logger.debug("Sitemap check failed for %s: %s", sitemap_url, e)

    # 1. Sitemap detection
    sitemap_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/sitemap.xml"]
    async with httpx.AsyncClient(follow_redirects=True) as client:
        for path in sitemap_paths:
            sitemap_url = urljoin(f"{parsed_base.scheme}://{base_domain}", path)
            await fetch_sitemap_urls(sitemap_url, client)

        if urls:
            # Deduplicate by path and limit to 100
            seen_paths = set()
            final_urls = []
            for u in urls:
                norm = _normalize_url(u)
                if norm not in seen_paths:
                    seen_paths.add(norm)
                    final_urls.append(u)
            
            final_urls = final_urls[:100]
            logger.info("Sitemap discovery successful: found %d URLs", len(final_urls))
            return final_urls

        # 2. Link crawling fallback
        logger.info("No sitemap found, falling back to link crawling for %s", base_url)
        try:
            response = await _fetch_with_retry(client, base_url)
            if not response:
                return [base_url]
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            links = [base_url]
            excluded_exts = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".css", ".js", ".mp4", ".mp3"}
            
            for a in soup.find_all("a", href=True):
                url = urljoin(base_url, a["href"])
                parsed_url = urlparse(url)
                
                # Filter: same domain, no excluded extensions
                if (parsed_url.netloc == base_domain and 
                    not any(parsed_url.path.lower().endswith(ext) for ext in excluded_exts)):
                    links.append(url)
            
            # Deduplicate by path and limit to 100
            seen_paths = set()
            final_links = []
            for u in links:
                norm = _normalize_url(u)
                if norm not in seen_paths:
                    seen_paths.add(norm)
                    final_links.append(u)
            
            final_links = final_links[:100]
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
    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) >= 2:
        logger.info("Specific page URL detected, scraping single page: %s", base_url)
        return await scrape_url(base_url)

    # Otherwise do full website discovery
    urls = await discover_urls(base_url)
    logger.info("Starting scrape for %d discovered URLs from %s", len(urls), base_url)

    combined_content = await scrape_multiple_urls(urls)
    return combined_content
