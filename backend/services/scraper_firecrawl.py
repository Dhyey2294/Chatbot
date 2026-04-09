import io
import re
import asyncio
import hashlib
import logging
from collections import defaultdict, Counter
from typing import Callable, List, Optional
from urllib.parse import urlparse
from firecrawl import FirecrawlApp

from services.image_extractor import extract_images, _tokenize

logger = logging.getLogger(__name__)


# IMAGE MATCHING

# Minimum token-overlap score to count a key as matched in Pass 2 / Pass 3
_MATCH_MIN_SCORE = 2

# Maximum images to attach to a single chunk
_MAX_IMAGES_PER_CHUNK = 4


def _match_images_to_chunk(
    chunk_text: str,
    image_map: dict,
    keyword_index: dict,
) -> list:
    """
    Match images from the image_map to a chunk of text using 3 passes.

    Pass 1 — Direct: image map key (lowercased) is a substring of chunk text.
    Pass 2 — Token overlap: tokenize chunk; score each key by matching tokens.
             Return keys with score >= _MATCH_MIN_SCORE.
    Pass 3 — Keyword index fallback: look up chunk tokens in the prebuilt
             keyword_index (tokens that appear in 3+ keys) and score candidates.

    Returns a deduplicated list of image URLs, capped at _MAX_IMAGES_PER_CHUNK.
    Returns [] if no pass matches.
    """
    if not image_map:
        return []

    chunk_lower = chunk_text.lower()

    # ── Pass 1: Direct substring match ──────────────────────────────────────
    direct_hits = [
        key for key in image_map
        if key.lower() in chunk_lower
    ]
    if direct_hits:
        result = _merge_images(image_map, direct_hits)
        logger.debug(
            "Image match Pass 1 (direct): %d keys matched, %d images",
            len(direct_hits), len(result)
        )
        return result

    # ── Pass 2: Token overlap ────────────────────────────────────────────────
    chunk_tokens = set(_tokenize(chunk_text))
    if chunk_tokens:
        scores: dict = defaultdict(int)
        for key in image_map:
            key_text = key.lower()
            for token in chunk_tokens:
                if token in key_text:
                    scores[key] += 1

        qualified = [key for key, score in scores.items() if score >= 3]
        if qualified:
            result = _merge_images(image_map, qualified)
            logger.debug(
                "Image match Pass 2 (token overlap): %d keys matched, %d images",
                len(qualified), len(result)
            )
            return result

    # ── Pass 3: Keyword index fallback ───────────────────────────────────────
    if keyword_index and chunk_tokens:
        candidate_scores: dict = defaultdict(int)
        for token in chunk_tokens:
            for candidate_key in keyword_index.get(token, []):
                candidate_scores[candidate_key] += 1

        qualified = [
            key for key, score in candidate_scores.items()
            if score >= 3
        ]
        if qualified:
            result = _merge_images(image_map, qualified)
            logger.debug(
                "Image match Pass 3 (keyword index): %d keys matched, %d images",
                len(qualified), len(result)
            )
            return result

    logger.debug("Image match: no pass matched for this chunk")
    return []


def _merge_images(image_map: dict, keys: list) -> list:
    """Merge image URLs from the given keys, deduplicate, and cap at _MAX_IMAGES_PER_CHUNK."""
    seen = set()
    result = []
    for key in keys:
        for url in image_map.get(key, []):
            if url not in seen:
                seen.add(url)
                result.append(url)
                if len(result) >= _MAX_IMAGES_PER_CHUNK:
                    return result
    return result

# Progress callback type: (percent: int, message: str, **extras) -> None
ProgressCallback = Optional[Callable[..., None]]

# Connect to your local Firecrawl instance
app = FirecrawlApp(api_key="test", api_url="http://localhost:3002")

MAX_URLS_BY_TYPE = {
    "shopify":    50,
    "ecommerce":  200,
    "service":    200,
    "restaurant": 100,
    "realestate": 150,
    "education":  100,
}
MAX_URLS_DEFAULT = 200

# How many pages to scrape in parallel
CONCURRENCY = 8

# Minimum content length to keep a scraped page
MIN_CONTENT_LENGTH = 80

# Boilerplate threshold: lines appearing in this fraction of pages are site-wide noise
BOILERPLATE_THRESHOLD = 0.25

# Minimum pages needed before boilerplate detection kicks in
BOILERPLATE_MIN_PAGES = 10

# Max path depth for deep-leaf URL capping (4+ segments = likely thin sub-page)
MAX_DEPTH_CAP = 3


# SITE TYPE DETECTION

SHOPIFY_SIGNALS = [
    r"/collections/",
    r"/products/",
    r"cdn\.shopify\.com",
    r"myshopify\.com",
    r"shopify-section",
]
SHOPIFY_SIGNALS_COMPILED = [re.compile(p, re.IGNORECASE) for p in SHOPIFY_SIGNALS]


def _is_shopify_site(urls: List[str]) -> bool:
    """Detect Shopify by checking URL patterns across all discovered URLs."""
    shopify_count = sum(
        1 for url in urls
        if any(p.search(url) for p in SHOPIFY_SIGNALS_COMPILED)
    )
    return shopify_count >= 3


# URL FILTERING

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
    # Transactional / user-specific
    r"/invoice/",
    r"/print/",
    r"/share/",
    r"/unsubscribe",
    r"/dashboard",
    r"/compare",
    r"/shortlist",
    r"/saved",
    # Query string noise
    r"\?minprice=",
    r"\?maxprice=",
    r"\?coupon=",
    r"\?token=",
    r"\?reset=",
    r"\?covers=",
    r"\?party=",
    r"\?table=",
    r"\?date=",
    r"\?module=",
    r"\?lesson=",
    # City-specific store locator flood (generic pattern)
    r"/store-locator-[a-z]",
    r"/pages/store-locator-[a-z]",
]

SKIP_COMPILED = [re.compile(p, re.IGNORECASE) for p in SKIP_PATTERNS]


def _should_skip(url: str) -> bool:
    return any(p.search(url) for p in SKIP_COMPILED)


def _url_depth(url: str) -> int:
    """Count meaningful path segments in a URL."""
    path = urlparse(url).path
    return len([p for p in path.split("/") if p])


def _detect_site_type(urls: List[str]) -> str:
    """Detect site type from discovered URLs.
    Returns one of: shopify, ecommerce, service, restaurant, realestate, education.
    """
    url_str = " ".join(urls).lower()

    # Shopify check first — most specific
    if _is_shopify_site(urls):
        return "shopify"

    # E-commerce signals
    if any(x in url_str for x in ["/product/", "/products/", "/shop/", "/wc-", "/item/", "/p/"]):
        return "ecommerce"

    # Restaurant signals
    if any(x in url_str for x in ["/menu/", "/food/", "/drinks/", "/reservation", "/book-a-table"]):
        return "restaurant"

    # Real estate signals
    if any(x in url_str for x in ["/property/", "/properties/", "/listing/", "/listings/", "/mls", "/projects/"]):
        return "realestate"

    # Education signals
    if any(x in url_str for x in ["/courses/", "/course/", "/curriculum/", "/lesson/", "/programs/", "/workshop/"]):
        return "education"

    # Default: service/agency/saas
    return "service"


# GROUP CAPS — per site type

SITE_CONFIGS = {
    "shopify": {
        "group_caps": [
            (r"/pages/store-locator-",  0),   # city variant flood — hard skip
            (r"/store-locator-",        0),
            (r"/store-locator/",        0),
            (r"/collections/",          0),   # JS grids — no real text content
            (r"/products/",             0),   # handled via /products.json feed
            (r"/lookbook",              0),   # image-only pages
            (r"/blog/",                 5),   # reduced — context only, not primary source
            (r"/news/",                 5),
            (r"/articles?/",            5),
            (r"/pages/",               20),   # about, FAQ, shipping, size charts etc
            (r"/policies/",             5),   # refund, privacy, terms, shipping
        ],
    },
    "ecommerce": {
        "group_caps": [
            (r"/pages/store-locator-",  0),
            (r"/store-locator-",        0),
            (r"/store-locator/",        0),
            (r"/product/",             80),
            (r"/products/",            80),
            (r"/p/",                   80),
            (r"/item/",                80),
            (r"/category/",            30),
            (r"/categories?/",         30),
            (r"/shop/",                20),
            (r"/collection/",          20),
            (r"/blog/",                 8),
            (r"/news/",                 8),
            (r"/articles?/",            8),
            (r"/lookbook",              0),
        ],
    },
    "service": {
        "group_caps": [
            # No cap (-1 sentinel) on service/solution pages — scrape all
            (r"/services?/",           -1),
            (r"/solutions?/",          -1),
            (r"/what-we-do/",          -1),
            (r"/offerings?/",          -1),
            (r"/capabilities?/",       -1),
            (r"/features?/",           -1),
            (r"/case-studies?/",       20),
            (r"/portfolio/",           20),
            (r"/work/",                20),
            (r"/projects?/",           20),
            (r"/team/",                15),
            (r"/blog/",                15),
            (r"/resources?/",          15),
            (r"/docs/",                20),
            (r"/careers?/",             0),
            (r"/jobs/",                 0),
        ],
    },
    "restaurant": {
        "group_caps": [
            (r"/menu/",                30),
            (r"/food/",                20),
            (r"/drinks?/",             10),
            (r"/order/",                8),
            (r"/catering/?",            8),
            (r"/events?/",             10),
            (r"/locations?/",          10),
            (r"/blog/",                 5),
            (r"/careers?/",             0),
            (r"/jobs/",                 0),
        ],
    },
    "realestate": {
        "group_caps": [
            (r"/property/",            70),
            (r"/properties/",          70),
            (r"/listing/",             70),
            (r"/listings/",            70),
            (r"/projects?/",           25),
            (r"/location/",            15),
            (r"/area/",                15),
            (r"/neighborhood/",        10),
            (r"/agents?/",             10),
            (r"/blog/",                 8),
            (r"/careers?/",             0),
            (r"/jobs/",                 0),
            (r"/saved/",                0),
            (r"/shortlist/",            0),
            (r"/compare/",              0),
        ],
    },
    "education": {
        "group_caps": [
            # No cap on course/program pages — scrape all
            (r"/courses?/",            -1),
            (r"/programs?/",           -1),
            (r"/workshops?/",          -1),
            (r"/curriculum/",          15),
            (r"/instructors?/",        10),
            (r"/faculty/",             10),
            (r"/testimonials?/",        8),
            (r"/success-stories?/",     8),
            (r"/resources?/",          10),
            (r"/blog/",                 8),
            (r"/careers?/",             0),
            (r"/jobs/",                 0),
            (r"/dashboard",             0),
            (r"/certificate/",          0),
        ],
    },
}


def _apply_group_caps(urls: List[str], site_type: str) -> List[str]:
    """
    Cap URLs per group. Runs on non-guaranteed URLs only.
    -1 cap = no limit (always include). 0 cap = hard skip.
    Also enforces a global depth cap on ungrouped URLs.
    """
    config = SITE_CONFIGS.get(site_type, SITE_CONFIGS["service"])
    caps_raw = config["group_caps"]
    group_caps = [(re.compile(p, re.IGNORECASE), cap) for p, cap in caps_raw]
    group_counts = defaultdict(int)
    deep_page_count = 0
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
                continue          # hard skip
            if cap == -1:
                result.append(url)  # no cap — always include
                continue
            if group_counts[matched_group] < cap:
                group_counts[matched_group] += 1
                result.append(url)
            continue

        # Ungrouped URLs: apply depth cap to prevent thin leaf pages flooding
        if _url_depth(url) >= 4:
            if deep_page_count < MAX_DEPTH_CAP * 10:
                deep_page_count += 1
                result.append(url)
        else:
            result.append(url)

    return result


# URL PRIORITY SCORING

PRIORITY_RULES = [
    # Tier 0 — Always-first guaranteed pages (150)
    (150, [
        r"/(faq|faqs|frequently-asked-questions)/?$",
        r"/(faq|faqs)/",
        r"/(help|support)/?$",
        r"/(pricing|plans|packages|tariff)/?$",
        r"/(about|about-us|our-story|who-we-are|company|brand)/?$",
        r"/(contact|contact-us|get-in-touch|reach-us|contact-number)/?$",
        r"/(shipping|delivery)(-policy)?/?$",
        r"/(returns?|refund|exchange)(-policy)?/?$",
        r"/(privacy|privacy-policy|privacy-note)/?$",
        r"/(terms|terms-of-service|terms-and-conditions)/?$",
        r"/(warranty|guarantee|cancellation)/?$",
        r"/(size.?guide|size.?chart|men.?size|women.?size|kids.?size)/?$",
        r"/(membership|loyalty|rewards)/?$",
        r"/pages/(faq|faqs|help|support|pricing|about|contact|shipping|delivery|returns?|refund|exchange|privacy|terms|warranty|size|membership)",
        r"/(policies)/(refund|privacy|terms|shipping)",
    ]),
    # Tier 1 — Core service/product pages (120)
    (120, [
        r"/(services?|our-services|what-we-do|offerings|capabilities)/?$",
        r"/services?/",
        r"/solutions?/",
        r"/(features?|how-it-works|why-us)/?$",
        r"/features?/",
        r"/(menu|our-menu)/?$",
        r"/menu/",
        r"/(courses?|programs?|workshops?)/?$",
        r"/courses?/",
        r"/programs?/",
        r"/workshops?/",
        r"/(mission|vision|values|culture)/?$",
        r"/(team|our-team|leadership|founders|staff)/?$",
        r"/team/",
        r"/(schedulecall|book|book-a-call|consultation|get-started)/?$",
    ]),
    # Tier 2 — Listing and category pages (90)
    (90, [
        r"/collections/",
        r"/categories?/",
        r"/category/",
        r"/shop/?$",
        r"/shop/",
        r"/(portfolio|case-studies?|work|projects?)/?$",
        r"/portfolio/",
        r"/case-studies?/",
        r"/work/",
        r"/projects?/",
        r"/(instructors?|faculty|coaches?)/?$",
        r"/instructors?/",
        r"/(locations?|our-locations?|stores?)/?$",
        r"/locations?/",
        r"/(catering|events?)/?$",
        r"/catering/",
        r"/events?/",
        r"/(testimonials?|success-stories?|reviews?)/?$",
        r"/testimonials?/",
        r"/(clients?|partners?)/?$",
    ]),
    # Tier 3 — Product and listing detail pages (70)
    (70, [
        r"/products?/",
        r"/product/",
        r"/items?/",
        r"/p/",
        r"/(property|properties|listing|listings)/",
        r"/pages/",
        r"/services?/[^/]+",     # deep service sub-pages
        r"/(docs|documentation|help)/",
        r"/resources?/",
        r"/(allergens|nutrition|ingredients)/?$",
        r"/(emi-calculator|loan|finance)/?$",
    ]),
    # Tier 4 — Blog / editorial (30)
    (30, [
        r"/blog/",
        r"/news/",
        r"/articles?/",
        r"/guides?/",
        r"/learn/",
        r"/academy/",
        r"/insights?/",
        r"/(press|media-center|newsroom)/?$",
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


def _filter_and_prioritize(urls: List[str], base_url: str, site_type: str) -> List[str]:
    """
    1. Remove external domains
    2. Remove skip-listed URLs
    3. Deduplicate
    4. Always-include guaranteed pages (faq, about, contact, pricing, policies etc.)
    5. Sort remainder by priority score
    6. Apply group caps and depth caps (site-type aware)
    7. Cap at per-site-type MAX_URLS
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

    # Split into guaranteed (score >= 150) and normal
    guaranteed = [u for u in candidates if _priority_score(u) >= 150]
    normal = [u for u in candidates if _priority_score(u) < 150]
    normal.sort(key=_priority_score, reverse=True)

    max_urls = MAX_URLS_BY_TYPE.get(site_type, MAX_URLS_DEFAULT)

    logger.info(
        "URL filtering: %d discovered → %d after dedup/skip (site_type=%s, guaranteed=%d, max=%d)",
        len(urls), len(candidates), site_type, len(guaranteed), max_urls
    )

    # Apply group caps only to non-guaranteed URLs
    capped_normal = _apply_group_caps(normal, site_type)
    final = guaranteed + capped_normal

    logger.info(
        "After group caps: %d URLs → capping at %d",
        len(final), max_urls
    )

    return final[:max_urls]


# CONTENT CLEANING

# Block-level noise: find start trigger, drop everything until end trigger (inclusive).
# Window: up to 80 lines forward.
# These are structural patterns, not website-specific strings.
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
    # Broken / image-only markdown
    r"^\s*!?\[?\s*!?\[",                        # Broken/nested image markdown e.g. ![ ![(
    r"^\s*!\[.*?\]\(.*?\)\s*$",                 # Standard image-only lines
    r"^\s*\[\]\(.*?\)\s*$",                     # Empty links
    r"!\[share\]",                               # Share icon markdown
    r"data:image/",                              # Base64 embedded images

    # ── Modal / close buttons ──────────────────────────────────────────────
    r"^\s*x\s*$",                               # Modal close button (single x)

    # ── CDN / technical artifacts ──────────────────────────────────────────
    r"#shopify-section-",                        # Shopify section anchors
    r"cdn\.shopify\.com",                        # Shopify CDN links

    # ── Cookie / GDPR residue (generic) ───────────────────────────────────
    r"^\s*Cookie(s)? (Policy|Details|Settings|Preferences|Notice|Banner)\s*$",
    r"^\s*Cookies Details",
    r"^\s*Always Active\s*$",
    r"^\s*Consent Leg\.Interest\s*$",
    r"^\s*checkbox label label\s*$",
    r"^\s*(Allow All|Reject All|Confirm My Choices|Accept All Cookies)\s*$",
    r"^\s*Apply\s*Cancel\s*$",
    r"^\s*Privacy Preference Center\s*$",
    r"^\s*(Accept|Decline|Accept All|Reject All|Manage Cookies?)\s*$",
    r"^\s*By clicking.{0,60}(cookies|consent|accept)",  # "By clicking Accept, you consent..."

    # ── Generic navigation noise ───────────────────────────────────────────
    r"^\s*Skip to (content|main|navigation|nav|footer)\s*$",
    r"^\s*#### Location\s*$",
    r"Opens in a new window",
    r"Choosing a selection results in a full page refresh",

    # ── Generic UI / CTA boilerplate ──────────────────────────────────────
    # These match patterns across all site types — not hardcoded to any brand
    r"^\s*Open media \d+ in modal\s*$",
    r"^\s*View full details\s*$",
    r"^\s*(Email|Facebook|Twitter|Pinterest|Instagram|LinkedIn|YouTube|TikTok|Copy Link|WhatsApp|Share)\s*$",
    r"^\s*(CONTINUE|APPLY|CANCEL|CLEAR|RESET|SUBMIT)\s*$",
    r"^\s*Powered by\s*$",
    r"^\s*(Back|Search|Filter|Sort|Menu|Close|Open) (Button|Icon|Toggle)\s*$",
    r"^\s*Your browser does not support the video tag\.?\s*$",  # HTML5 video fallback (any site)

    # ── Auth/CTA button lines (generic pattern — label!BrandName or label! alone) ──
    # Matches things like "Login!user", "Start Free Trial!BrandName", "Sign Up!logo"
    r"^\s*(Login|Sign ?[Ii]n|Sign ?[Uu]p|Register|Log [Ii]n)![A-Za-z]",
    r"^\s*(Start Free Trial|Get Started|Try for Free|Start for Free)(![\w].*)?$",

    # ── Generic footer / copyright lines ──────────────────────────────────
    r"^\s*Copyright\s*©",
    r"^\s*©\s*20\d\d",
    r"^\s*All rights reserved\.?\s*$",

    # ── Generic CTA blocks that appear on every page ───────────────────────
    r"^\s*Book (Now|a Call|a Demo|a Meeting|Free Call)\s*[!\-]?\s*$",
    r"^\s*-{3,}\s*$",                           # Horizontal rules used as dividers (--- etc)

    # ── Generic wishlist / social auth noise ──────────────────────────────
    r"^\s*Added [Tt]o (Wishlist|Bag|Cart|Basket)\s*$",
    r"^\s*Your wishlist has been temporarily saved.*$",
    r"^\s*Please (Log ?in|Login|Sign ?in).*wishlist.*$",
    r"^\s*Please (Login|Sign ?in)\s*$",
    r"^\s*/ Signup\s*$",

    # ── E-commerce product boilerplate (generic — not Shopify-specific) ───
    r"^\s*(ADD TO BAG|ADD TO CART|BUY NOW|ADD TO BASKET|SHOP NOW|ADD TO WISHLIST)\s*$",
    r"^\s*similar products\s*$",
    r"^\s*Unit price\s*/\s*per\s*$",
    r"^\s*Sale\s+Sold out\s*$",
    r"^\s*Regular price\s*$",
    r"^\s*(Free shipping|Free Delivery|Free Returns)\s*$",
    r"^\s*(Incl\.|Including|Excl\.|Excluding).{0,30}(tax|taxes|VAT|GST)\s*$",  # Any tax line
    r"^\s*MRP incl\.of all taxes\s*$",

    # ── Separator noise ────────────────────────────────────────────────────
    r"^\s*={10,}\s*$",
    r"^\s*-{10,}\s*$",
    r"^\s*\*{10,}\s*$",

    # ── Size chart noise (e-commerce) ─────────────────────────────────────
    r"^\s*Measurements in:\s*(CM|INCHES|CM\s+INCHES)\s*$",

    # ── Verify Email / account actions ────────────────────────────────────
    r"^\s*Verify Email\s*$",

    # ── Generic newsletter forms ───────────────────────────────────────────
    r"^\s*(Subscribe|Unsubscribe)\s*$",
    r"^\s*Enter your email.*$",
    r"^\s*Get \d+% off.*subscribe.*$",          # "Get 10% off when you subscribe"

    # ── Phone country selector (contact forms) ─────────────────────────────
    # The giant country dropdown list that leaks into markdown on contact pages
    r"^\s*International\s*$",
    r"^\s*(Afghanistan|Albania|Algeria|Andorra|Angola)\s*$",
    r"^\s*\\\s*$",
    r"^\s*\\\-+\\\s*$",
    r"^\s*\*\*\s*$",
    r"^\s*\]\(\s*$",
    r".*\]\(\s*$",
    r"^\s*!\s*$",
    r"^\s*\(\d+\)\s*$",
    r"^\s*\d+-Day (Delivery|Turnaround)\s*",
    r"^\s*\d+% Repeat Buyers\s*$",
    r"^\s*\d+min Response Time\s*$",
    r"^\s*\d+ orders? past \d+ hours?\s*$",
    r"^\s*\d+-Day Money-Back Guarantee\s*$",
    r"^\s*Show more Reviews\s*$",
    r"^\s*Related Service\s*$",
    r"^\s*Message \w+\s*$",
    r"^\s*Rating & Reviews\s*$",
    r"\bCheck Icon",
    r"^\s*\d \!\[\]\(",
    r"^\s*(Communication|Value for money|Quality|Delivery|Recommend)\s*$",
    r"^\s*Primary (typeface|Color|Colour)\s*$",
    r"^\s*Secondary (typeface|Color|Colour)\s*$",
    r"^\s*^\d{3}$",
    r"^\s*0\d\d\s*$",
    r"^\s*Platform\s*$",
    r"^\s*What we did\s*$",
    r"^\s*Key Market\s*$",
    r"^\s*Project (Focus|Completion|Type)\s*$",
    r"^\s*Tools we used\s*$",
    r"^\s*Brand Assets\s*$",
    r"^\s*/[A-Za-z& ]+$",
    r"^\s*\(\d+\)\]\(\s*$",
    r"^\s*\(\d+\)\]\(.*$",
    r"^\s*/[A-Za-z0-9&,. /-]{1,60}\s*$",
    r"^\s*### What's Included\s*$",
    r"^\s*About this design\s*$",
    r"^\s*### Why \w[\w ]{0,30}\?\s*$",
    r"^\s*### Let.s connect\s*$",
    r"^\s*### \d+ Reviews\s*$",
    r"^\s*\d+ Reviews\s*$",
    r"^\s*\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec),? \d{4}\s*$",
    r"^\s*[1-5]\.[0-9]\s*$",
    r"^\s*Design\s*$",
    r"^\s*Industry\s*$",
    r"^\s*From \$[\d,]+\s*$",
    r"^\s*\d{2,3} Reviews\s*$",
    r"^\s*\d+-Day Money-Back Guarantee\s*$",
    r"^\s*### Related Blog\s*$",
    r"^\s*### Popular Services\s*$",
    r"^\s*More Case Studies\s*$",
    r"^\s*Share this article\s*$",
    r"^\s*Quick View!arrow\s*$",
    r"^\s*Case Study !arrow\s*$",
    r"^\s*[⭐★]{3,}\s*$",
    r"^\s*[\d.]+\(\d+ Reviews?\).*$",
    r"^\s*20\d\d\s*$",
    r"^\s*### ROI\s*$",
    r"^\s*### Overview\s*$",
    r"^\s*Research\s*$",
    r"^\s*(UI Design|UX Design|Website Design)\s*$",
    r"^\s*(Email Marketing Automation Services|Social Media Automation Service|Make \(Integromat\) Automation)\s*",
    r"^\s*/\s?[A-Za-z0-9&,. -]{1,60}\s*$",
]

LINE_DROP_COMPILED = [re.compile(p, re.IGNORECASE) for p in LINE_DROP_PATTERNS]

# Country list for contact form dropdown noise (appears as a giant list in scraped markdown)
# We remove lines that are ONLY a country name (i.e., leaked from a <select> element)
_COUNTRIES = {
    "afghanistan", "albania", "algeria", "andorra", "angola", "argentina", "armenia",
    "australia", "austria", "azerbaijan", "bahamas", "bahrain", "bangladesh", "barbados",
    "belarus", "belgium", "belize", "benin", "bhutan", "bolivia", "botswana", "brazil",
    "brunei", "bulgaria", "burkina faso", "burundi", "cambodia", "cameroon", "canada",
    "chad", "chile", "china", "colombia", "comoros", "congo", "costa rica", "croatia",
    "cuba", "cyprus", "czech republic", "denmark", "djibouti", "dominica", "ecuador",
    "egypt", "el salvador", "eritrea", "estonia", "ethiopia", "fiji", "finland", "france",
    "gabon", "gambia", "georgia", "germany", "ghana", "greece", "grenada", "guatemala",
    "guinea", "guyana", "haiti", "honduras", "hungary", "iceland", "india", "indonesia",
    "iran", "iraq", "ireland", "israel", "italy", "jamaica", "japan", "jordan",
    "kazakhstan", "kenya", "kiribati", "kuwait", "kyrgyzstan", "laos", "latvia",
    "lebanon", "lesotho", "liberia", "libya", "liechtenstein", "lithuania", "luxembourg",
    "madagascar", "malawi", "malaysia", "maldives", "mali", "malta", "mauritania",
    "mauritius", "mexico", "moldova", "monaco", "mongolia", "montenegro", "morocco",
    "mozambique", "myanmar", "namibia", "nauru", "nepal", "netherlands", "new zealand",
    "nicaragua", "niger", "nigeria", "norway", "oman", "pakistan", "palau", "panama",
    "paraguay", "peru", "philippines", "poland", "portugal", "qatar", "romania", "russia",
    "rwanda", "samoa", "san marino", "saudi arabia", "senegal", "serbia", "seychelles",
    "sierra leone", "singapore", "slovakia", "slovenia", "somalia", "south africa",
    "south korea", "south sudan", "spain", "sri lanka", "sudan", "suriname", "sweden",
    "switzerland", "syria", "taiwan", "tajikistan", "tanzania", "thailand", "togo",
    "tonga", "trinidad and tobago", "tunisia", "turkey", "turkmenistan", "tuvalu",
    "uganda", "ukraine", "united arab emirates", "united kingdom", "united states",
    "uruguay", "uzbekistan", "vanuatu", "venezuela", "vietnam", "yemen", "zambia",
    "zimbabwe", "kosovo", "palestine", "north korea", "north macedonia",
}


def _is_country_line(line: str) -> bool:
    """Return True if the line contains only a country name (contact form dropdown leak)."""
    stripped = line.strip().lower()
    return stripped in _COUNTRIES


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


def _remove_country_dropdown_blocks(text: str) -> str:
    """
    Remove runs of country names that leak from contact form <select> dropdowns.
    If 3+ consecutive lines are country names, drop the entire run.
    """
    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        # Check if current line is a country name
        if _is_country_line(lines[i]):
            # Look ahead to find the full run
            run_end = i
            while run_end < len(lines) and _is_country_line(lines[run_end]):
                run_end += 1
            run_length = run_end - i
            if run_length >= 3:
                # It's a country dropdown block — skip the whole run
                i = run_end
                continue
        result.append(lines[i])
        i += 1
    return "\n".join(result)


def _remove_markdown_artifacts(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\\\n", "\n", text)
    text = re.sub(r"\(\d*\)\]\([^\n]*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\]\([^\n]{0,100}$", "", text, flags=re.MULTILINE)
    lines = text.splitlines()
    result = []
    i = 0
    while i < len(lines):
        result.append(lines[i])
        j = i + 1
        while j < len(lines) and lines[j].strip() == lines[i].strip() and lines[i].strip():
            j += 1
        if j - i >= 3:
            i = j
        else:
            i += 1
    return "\n".join(result)


def _clean_markdown(text: str) -> str:
    if not text:
        return ""

    text = _remove_markdown_artifacts(text)
    text = _remove_noise_blocks(text)

    # 2. Remove contact form country dropdown leakage
    text = _remove_country_dropdown_blocks(text)

    # 3. Drop noisy individual lines using compiled patterns
    lines = text.splitlines()
    cleaned = [
        line for line in lines
        if not any(p.search(line) for p in LINE_DROP_COMPILED)
        and not _is_country_line(line)
    ]
    result = "\n".join(cleaned)

    # 4. Convert [label](url) → label (keep text, remove URL noise)
    result = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", result)

    # 5. Remove bare URLs
    result = re.sub(r"https?://\S+", "", result)

    # 6. Collapse 3+ blank lines → 2
    result = re.sub(r"\n{3,}", "\n\n", result)

    # 7. Drop lines that became empty after cleaning
    result = "\n".join(line for line in result.splitlines() if line.strip())

    return result.strip()


# GLOBAL BOILERPLATE REMOVAL

def _remove_global_boilerplate(contents: List[str]) -> List[str]:
    """
    Detect and remove lines that appear across too many pages — these are
    site-wide nav/header/footer boilerplate, not real content.

    This is SELF-LEARNING per website: it finds repeated lines automatically,
    so it works for any site regardless of brand or content type.

    Only activates when we have enough pages (BOILERPLATE_MIN_PAGES) to
    reliably detect patterns. Threshold (BOILERPLATE_THRESHOLD = 30%) means:
    if a line appears on 30%+ of all scraped pages, it's boilerplate.

    Real content almost never appears on 30%+ of pages.
    Nav/footer/header items typically appear on 80-100% of pages.
    """
    if len(contents) < BOILERPLATE_MIN_PAGES:
        logger.info(
            "Boilerplate detection skipped: only %d pages (need %d+)",
            len(contents), BOILERPLATE_MIN_PAGES
        )
        return contents

    total = len(contents)
    line_counts: Counter = Counter()

    for content in contents:
        # Count each unique line per page (deduplicated within the page)
        # so a line repeated 10x on one page still only counts as 1 occurrence
        unique_lines = set(
            re.sub(r"^[\s*\->#]+", "", line).strip().lower()
            for line in content.splitlines()
            if len(line.strip()) > 5
        )
        for line in unique_lines:
            line_counts[line] += 1

    # Lines appearing on BOILERPLATE_THRESHOLD fraction of pages → boilerplate
    boilerplate: set = {
        line for line, count in line_counts.items()
        if count / total >= BOILERPLATE_THRESHOLD
    }

    if boilerplate:
        logger.info(
            "Boilerplate detection: found %d repeated lines across %d pages (threshold=%.0f%%)",
            len(boilerplate), total, BOILERPLATE_THRESHOLD * 100
        )

    cleaned = []
    for content in contents:
        lines = content.splitlines()
        filtered = [
            line for line in lines
            if re.sub(r"^[\s*\->#]+", "", line).strip().lower() not in boilerplate
        ]
        cleaned.append("\n".join(filtered))

    return cleaned


# CONTENT DEDUPLICATION

def _content_fingerprint(text: str) -> str:
    """
    Hash the middle section of content to detect template pages.

    Why middle? Because all pages on a site share the same header (top)
    and footer (bottom). Fingerprinting only the first 600 chars means
    two pages with different content but the same nav/header look identical.
    Skipping the first 200 chars and sampling the next 600 chars gets us
    into the actual unique content of the page.
    """
    # Skip first 200 chars (usually nav/header), sample next 600 chars
    sample = text[200:800] if len(text) > 800 else text
    normalized = re.sub(r"\s+", " ", sample.lower().strip())
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


# CORE SCRAPING

async def scrape_url(url: str) -> str:
    """Scrape a single URL and return cleaned markdown."""
    try:
        result = await asyncio.to_thread(
            app.scrape,
            url,
            formats=["markdown"],
            only_main_content=True,
            headers={
                "Accept-Language": "en-IN,en;q=0.9",
                "Cookie": "location=IN; currency=INR",
            }
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

            # Reject pages that returned the geo-selector popup instead of real content
            if "CHOOSE YOUR SHIPPING LOCATION" in content or "Remember Selection" in content:
                logger.warning("[%d/%d] Geo-popup detected, skipping: %s", index, total, url)
                return None

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


async def _scrape_concurrent(
    urls: List[str],
    concurrency: int = CONCURRENCY,
    on_progress: ProgressCallback = None,
    progress_range: tuple = (15, 70),
) -> List[str]:
    """Scrape a list of URLs concurrently, return non-empty results."""
    semaphore = asyncio.Semaphore(concurrency)
    total = len(urls)
    completed = 0
    start_pct, end_pct = progress_range

    async def _scrape_and_track(url: str, index: int) -> Optional[str]:
        nonlocal completed
        result = await _scrape_with_semaphore(semaphore, url, index, total)
        completed += 1
        if on_progress:
            pct = int(start_pct + (completed / max(total, 1)) * (end_pct - start_pct))
            on_progress(pct, f"Scraped {completed}/{total} pages")
        return result

    tasks = [_scrape_and_track(url, i + 1) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


async def scrape_multiple_urls(urls: List[str]) -> str:
    """Public helper — scrape multiple URLs (used by train_router for file/faq flows)."""
    contents = await _scrape_concurrent(urls)
    contents = _remove_global_boilerplate(contents)
    unique = _deduplicate_content(contents)
    return "\n\n---\n\n".join(unique)


# MAIN ENTRY POINT

async def scrape_website(base_url: str, on_progress: ProgressCallback = None) -> str:
    """
    Main entry point.

    Flow A — Specific deep page (2+ path segments): scrape directly.

    Flow B — Homepage or shallow URL (full site):
      1. Map → discover all URLs
      2. Detect site type (shopify / ecommerce / service / restaurant / realestate / education)
      3. Filter + prioritize:
         - Guaranteed pages (faq, about, contact, pricing, policies, size charts) always included first
         - Remaining pages sorted by priority score, group-capped by site type, depth-capped
      4. Scrape concurrently (CONCURRENCY parallel requests)
      4.5. Remove site-wide boilerplate (self-learning, works for any site)
      5. Deduplicate by content fingerprint (middle-section sampling)
      Fallback 1: Firecrawl crawl (if Map fails)
      Fallback 2: Single page scrape (if crawl also fails)
    """
    def emit(percent: int, message: str, **extras):
        if on_progress:
            on_progress(percent, message, **extras)

    parsed = urlparse(base_url)
    path_parts = [p for p in parsed.path.split("/") if p]

    # ── Flow A: Single specific page ─────────────────────────────────────
    if len(path_parts) >= 2:
        logger.info("Specific page — scraping directly: %s", base_url)
        emit(10, "Scraping page...")
        content = await scrape_url(base_url)
        emit(70, "Processing content...")
        _save_debug(content)
        emit(73, "Extracting images...")
        image_map, keyword_index, product_texts = await extract_images(base_url, [base_url])
        # For Shopify single-page scrapes, prepend product catalogue if available
        is_shopify = _is_shopify_site([base_url]) or bool(product_texts)
        if is_shopify and product_texts:
            products_block = "\n\n---\n\n".join(product_texts)
            content = products_block + "\n\n---\n\n" + content
        return content, (image_map, keyword_index)

    # ── Flow B: Full website ──────────────────────────────────────────────
    logger.info("Full site scrape starting for: %s", base_url)

    try:
        # Step 1: Discover URLs
        emit(0, "Discovering pages on your website...")
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
        emit(10, f"Found {len(all_urls)} pages — filtering...")
        _save_map_debug(all_urls)

        # Always include homepage
        homepage = base_url.rstrip("/")
        if homepage not in [u.rstrip("/") for u in all_urls]:
            all_urls.insert(0, homepage)

        # Step 2: Detect site type
        site_type = _detect_site_type(all_urls)
        is_shopify = (site_type == "shopify")
        logger.info("Site type detected: %s", site_type)

        # Step 3: Filter, prioritize, group-cap, depth-cap
        emit(12, "Prioritizing pages...")
        urls_to_scrape = _filter_and_prioritize(all_urls, base_url, site_type)
        if not urls_to_scrape:
            raise ValueError("No URLs remaining after filtering")

        emit(15, f"Scraping {len(urls_to_scrape)} pages...")
        logger.info(
            "Scraping %d URLs (concurrency=%d, site_type=%s)",
            len(urls_to_scrape), CONCURRENCY, site_type
        )

        # Step 4: Concurrent scrape — emits per-page progress from 15% → 70%
        contents = await _scrape_concurrent(
            urls_to_scrape,
            CONCURRENCY,
            on_progress=on_progress,
            progress_range=(15, 70),
        )

        # Step 4.5: Remove site-wide boilerplate
        emit(70, "Removing boilerplate...")
        contents = _remove_global_boilerplate(contents)

        # Step 5: Deduplicate by middle-section fingerprint
        emit(72, "Deduplicating content...")
        unique_contents = _deduplicate_content(contents)

        # Extract images early so product_texts is available for geo-blocked fallback
        emit(73, "Extracting images...")
        image_map, keyword_index, product_texts = await extract_images(base_url, urls_to_scrape)

        scraped_text = "\n\n---\n\n".join(unique_contents)
        if not unique_contents or len(scraped_text) < 500:
            if is_shopify and product_texts:
                logger.info(
                    "No scraped content (geo-blocked) — using Shopify product feed only (%d products)",
                    len(product_texts)
                )
                combined = "\n\n---\n\n".join(product_texts)
                _save_debug(combined)
                return combined, (image_map, keyword_index)
            else:
                raise ValueError("No meaningful content after scraping")

        logger.info(
            "Done: %d unique pages / %d scraped (%.0f%% yield)",
            len(unique_contents), len(urls_to_scrape),
            100 * len(unique_contents) / max(len(urls_to_scrape), 1)
        )

        combined = "\n\n---\n\n".join(unique_contents)
        _save_debug(combined)

        # Inject Shopify product catalogue into scraped content
        if is_shopify and product_texts:
            logger.info("Prepending %d Shopify product texts to combined content", len(product_texts))
            products_block = "\n\n---\n\n".join(product_texts)
            combined = products_block + "\n\n---\n\n" + combined

        return combined, (image_map, keyword_index)

    except Exception as e:
        logger.warning("Map-first failed (%s) — trying crawl fallback", e)
        emit(10, "Map failed — trying crawl fallback...")

        # Fallback 1: Crawl
        try:
            emit(15, "Crawling website...")
            result = await asyncio.to_thread(
                app.crawl,
                base_url,
                limit=50,
                scrape_options={"formats": ["markdown"], "onlyMainContent": True}
            )
            pages = result.data if result and result.data else []
            contents = []
            seen_fps = set()
            total_pages = len(pages)
            for i, page in enumerate(pages):
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
                pct = int(15 + ((i + 1) / max(total_pages, 1)) * 55)
                emit(pct, f"Crawled {i + 1}/{total_pages} pages")

            if not contents:
                raise ValueError("Crawl returned no content")

            emit(70, "Removing boilerplate...")
            contents = _remove_global_boilerplate(contents)

            logger.info("Crawl fallback: %d unique pages", len(contents))
            combined = "\n\n---\n\n".join(contents)
            _save_debug(combined)

            emit(73, "Extracting images...")
            image_map, keyword_index, product_texts = await extract_images(base_url, [])

            # Detect Shopify for fallback path
            is_shopify_fallback = _is_shopify_site([base_url]) or bool(product_texts)
            if is_shopify_fallback and product_texts:
                logger.info("Crawl fallback: prepending %d Shopify product texts", len(product_texts))
                products_block = "\n\n---\n\n".join(product_texts)
                combined = products_block + "\n\n---\n\n" + combined

            return combined, (image_map, keyword_index)

        except Exception as e2:
            logger.warning("Crawl fallback failed (%s) — single page scrape", e2)
            emit(20, "Scraping main page...")
            content = await scrape_url(base_url)
            emit(70, "Processing content...")
            _save_debug(content)
            emit(73, "Extracting images...")
            image_map, keyword_index, product_texts = await extract_images(base_url, [base_url])
            # Detect Shopify for single-page fallback
            is_shopify_fallback2 = _is_shopify_site([base_url]) or bool(product_texts)
            if is_shopify_fallback2 and product_texts:
                logger.info("Single-page fallback: prepending %d Shopify product texts", len(product_texts))
                products_block = "\n\n---\n\n".join(product_texts)
                content = products_block + "\n\n---\n\n" + content
            return content, (image_map, keyword_index)


# HELPERS

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


# FILE EXTRACTORS

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