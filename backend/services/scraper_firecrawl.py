import io
import re
import asyncio
import hashlib
import logging
from collections import defaultdict
from typing import List, Optional
from urllib.parse import urlparse
from firecrawl import FirecrawlApp

logger = logging.getLogger(__name__)

# Connect to your local Firecrawl instance
app = FirecrawlApp(api_key="test", api_url="http://localhost:3002")

# Maximum URLs to scrape per website
MAX_URLS = 200

# How many pages to scrape in parallel
CONCURRENCY = 8

# Minimum content length to keep a scraped page
MIN_CONTENT_LENGTH = 80

# ─────────────────────────────────────────────
# SITE TYPE DETECTION
# ─────────────────────────────────────────────

SHOPIFY_SIGNALS = [
    r"/collections/",
    r"/products/",
    r"cdn\.shopify\.com",
    r"myshopify\.com",
    r"shopify-section",
]
SHOPIFY_SIGNALS_COMPILED = [re.compile(p, re.IGNORECASE) for p in SHOPIFY_SIGNALS]


def _is_shopify_site(urls: List[str]) -> bool:
    """Detect Shopify by checking URL patterns in the first 100 discovered URLs."""
    shopify_count = sum(
        1 for url in urls[:100]
        if any(p.search(url) for p in SHOPIFY_SIGNALS_COMPILED)
    )
    return shopify_count >= 3


# ─────────────────────────────────────────────
# URL FILTERING
# ─────────────────────────────────────────────

SKIP_PATTERNS = [
    # Auth / account
    r"/login", r"/logout", r"/signin", r"/signup", r"/register",
    r"/account", r"/my-account", r"/profile", r"/password",
    # Cart / checkout / transactional
    r"/cart", r"/checkout", r"/order", r"/orders", r"/payment",
    r"/wishlist", r"/bag",
    # Static assets
    r"/cdn/", r"/assets/", r"/static/", r"/dist/", r"/_next/",
    r"\.jpg$", r"\.jpeg$", r"\.png$", r"\.gif$", r"\.webp$",
    r"\.svg$", r"\.ico$", r"\.css$", r"\.js$", r"\.woff",
    r"\.pdf$", r"\.zip$", r"\.xml$",
    # Search / filter / dynamic
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
    # Transactional confirmation pages
    r"/thank.you", r"/thankyou", r"/order-confirmed", r"/confirmation",
    # Tag / author archive pages
    r"/tag/", r"/tags/", r"/author/",
    # Pagination
    r"/page/\d+",
]

SKIP_COMPILED = [re.compile(p, re.IGNORECASE) for p in SKIP_PATTERNS]


def _should_skip(url: str) -> bool:
    return any(p.search(url) for p in SKIP_COMPILED)


# ─────────────────────────────────────────────
# GROUP CAPS
# ─────────────────────────────────────────────

# For Shopify: collections are JS-rendered grids — they return near-empty content.
# Skip them entirely and scrape individual product pages instead.
SHOPIFY_GROUP_CAPS = [
    (r"/pages/store-locator-", 0),
    (r"/store-locator-", 0),
    (r"/store-locator/", 0),
    (r"/collections/", 0),       # JS grids — no real text content
    (r"/products/", 80),         # Primary content source on Shopify
    (r"/blog/", 10),
    (r"/news/", 10),
    (r"/articles?/", 10),
    (r"/lookbook", 0),           # Image-only pages
]

# For generic sites: collections/categories may have real content.
GENERIC_GROUP_CAPS = [
    (r"/pages/store-locator-", 0),
    (r"/store-locator-", 0),
    (r"/store-locator/", 0),
    (r"/products/", 40),
    (r"/collections/", 15),
    (r"/categories?/", 15),
    (r"/blog/", 12),
    (r"/news/", 12),
    (r"/articles?/", 12),
    (r"/lookbook", 0),
]


def _apply_group_caps(urls: List[str], is_shopify: bool) -> List[str]:
    """
    Cap URLs per group. Runs AFTER priority sort so we keep the best ones first.
    """
    caps_raw = SHOPIFY_GROUP_CAPS if is_shopify else GENERIC_GROUP_CAPS
    group_caps = [(re.compile(p, re.IGNORECASE), cap) for p, cap in caps_raw]
    group_counts = defaultdict(int)
    result = []

    for url in urls:
        matched_group = None
        cap = None
        for pattern, group_cap in group_caps:
            if pattern.search(url):
                matched_group = pattern.pattern
                cap = group_cap
                break

        if matched_group is not None:
            if cap == 0:
                continue
            if group_counts[matched_group] < cap:
                group_counts[matched_group] += 1
                result.append(url)
        else:
            result.append(url)

    return result


# ─────────────────────────────────────────────
# URL PRIORITY SCORING
# ─────────────────────────────────────────────

PRIORITY_RULES = [
    # Tier 1 — Core informational pages (100)
    (100, [
        r"/(about|about-us|our-story|who-we-are|company|brand)/?$",
        r"/(contact|contact-us|get-in-touch|reach-us|contact-number)/?$",
        r"/(faq|faqs|frequently-asked|help|support)/?$",
        r"/(pricing|plans|packages|tariff)/?$",
        r"/(services|our-services|what-we-do|offerings)/?$",
        r"/(team|our-team|leadership|founders|staff)/?$",
        r"/(mission|vision|values|culture|mission-statement)/?$",
        r"/(membership|loyalty|rewards)/?$",
        r"/(size.?guide|size.?chart|men.size|women.size|kids.size)/?$",
    ]),
    # Tier 2 — Policies (80)
    (80, [
        r"/(privacy|privacy-policy|privacy-note|terms|terms-of-service|terms-and-conditions)/?$",
        r"/(return|refund|shipping|delivery|exchange)(-policy)?/?$",
        r"/(warranty|guarantee|cancellation|disclaimer|legal)/?$",
    ]),
    # Tier 3a — High-value /pages/ (70)
    (70, [
        r"/pages/(about|contact|faq|help|support|pricing|membership|size|shipping|return|refund|privacy|terms|warranty|media|press|stores)",
    ]),
    # Tier 3b — Shopify product pages (65) — primary content source
    (65, [
        r"/products/",
    ]),
    # Tier 3c — Collections / categories (55)
    (55, [
        r"/collections/",
        r"/categories?/",
        r"/shop/",
        r"/menu/",
        r"/portfolio/",
        r"/case-studies?/",
        r"/courses?/",
    ]),
    # Tier 4 — Generic /pages/ (45)
    (45, [
        r"/pages/",
        r"/services?/",
        r"/projects?/",
        r"/store/",
    ]),
    # Tier 5 — Blog / editorial (25)
    (25, [
        r"/blog/",
        r"/news/",
        r"/articles?/",
        r"/resources?/",
        r"/guides?/",
        r"/learn/",
        r"/academy/",
    ]),
]

PRIORITY_COMPILED = [
    (score, [re.compile(p, re.IGNORECASE) for p in patterns])
    for score, patterns in PRIORITY_RULES
]


def _priority_score(url: str) -> int:
    path = urlparse(url).path
    if path in ("", "/"):
        return 200
    for score, patterns in PRIORITY_COMPILED:
        if any(p.search(path) for p in patterns):
            return score
    return 10


def _normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if "#" in url:
        url = url[:url.index("#")]
    return url


def _filter_and_prioritize(urls: List[str], base_url: str, is_shopify: bool) -> List[str]:
    """
    1. Remove external domains
    2. Remove skip-listed URLs
    3. Deduplicate
    4. Sort by priority score
    5. Apply group caps (site-type aware)
    6. Cap at MAX_URLS
    """
    base_domain = urlparse(base_url).netloc
    seen = set()
    candidates = []

    for url in urls:
        url = _normalize_url(url)
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != base_domain:
            continue
        if _should_skip(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        candidates.append(url)

    candidates.sort(key=_priority_score, reverse=True)

    logger.info(
        "URL filtering: %d discovered → %d after dedup/skip (shopify=%s)",
        len(urls), len(candidates), is_shopify
    )

    candidates = _apply_group_caps(candidates, is_shopify)

    logger.info(
        "After group caps: %d URLs → capping at %d",
        len(candidates), MAX_URLS
    )

    return candidates[:MAX_URLS]


# ─────────────────────────────────────────────
# CONTENT CLEANING
# ─────────────────────────────────────────────

# Block-level noise: find start trigger, drop everything until end trigger (inclusive).
# Window: up to 80 lines forward.
BLOCK_NOISE_MARKERS = [
    ("Privacy Preference Center", "Reject All Confirm My Choices"),
    ("Manage Consent Preferences", "Reject All Confirm My Choices"),
    ("We use our own and third-party cookies", "Reject All Confirm My Choices"),
    ("Cookie Policy", "Cookie List"),
    ("Subscribe to our newsletter", "Subscribe"),
    ("Sign up for our newsletter", "Subscribe"),
    ("GDPR", "Confirm My Choices"),
]

LINE_DROP_PATTERNS = [
    # Broken/nested image markdown  e.g.  ![ ![(
    r"^\s*!?\[?\s*!?\[",
    # Modal close button
    r"^\s*x\s*$",
    # Standard image-only lines
    r"^\s*!\[.*?\]\(.*?\)\s*$",
    # Empty links
    r"^\s*\[\]\(.*?\)\s*$",
    # Shopify CDN / anchors
    r"#shopify-section-",
    r"cdn\.shopify\.com",
    # Cookie residue
    r"^\s*Cookie Policy\s*$",
    r"^\s*Cookies Details",
    r"^\s*Always Active\s*$",
    r"^\s*Consent Leg\.Interest\s*$",
    r"^\s*checkbox label label\s*$",
    r"^\s*(Allow All|Reject All|Confirm My Choices)\s*$",
    r"^\s*Apply\s*Cancel\s*$",
    r"^\s*Privacy Preference Center\s*$",
    # Navigation noise
    r"^\s*Skip to (content|main|navigation|nav)\s*$",
    r"^\s*(Woman|Man|Ethnic|Kids|Home_Beauty|Home\\?_Beauty)\s*$",
    r"^\s*India\s+Global\s*$",
    r"^\s*#### Location\s*$",
    # UI widget strings
    r"^\s*Added [Tt]o (Wishlist|Bag|Cart|Basket)\s*$",
    r"^\s*(ADD TO BAG|ADD TO CART|BUY NOW|ADD TO BASKET|SHOP NOW)\s*$",
    r"^\s*similar products\s*$",
    r"^\s*(Free shipping|Fresh Fashion)\s*$",
    r"^\s*Your wishlist has been temporarily saved.*$",
    r"^\s*Please (Log ?in|Login|Sign ?in).*wishlist.*$",
    r"^\s*Please (Login|Sign ?in)\s*$",
    r"^\s*/ Signup\s*$",
    r"^\s*Open media \d+ in modal\s*$",
    r"^\s*View full details\s*$",
    r"^\s*(Email|Facebook|Twitter|Pinterest|Instagram|Copy Link|WhatsApp|Share)\s*$",
    r"^\s*CHOOSE YOUR SHIPPING LOCATION\s*$",
    r"^\s*Remember Selection\s*$",
    r"^\s*(CONTINUE|APPLY|CANCEL|CLEAR)\s*$",
    r"^\s*Powered by\s*$",
    r"^\s*(Back|Search|Filter) (Button|Icon)\s*$",
    r"!\[share\]",
    r"data:image/",
    r"Choosing a selection results in a full page refresh",
    r"Opens in a new window",
    # Shopify product boilerplate
    r"^\s*Unit price\s*/\s*per\s*$",
    r"^\s*Sale\s+Sold out\s*$",
    r"^\s*MRP incl\.of all taxes\s*$",
    r"^\s*Regular price\s*$",
    r"^\s*Incl\. of all taxes\s*$",
    r"^\s*={10,}\s*$",
    r"^\s*-{10,}\s*$",
    # Lookbook / brand label boilerplate
    r"^\s*Lookbook\s+\w+\s*$",
    r"^\s*(Nuon M|Nuon W|WES|WL|SW LOV NUON)\s*$",
    r"^\s*Summer lookbook\s*$",
    r"^\s*Verify Email\s*$",
    # Size chart noise
    r"^\s*Measurements in:\s*(CM|INCHES|CM\s+INCHES)\s*$",
]

LINE_DROP_COMPILED = [re.compile(p, re.IGNORECASE) for p in LINE_DROP_PATTERNS]


def _remove_noise_blocks(text: str) -> str:
    """Remove entire multi-line noise blocks (cookie banners, consent dialogs)."""
    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        matched_block = False
        for start_marker, end_marker in BLOCK_NOISE_MARKERS:
            if start_marker.lower() in line.lower():
                for j in range(i, min(i + 80, len(lines))):
                    if end_marker.lower() in lines[j].lower():
                        i = j + 1
                        matched_block = True
                        break
                if not matched_block:
                    matched_block = True
                    i += 1
                break
        if not matched_block:
            result.append(line)
            i += 1
    return "\n".join(result)


def _clean_markdown(text: str) -> str:
    """
    Post-process scraped markdown to remove all noise before chunking.
    Universal — works for e-commerce, Shopify, SaaS, education, etc.
    """
    if not text:
        return ""

    text = _remove_noise_blocks(text)

    lines = text.splitlines()
    cleaned = [line for line in lines if not any(p.search(line) for p in LINE_DROP_COMPILED)]
    result = "\n".join(cleaned)

    # Convert [label](url) → label
    result = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", result)
    # Remove bare URLs
    result = re.sub(r"https?://\S+", "", result)
    # Collapse 3+ blank lines → 2
    result = re.sub(r"\n{3,}", "\n\n", result)
    # Drop lines that are now empty
    result = "\n".join(line for line in result.splitlines() if line.strip())

    return result.strip()


# ─────────────────────────────────────────────
# CONTENT DEDUPLICATION
# ─────────────────────────────────────────────

def _content_fingerprint(text: str) -> str:
    """Hash first ~600 chars to detect template pages with identical structure."""
    normalized = re.sub(r"\s+", " ", text[:600].lower().strip())
    return hashlib.md5(normalized.encode()).hexdigest()


def _deduplicate_content(contents: List[str]) -> List[str]:
    seen = set()
    unique = []
    for content in contents:
        fp = _content_fingerprint(content)
        if fp not in seen:
            seen.add(fp)
            unique.append(content)
        else:
            logger.info("Skipping duplicate content page")
    return unique


# ─────────────────────────────────────────────
# CORE SCRAPING
# ─────────────────────────────────────────────

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


async def _scrape_with_semaphore(
    semaphore: asyncio.Semaphore,
    url: str,
    index: int,
    total: int
) -> Optional[str]:
    async with semaphore:
        try:
            logger.info("[%d/%d] Scraping: %s", index, total, url)
            content = await scrape_url(url)
            if len(content) >= MIN_CONTENT_LENGTH:
                return content
            logger.warning(
                "[%d/%d] Too short (%d chars), skipping: %s",
                index, total, len(content), url
            )
            return None
        except ValueError as e:
            logger.warning("[%d/%d] Failed: %s → %s", index, total, url, e)
            return None


async def _scrape_concurrent(urls: List[str], concurrency: int = CONCURRENCY) -> List[str]:
    """Scrape a list of URLs concurrently, return non-empty results."""
    semaphore = asyncio.Semaphore(concurrency)
    total = len(urls)
    tasks = [
        _scrape_with_semaphore(semaphore, url, i + 1, total)
        for i, url in enumerate(urls)
    ]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


async def scrape_multiple_urls(urls: List[str]) -> str:
    """Public helper — scrape multiple URLs (used by train_router for file/faq flows)."""
    contents = await _scrape_concurrent(urls)
    unique = _deduplicate_content(contents)
    return "\n\n---\n\n".join(unique)


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

async def scrape_website(base_url: str) -> str:
    """
    Main entry point.

    Flow A — Specific deep page (2+ path segments): scrape directly.

    Flow B — Homepage or shallow URL (full site):
      1. Map → discover all URLs
      2. Detect site type (Shopify vs generic)
         - Shopify: skip /collections/ (JS grids), focus on /products/ (up to 80)
         - Generic: include /collections/ and /products/ with balanced caps
      3. Filter + prioritize + group-cap
      4. Scrape concurrently (CONCURRENCY parallel requests)
      5. Deduplicate by content fingerprint
      Fallback 1: Firecrawl crawl (if Map fails)
      Fallback 2: Single page scrape (if crawl also fails)
    """
    parsed = urlparse(base_url)
    path_parts = [p for p in parsed.path.split("/") if p]

    # ── Flow A: Single specific page ─────────────────────────────────────
    if len(path_parts) >= 2:
        logger.info("Specific page — scraping directly: %s", base_url)
        content = await scrape_url(base_url)
        _save_debug(content)
        return content

    # ── Flow B: Full website ──────────────────────────────────────────────
    logger.info("Full site scrape starting for: %s", base_url)

    try:
        # Step 1: Discover URLs
        logger.info("Running Map on %s ...", base_url)
        map_result = await asyncio.to_thread(app.map, base_url)

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
        _save_map_debug(all_urls)

        # Always include homepage
        homepage = base_url.rstrip("/")
        if homepage not in [u.rstrip("/") for u in all_urls]:
            all_urls.insert(0, homepage)

        # Step 2: Detect site type
        is_shopify = _is_shopify_site(all_urls)
        logger.info("Site type: %s", "Shopify" if is_shopify else "Generic")

        # Step 3: Filter, prioritize, group-cap
        urls_to_scrape = _filter_and_prioritize(all_urls, base_url, is_shopify)
        if not urls_to_scrape:
            raise ValueError("No URLs remaining after filtering")

        logger.info(
            "Scraping %d URLs (concurrency=%d, type=%s)",
            len(urls_to_scrape), CONCURRENCY,
            "Shopify" if is_shopify else "Generic"
        )

        # Step 4: Concurrent scrape
        contents = await _scrape_concurrent(urls_to_scrape, CONCURRENCY)

        # Step 5: Deduplicate
        unique_contents = _deduplicate_content(contents)

        if not unique_contents:
            raise ValueError("No meaningful content after scraping")

        logger.info(
            "Done: %d unique pages / %d scraped (%.0f%% yield)",
            len(unique_contents), len(urls_to_scrape),
            100 * len(unique_contents) / max(len(urls_to_scrape), 1)
        )

        combined = "\n\n---\n\n".join(unique_contents)
        _save_debug(combined)
        return combined

    except Exception as e:
        logger.warning("Map-first failed (%s) — trying crawl fallback", e)

        # ── Fallback 1: Crawl ─────────────────────────────────────────────
        try:
            result = await asyncio.to_thread(
                app.crawl,
                base_url,
                limit=50,
                scrape_options={"formats": ["markdown"], "onlyMainContent": True}
            )
            pages = result.data if result and result.data else []
            contents = []
            seen_fps = set()
            for page in pages:
                md = getattr(page, "markdown", None)
                if not md:
                    continue
                cleaned = _clean_markdown(md)
                if len(cleaned) < MIN_CONTENT_LENGTH:
                    continue
                fp = _content_fingerprint(cleaned)
                if fp in seen_fps:
                    continue
                seen_fps.add(fp)
                contents.append(cleaned)

            if not contents:
                raise ValueError("Crawl returned no content")

            logger.info("Crawl fallback: %d unique pages", len(contents))
            combined = "\n\n---\n\n".join(contents)
            _save_debug(combined)
            return combined

        except Exception as e2:
            logger.warning("Crawl fallback failed (%s) — single page scrape", e2)
            content = await scrape_url(base_url)
            _save_debug(content)
            return content


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _save_debug(content: str) -> None:
    try:
        with open("scrape_debug.txt", "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("scrape_debug.txt saved (%d chars)", len(content))
    except Exception as e:
        logger.warning("Could not save scrape_debug.txt: %s", e)


def _save_map_debug(urls: List[str]) -> None:
    try:
        with open("map_debug.txt", "w", encoding="utf-8") as f:
            f.write(f"Total URLs discovered: {len(urls)}\n\n")
            for i, url in enumerate(urls, 1):
                f.write(f"{i}. {url}\n")
        logger.info("map_debug.txt saved (%d URLs)", len(urls))
    except Exception as e:
        logger.warning("Could not save map_debug.txt: %s", e)


# ─────────────────────────────────────────────
# FILE EXTRACTORS
# ─────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    import fitz
    text_pages = []
    with fitz.open(stream=file_bytes, filetype="pdf") as doc:
        for page in doc:
            text_pages.append(page.get_text())
    return "\n".join(text_pages)


def extract_text_from_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def extract_text_from_faq(faqs: List[dict]) -> str:
    entries = []
    for item in faqs:
        question = item.get("question", "").strip()
        answer = item.get("answer", "").strip()
        entries.append(f"Q: {question}\nA: {answer}")
    return "\n\n".join(entries)