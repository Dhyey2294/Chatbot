import io
import re
import asyncio
import logging
from typing import List
from urllib.parse import urlparse
from firecrawl import FirecrawlApp

logger = logging.getLogger(__name__)

# Connect to your local Firecrawl instance
app = FirecrawlApp(api_key="test", api_url="http://localhost:3002")

# Maximum URLs to scrape per website
MAX_URLS = 200

# ─────────────────────────────────────────────
# URL FILTERING
# ─────────────────────────────────────────────

# URL patterns that are universally useless across ALL website types.
# These never contain content a chatbot needs to answer questions.
SKIP_PATTERNS = [
    # Auth / account
    r"/login", r"/logout", r"/signin", r"/signup", r"/register",
    r"/account", r"/my-account", r"/profile", r"/password",
    # Cart / checkout / transactional
    r"/cart", r"/checkout", r"/order", r"/orders", r"/payment",
    r"/wishlist", r"/bag",
    # Static assets and files
    r"/cdn/", r"/assets/", r"/static/", r"/dist/", r"/_next/",
    r"\.jpg$", r"\.jpeg$", r"\.png$", r"\.gif$", r"\.webp$",
    r"\.svg$", r"\.ico$", r"\.css$", r"\.js$", r"\.woff",
    r"\.pdf$", r"\.zip$", r"\.xml$",
    # Search / filter / sorting (dynamic/duplicate content)
    r"/search", r"\?q=", r"\?query=", r"\?s=",
    r"\?sort", r"\?filter", r"\?page=", r"\?ref=",
    r"\?variant=", r"\?color=", r"\?size=", r"\?utm_",
    # Admin / API / technical
    r"/admin", r"/api/", r"/wp-admin", r"/wp-json",
    r"/feed", r"/rss", r"/sitemap",
    # Non-HTTP
    r"javascript:", r"mailto:", r"tel:",
    # Anchor-only
    r"^#",
]

SKIP_COMPILED = [re.compile(p, re.IGNORECASE) for p in SKIP_PATTERNS]


def _should_skip(url: str) -> bool:
    """Return True if the URL should be excluded from scraping."""
    return any(p.search(url) for p in SKIP_COMPILED)


# ─────────────────────────────────────────────
# URL PRIORITY SCORING
# ─────────────────────────────────────────────

# Higher score = scraped first within the MAX_URLS cap.
# Generic scoring — works for any website type.
PRIORITY_RULES = [
    # Tier 1 — Core informational pages (score 100)
    (100, [
        r"/(about|about-us|our-story|who-we-are|company|brand)/?$",
        r"/(contact|contact-us|get-in-touch|reach-us)/?$",
        r"/(faq|faqs|frequently-asked|help|support)/?$",
        r"/(pricing|plans|packages|tariff)/?$",
        r"/(services|our-services|what-we-do|offerings)/?$",
        r"/(team|our-team|leadership|founders|staff)/?$",
        r"/(mission|vision|values|culture)/?$",
    ]),
    # Tier 2 — Policy / legal (score 80)
    (80, [
        r"/(privacy|privacy-policy|terms|terms-of-service|terms-and-conditions)/?$",
        r"/(return|refund|shipping|delivery|exchange)(-policy)?/?$",
        r"/(warranty|guarantee|cancellation)/?$",
        r"/(disclaimer|legal|cookie-policy)/?$",
    ]),
    # Tier 3 — Content / product / category pages (score 60)
    (60, [
        r"/pages/",
        r"/collections/",
        r"/categories?/",
        r"/products?/",
        r"/services?/",
        r"/courses?/",
        r"/menu/",
        r"/shop/",
        r"/store/",
        r"/portfolio/",
        r"/projects?/",
        r"/case-studies?/",
    ]),
    # Tier 4 — Blog / news / resources (score 40)
    (40, [
        r"/blog/",
        r"/news/",
        r"/articles?/",
        r"/resources?/",
        r"/insights?/",
        r"/guides?/",
        r"/tutorials?/",
        r"/learn/",
        r"/academy/",
    ]),
    # Tier 5 — Everything else valid gets score 20 (default)
]

PRIORITY_COMPILED = [
    (score, [re.compile(p, re.IGNORECASE) for p in patterns])
    for score, patterns in PRIORITY_RULES
]


def _priority_score(url: str) -> int:
    """Return a priority score for a URL. Higher = scraped first."""
    path = urlparse(url).path

    # Homepage always gets highest priority
    if path in ("", "/"):
        return 200

    for score, patterns in PRIORITY_COMPILED:
        if any(p.search(path) for p in patterns):
            return score

    return 20  # default for unrecognized but valid pages


def _filter_and_prioritize(urls: List[str], base_url: str) -> List[str]:
    """
    1. Remove external domains
    2. Remove universally useless URLs
    3. Deduplicate
    4. Sort by priority score (highest first)
    5. Cap at MAX_URLS
    """
    base_domain = urlparse(base_url).netloc
    seen = set()
    candidates = []

    for url in urls:
        url = url.strip().rstrip("/")
        if not url:
            continue

        # Skip external domains
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != base_domain:
            continue

        # Skip universally useless URLs
        if _should_skip(url):
            continue

        # Deduplicate
        if url in seen:
            continue
        seen.add(url)
        candidates.append(url)

    # Sort by priority score descending
    candidates.sort(key=_priority_score, reverse=True)

    logger.info(
        "URL filtering: %d discovered → %d after filter → %d after cap",
        len(urls), len(candidates), min(len(candidates), MAX_URLS)
    )

    return candidates[:MAX_URLS]

# CONTENT CLEANING

LINE_DROP_PATTERNS = [
    # Image-only lines
    r"^\s*!\[.*?\]\(.*?\)\s*$",
    # Empty links
    r"^\s*\[\]\(.*?\)\s*$",
    # Shopify-specific anchors and CDN
    r"#shopify-section-",
    r"cdn\.shopify\.com",
    # Cookie / GDPR
    r"OneTrust|onetrust|Privacy Preference|GDPR",
    r"^\s*(Allow All|Reject All|Confirm My Choices)\s*$",
    r"^\s*Cookies Details\s*$",
    r"^\s*Always Active\s*$",
    r"^\s*Consent Leg\.Interest\s*$",
    r"^\s*checkbox label label\s*$",
    # Common UI widget strings (universal)
    r"^\s*Skip to (content|main|navigation|nav)\s*$",
    r"^\s*Added [Tt]o (Wishlist|Bag|Cart|Basket)\s*$",
    r"^\s*(ADD TO BAG|ADD TO CART|BUY NOW|ADD TO BASKET)\s*$",
    r"^\s*similar products\s*$",
    r"^\s*(Free shipping|Fresh Fashion)\s*$",
    r"^\s*Your wishlist has been temporarily saved.*$",
    r"^\s*Please (Log ?in|Login|Sign ?in).*wishlist.*$",
    r"^\s*Please (Login|Sign ?in)\s*$",
    r"^\s*/ Signup\s*$",
    r"^\s*Open media \d+ in modal\s*$",
    r"^\s*View full details\s*$",
    r"^\s*(Email|Facebook|Twitter|Pinterest|Copy Link)\s*$",
    r"^\s*CHOOSE YOUR SHIPPING LOCATION\s*$",
    r"^\s*Remember Selection\s*$",
    r"^\s*CONTINUE\s*$",
    r"^\s*(Apply|Cancel|Clear)\s*$",
    r"^\s*Powered by\s*$",
    r"^\s*(Back|Search|Filter) (Button|Icon)\s*$",
    r"!\[share\]",
    r"data:image/",
    r"Choosing a selection results in a full page refresh",
    r"Opens in a new window",
    # Shopify product page boilerplate
    r"^\s*Unit price\s*/\s*per\s*$",
    r"^\s*Sale\s+Sold out\s*$",
    r"^\s*MRP incl\.of all taxes\s*$",
    r"^\s*Regular price\s*$",
    r"^\s*x\s*$",
    r"^\s*={10,}\s*$",  # Long lines of ===
    r"^\s*-{10,}\s*$",  # Long lines of ---
]

LINE_DROP_COMPILED = [re.compile(p, re.IGNORECASE) for p in LINE_DROP_PATTERNS]


def _clean_markdown(text: str) -> str:
    """
    Post-process scraped markdown to remove noise before chunking.
    Universal — works across e-commerce, SaaS, food, education, etc.
    """
    lines = text.splitlines()
    cleaned = []

    for line in lines:
        if any(p.search(line) for p in LINE_DROP_COMPILED):
            continue
        # Drop image-linked images: [![](img)](url)
        if re.match(r"^\s*\[!\[.*?\]\(.*?\)\]\(.*?\)\s*$", line):
            continue
        cleaned.append(line)

    result = "\n".join(cleaned)

    # Collapse 3+ blank lines → 2
    result = re.sub(r"\n{3,}", "\n\n", result)

    # Convert markdown links to plain text: [label](url) → label
    result = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", result)

    # Remove leftover bare URLs
    result = re.sub(r"https?://\S+", "", result)

    # Remove lines that became empty after processing
    result = "\n".join(line for line in result.splitlines() if line.strip())

    return result.strip()


# CORE SCRAPING

async def scrape_url(url: str) -> str:
    """Scrape a single URL and return cleaned markdown."""
    try:
        result = await asyncio.to_thread(
            app.scrape,
            url,
            formats=["markdown"],
            only_main_content=True,
        )
        markdown = result.markdown
        if not markdown or len(markdown) < 10:
            raise ValueError(f"No meaningful content at {url}")
        return _clean_markdown(markdown)
    except Exception as e:
        raise ValueError(f"Firecrawl failed to scrape {url}: {e}")


async def scrape_multiple_urls(urls: List[str]) -> str:
    """Scrape multiple URLs and join their content."""
    async def _safe(url):
        try:
            return await scrape_url(url)
        except ValueError as e:
            logger.warning("Skipping %s: %s", url, e)
            return None

    results = await asyncio.gather(*[_safe(u) for u in urls])
    return "\n\n---\n\n".join(r for r in results if r)


async def scrape_website(base_url: str) -> str:
    """
    Main entry point.

    Flow A — Deep/specific page (2+ path segments):
      Scrape that single page directly.

    Flow B — Homepage or shallow URL:
      1. Map  → discover all URLs on the site
      2. Filter + prioritize → keep up to MAX_URLS most informative URLs
      3. Scrape each URL individually
      Fallback 1: Firecrawl crawl (if Map fails)
      Fallback 2: Single page scrape (if crawl also fails)
    """
    parsed = urlparse(base_url)
    path_parts = [p for p in parsed.path.split("/") if p]

    # ── Flow A: Specific deep page ─────────────────────────────────────────
    if len(path_parts) >= 2:
        logger.info("Specific page — scraping directly: %s", base_url)
        content = await scrape_url(base_url)
        _save_debug(content)
        return content

    # ── Flow B: Full website via Map ───────────────────────────────────────
    logger.info("Full site scrape starting for: %s", base_url)

    try:
        # Step 1: Discover all URLs
        logger.info("Running Map on %s ...", base_url)
        map_result = await asyncio.to_thread(app.map, base_url)

        # Extract plain URL strings from whatever Map returns
        # Map can return: a list of strings, a MapResponse object,
        # a list of LinkResult objects, or an iterable
        raw = []
        if isinstance(map_result, list):
            raw = map_result
        elif hasattr(map_result, "links"):
            raw = map_result.links or []
        elif hasattr(map_result, "urls"):
            raw = map_result.urls or []
        else:
            try:
                raw = list(map_result)
            except Exception:
                raw = []

        # Normalize every item to a plain string
        all_urls = []
        for item in raw:
            if isinstance(item, str):
                all_urls.append(item)
            elif hasattr(item, "url"):
                all_urls.append(str(item.url))
            elif hasattr(item, "href"):
                all_urls.append(str(item.href))
            else:
                all_urls.append(str(item))

        if not all_urls:
            raise ValueError("Map returned no URLs")

        logger.info("Map found %d URLs", len(all_urls))
        
        # Save all discovered URLs to a file for inspection
        try:
            with open("map_debug.txt", "w", encoding="utf-8") as f:
                f.write(f"Total URLs discovered: {len(all_urls)}\n\n")
                for i, url in enumerate(all_urls, 1):
                    f.write(f"{i}. {url}\n")
            logger.info("Debug: saved map_debug.txt (%d URLs)", len(all_urls))
        except Exception as e:
            logger.warning("Could not save map debug file: %s", e)

        # Always include the homepage
        homepage = base_url.rstrip("/")
        if homepage not in [u.rstrip("/") for u in all_urls]:
            all_urls.insert(0, homepage)

        # Step 2: Filter and prioritize
        urls_to_scrape = _filter_and_prioritize(all_urls, base_url)
        if not urls_to_scrape:
            raise ValueError("No URLs remaining after filtering")

        # Step 3: Scrape each URL
        contents = []
        total = len(urls_to_scrape)
        for i, url in enumerate(urls_to_scrape, 1):
            try:
                logger.info("[%d/%d] Scraping: %s", i, total, url)
                cleaned = await scrape_url(url)
                if len(cleaned) > 100:
                    contents.append(cleaned)
            except ValueError as e:
                logger.warning("Skipping [%d/%d] %s: %s", i, total, url, e)

        if not contents:
            raise ValueError("No meaningful content after scraping all URLs")

        logger.info(
            "Map-first complete: %d/%d pages had content", len(contents), total
        )
        combined = "\n\n---\n\n".join(contents)
        _save_debug(combined)
        return combined

    except Exception as e:
        logger.warning("Map-first failed (%s) — trying crawl fallback", e)

        # ── Fallback 1: Firecrawl crawl ───────────────────────────────────
        try:
            result = await asyncio.to_thread(
                app.crawl,
                base_url,
                limit=50,
                scrape_options={
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                }
            )
            pages = result.data if result and result.data else []
            contents = []
            for page in pages:
                md = getattr(page, "markdown", None)
                if not md:
                    continue
                cleaned = _clean_markdown(md)
                if len(cleaned) > 100:
                    contents.append(cleaned)

            if not contents:
                raise ValueError("Crawl returned no content")

            logger.info("Crawl fallback: scraped %d pages", len(contents))
            combined = "\n\n---\n\n".join(contents)
            _save_debug(combined)
            return combined

        except Exception as e2:
            logger.warning("Crawl fallback failed (%s) — single scrape", e2)

            # ── Fallback 2: Single page ───────────────────────────────────
            content = await scrape_url(base_url)
            _save_debug(content)
            return content


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _save_debug(content: str) -> None:
    """Save full scraped content to a debug file for inspection."""
    try:
        with open("scrape_debug.txt", "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Debug file saved: scrape_debug.txt (%d chars)", len(content))
    except Exception as e:
        logger.warning("Could not save debug file: %s", e)


# ─────────────────────────────────────────────
# FILE EXTRACTORS
# ─────────────────────────────────────────────

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