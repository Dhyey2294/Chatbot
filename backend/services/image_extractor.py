import asyncio
import json
import logging
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Timeout for all HTTP requests in this module
_TIMEOUT = 10.0

_MAX_SHOPIFY_PRODUCTS = 2000

# Namespaces used in XML sitemaps with image extensions
_SITEMAP_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "image": "http://www.google.com/schemas/sitemap-image/1.1",
}

# Stopwords to exclude from tokenization (generic, domain-agnostic)
_STOPWORDS = {
    "with", "from", "that", "this", "have", "been", "will",
    "their", "about", "which", "when", "your", "into",
}


def _tokenize(text: str) -> list:
    """
    Split text into lowercase tokens by whitespace and punctuation.
    Filters out tokens shorter than 4 chars and common stopwords.
    """
    raw_tokens = re.split(r"[\s\-_/\\.,;:!?\"'()\[\]{}]+", text.lower())
    return [
        t for t in raw_tokens
        if len(t) >= 4 and t not in _STOPWORDS
    ]


_IMAGE_BLOCKLIST_PATTERNS = [
    r"/logo",
    r"logo\.",
    r"/brand",
    r"/favicon",
    r"favicon\.",
    r"/icons?/",
    r"\.svg$",
    r"/placeholder",
    r"placeholder\.",
    r"no.?image",
    r"default.?image",
    r"/banner",
    r"/header",
    r"/footer",
]
_IMAGE_BLOCKLIST_COMPILED = [re.compile(p, re.IGNORECASE) for p in _IMAGE_BLOCKLIST_PATTERNS]


def _is_blocked_image(url: str) -> bool:
    return any(p.search(url) for p in _IMAGE_BLOCKLIST_COMPILED)


def _build_keyword_index(image_map: dict) -> dict:
    """
    Build a keyword index from image map keys at training time.

    Tokenizes all image map keys, then for each token that appears
    in 3+ distinct keys, maps that token -> list of keys containing it.

    This is entirely dynamic — no hardcoded domain-specific words.
    """
    # token -> set of keys that contain it
    token_to_keys: dict = {}

    for key in image_map:
        for token in _tokenize(key):
            token_to_keys.setdefault(token, set()).add(key)

    # Only keep tokens that appear across 3+ distinct keys
    keyword_index = {
        token: list(keys)
        for token, keys in token_to_keys.items()
        if len(keys) >= 3
    }

    logger.info(
        "Keyword index built: %d tokens from %d image map keys",
        len(keyword_index), len(image_map)
    )
    return keyword_index


def _merge_image_maps(*maps: dict) -> dict:
    """
    Merge multiple {key: {"urls": [image_urls], "source_url": str}} dicts.
    For duplicate keys, union their image lists and deduplicate. Keep the first source_url seen.
    """
    merged: dict = {}
    for m in maps:
        for key, data in m.items():
            urls = data.get("urls", [])
            source_url = data.get("source_url", "")
            if key not in merged:
                merged[key] = {"urls": list(urls), "source_url": source_url}
            else:
                seen = set(merged[key]["urls"])
                for url in urls:
                    if url not in seen:
                        seen.add(url)
                        merged[key]["urls"].append(url)
    return merged


async def extract_images(base_url: str, scraped_urls: list) -> tuple:
    """
    Extract a {name: [image_urls]} map from a website, then build a keyword index.

    Runs ALL 4 sources and merges their results:
      1. Shopify /products.json feed
      2. XML sitemap (with image:loc tags)
      3. JSON-LD schema on scraped pages
      4. Open Graph tags on scraped pages

    Returns (image_map, keyword_index, product_texts). Never raises.
    product_texts is a list of plain-text product strings from the Shopify feed,
    or an empty list for non-Shopify sites.
    """
    base_url = base_url.rstrip("/")

    shopify_image_map = {}
    product_texts = []
    sitemap_result = {}
    json_ld_result = {}
    og_result = {}

    # Source 1: Shopify feed
    try:
        product_texts, shopify_image_map = await _try_shopify_feed(base_url)
        logger.info(
            "Image extractor [Shopify feed]: %d entries, %d product texts",
            len(shopify_image_map), len(product_texts)
        )
    except Exception as e:
        logger.debug("Shopify feed failed: %s", e)

    # Source 2: XML sitemap
    try:
        sitemap_result = await _try_sitemap(base_url)
        logger.info(
            "Image extractor [Sitemap]: %d entries", len(sitemap_result)
        )
    except Exception as e:
        logger.debug("Sitemap extraction failed: %s", e)

    # Sources 3 + 4: JSON-LD and OG tags on all scraped URLs
    all_urls = scraped_urls or []
    try:
        json_ld_result = await _try_json_ld(all_urls)
        logger.info(
            "Image extractor [JSON-LD]: %d entries from %d URLs",
            len(json_ld_result), len(all_urls)
        )
    except Exception as e:
        logger.debug("JSON-LD extraction failed: %s", e)

    try:
        og_result = await _try_og_tags(all_urls)
        logger.info(
            "Image extractor [OG tags]: %d entries from %d URLs",
            len(og_result), len(all_urls)
        )
    except Exception as e:
        logger.debug("OG tag extraction failed: %s", e)

    # Merge all sources
    image_map = _merge_image_maps(shopify_image_map, sitemap_result, json_ld_result, og_result)
    total = len(image_map)

    if total:
        logger.info(
            "Image extractor: merged %d total entries "
            "(shopify=%d, sitemap=%d, json_ld=%d, og=%d)",
            total,
            len(shopify_image_map), len(sitemap_result),
            len(json_ld_result), len(og_result),
        )
    else:
        logger.info("Image extractor: no images found from any source")

    # Build keyword index from the merged map
    keyword_index = _build_keyword_index(image_map)

    return image_map, keyword_index, product_texts


# ── Source 1: Shopify /products.json ─────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Remove all HTML tags from a string using a simple regex."""
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _format_product_text(product: dict, base_url: str) -> str:
    """
    Format a single Shopify product dict into a plain-text string for RAG.
    Returns an empty string if the product has no title.
    """
    title = (product.get("title") or "").strip()
    if not title:
        return ""

    lines = [title]

    handle = (product.get("handle") or "").strip()
    if handle:
        lines.append(f"URL: {base_url}/products/{handle}")

    vendor = (product.get("vendor") or "").strip()
    if vendor:
        lines.append(f"Vendor: {vendor}")

    product_type = (product.get("product_type") or "").strip()
    if product_type:
        lines.append(f"Type: {product_type}")

    # Price range from variants
    variants = product.get("variants") or []
    prices = []
    for v in variants:
        p = (v.get("price") or "").strip()
        if p:
            try:
                prices.append(float(p))
            except ValueError:
                pass
    if prices:
        lo = min(prices)
        hi = max(prices)
        if lo == hi:
            lines.append(f"Price: {lo:.2f}")
        else:
            lines.append(f"Price: {lo:.2f} - {hi:.2f}")

    # Variant options (skip if single default variant)
    if len(variants) > 1 or (len(variants) == 1 and (variants[0].get("title") or "").strip() != "Default Title"):
        option_titles = [v.get("title", "").strip() for v in variants if v.get("title", "").strip()]
        if option_titles:
            lines.append(f"Sizes/Options: {', '.join(option_titles)}")

    # Description — strip HTML, truncate to 500 chars
    body_html = (product.get("body_html") or "").strip()
    description = _strip_html(body_html)
    if description:
        if len(description) > 500:
            description = description[:500].rsplit(" ", 1)[0] + "..."
        lines.append(f"Description: {description}")

    # Tags
    tags = product.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if tags:
        lines.append(f"Tags: {', '.join(tags)}")

    return "\n".join(lines)


async def _try_shopify_feed(base_url: str) -> tuple:
    """
    Fetch paginated Shopify product feed.
    Returns (product_texts, image_map) where:
      - product_texts: list of plain-text strings, one per product
      - image_map: {title: [image_urls]}
    Returns ([], {}) on any failure — never raises.
    """
    product_texts = []
    image_map = {}
    page = 1

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            while True:
                url = f"{base_url}/products.json?limit=250&page={page}"
                try:
                    resp = await client.get(url)
                except Exception as e:
                    logger.debug("Shopify feed page %d fetch error: %s", page, e)
                    break

                if resp.status_code != 200:
                    break

                try:
                    data = resp.json()
                except Exception:
                    break

                products = data.get("products", [])
                if not products:
                    break  # No more pages

                for product in products:
                    title = (product.get("title") or "").strip()
                    if not title:
                        continue

                    # Build product text
                    text = _format_product_text(product, base_url)
                    if text:
                        product_texts.append(text)

                    # Build image map entry
                    images = product.get("images", [])
                    urls = [img["src"] for img in images if img.get("src") and not _is_blocked_image(img["src"])]
                    if urls:
                        handle = product.get("handle", "")
                        source_url = f"{base_url}/products/{handle}" if handle else base_url
                        image_map[title] = {"urls": urls, "source_url": source_url}

                # If we got fewer than 250, we're on the last page
                if len(products) < 250:
                    break
                page += 1
                await asyncio.sleep(0.5)

                if len(product_texts) >= _MAX_SHOPIFY_PRODUCTS:
                    product_texts = product_texts[:_MAX_SHOPIFY_PRODUCTS]
                    logger.info("Shopify feed: capped at %d products", _MAX_SHOPIFY_PRODUCTS)
                    break
    except Exception as e:
        logger.debug("Shopify feed unexpected error: %s", e)
        return [], {}

    return product_texts, image_map


# ── Source 2: XML Sitemap with image:loc tags ─────────────────────────────────

async def _try_sitemap(base_url: str) -> dict:
    """
    Fetch sitemap.xml (or sitemap_index.xml), find image:loc tags inside <url> blocks.
    """
    result = {}

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        # Try both common sitemap paths
        for path in ["/sitemap.xml", "/sitemap_index.xml"]:
            sitemap_url = base_url + path
            try:
                resp = await client.get(sitemap_url)
                if resp.status_code != 200:
                    continue
                xml_text = resp.text
            except Exception as e:
                logger.debug("Sitemap fetch failed for %s: %s", sitemap_url, e)
                continue

            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError as e:
                logger.debug("Sitemap XML parse error: %s", e)
                continue

            # Detect sitemap index (contains <sitemap> children)
            tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
            if tag == "sitemapindex":
                # Recurse into sub-sitemaps (look for product sitemaps specifically)
                sub_urls = []
                for sitemap_elem in root.iter():
                    loc_tag = sitemap_elem.tag.split("}")[-1] if "}" in sitemap_elem.tag else sitemap_elem.tag
                    if loc_tag == "loc" and sitemap_elem.text:
                        sub_url = sitemap_elem.text.strip()
                        # Prioritise product sitemaps
                        if "product" in sub_url.lower() or "image" in sub_url.lower():
                            sub_urls.insert(0, sub_url)
                        else:
                            sub_urls.append(sub_url)

                # Try up to 3 sub-sitemaps
                for sub_url in sub_urls[:3]:
                    try:
                        sub_resp = await client.get(sub_url)
                        if sub_resp.status_code == 200:
                            sub_result = _parse_image_sitemap(sub_resp.text)
                            result = _merge_image_maps(result, sub_result)
                    except Exception as e:
                        logger.debug("Sub-sitemap fetch failed for %s: %s", sub_url, e)
            else:
                # Regular sitemap — parse directly
                parsed = _parse_image_sitemap(xml_text)
                result = _merge_image_maps(result, parsed)

            if result:
                break  # Stop after first successful sitemap source

    return result


def _parse_image_sitemap(xml_text: str) -> dict:
    """Parse an XML sitemap and extract url → image:loc mappings."""
    result = {}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return result

    # Iterate over <url> elements
    for url_elem in root.iter():
        url_tag = url_elem.tag.split("}")[-1] if "}" in url_elem.tag else url_elem.tag
        if url_tag != "url":
            continue

        # Find the <loc> (page URL) — use it as the key
        page_loc = None
        image_locs = []

        for child in url_elem:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag == "loc":
                page_loc = (child.text or "").strip()
            elif child_tag == "image":
                # <image:image> element — look for <image:loc>
                for img_child in child:
                    img_tag = img_child.tag.split("}")[-1] if "}" in img_child.tag else img_child.tag
                    if img_tag == "loc" and img_child.text and not _is_blocked_image(img_child.text.strip()):
                        image_locs.append(img_child.text.strip())

        if page_loc and image_locs:
            # Use the last path segment of the URL as the key
            path = urlparse(page_loc).path.rstrip("/")
            key = path.split("/")[-1].replace("-", " ").replace("_", " ") if path else page_loc
            result[key] = {"urls": image_locs, "source_url": page_loc}

    return result


# ── Source 3: JSON-LD schema on key pages ─────────────────────────────────────

async def _try_json_ld(urls: list) -> dict:
    """
    Fetch all provided pages concurrently (semaphore=10) and extract image URLs
    from JSON-LD Product/Article/Org/WebPage schemas.
    """
    result = {}
    if not urls:
        return result

    semaphore = asyncio.Semaphore(3)

    async def _fetch_one(client: httpx.AsyncClient, url: str) -> tuple:
        async with semaphore:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return url, []
                return url, _extract_json_ld_images(resp.text)
            except Exception as e:
                logger.debug("JSON-LD page fetch failed for %s: %s", url, e)
                return url, []

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        tasks = [_fetch_one(client, url) for url in urls]
        responses = await asyncio.gather(*tasks)

    for url, images in responses:
        if images:
            path = urlparse(url).path.rstrip("/")
            key = path.split("/")[-1].replace("-", " ").replace("_", " ") if path else url
            if key in result:
                seen = set(result[key]["urls"])
                for img in images:
                    if img not in seen:
                        seen.add(img)
                        result[key]["urls"].append(img)
            else:
                result[key] = {"urls": images, "source_url": url}

    return result


def _extract_json_ld_images(html: str) -> list:
    """Extract image URLs from <script type="application/ld+json"> blocks in HTML."""
    images = []
    pattern = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.DOTALL | re.IGNORECASE
    )
    for match in pattern.finditer(html):
        raw = match.group(1).strip()
        try:
            data = json.loads(raw)
        except Exception:
            continue

        # Handle @graph arrays
        items = data if isinstance(data, list) else [data]
        for item in items:
            schema_type = item.get("@type", "")
            if not isinstance(schema_type, str):
                schema_type = " ".join(schema_type) if isinstance(schema_type, list) else ""

            if any(t in schema_type for t in ("Product", "Article", "Organization", "WebPage")):
                img = item.get("image")
                if not img:
                    continue
                if isinstance(img, str):
                    images.append(img)
                elif isinstance(img, list):
                    for i in img:
                        if isinstance(i, str):
                            images.append(i)
                        elif isinstance(i, dict) and i.get("url"):
                            images.append(i["url"])
                elif isinstance(img, dict) and img.get("url"):
                    images.append(img["url"])

    images = [img for img in images if not _is_blocked_image(img)]

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for url in images:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


# ── Source 4: Open Graph tags (fallback) ──────────────────────────────────────

async def _try_og_tags(urls: list) -> dict:
    """
    Fetch all provided pages concurrently (semaphore=10) and extract og:image
    meta tags as a fallback.
    """
    result = {}
    if not urls:
        return result

    semaphore = asyncio.Semaphore(3)

    async def _fetch_one(client: httpx.AsyncClient, url: str) -> tuple:
        async with semaphore:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return url, ""
                return url, _extract_og_image(resp.text)
            except Exception as e:
                logger.debug("OG tag page fetch failed for %s: %s", url, e)
                return url, ""

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        tasks = [_fetch_one(client, url) for url in urls]
        responses = await asyncio.gather(*tasks)

    for url, img_url in responses:
        if img_url and not _is_blocked_image(img_url):
            path = urlparse(url).path.rstrip("/")
            key = path.split("/")[-1].replace("-", " ").replace("_", " ") if path else url
            if key in result:
                if img_url not in result[key]["urls"]:
                    result[key]["urls"].append(img_url)
            else:
                result[key] = {"urls": [img_url], "source_url": url}

    return result


def _extract_og_image(html: str) -> str:
    """Extract the og:image URL from an HTML string."""
    pattern = re.compile(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        re.IGNORECASE
    )
    match = pattern.search(html)
    if match:
        return match.group(1).strip()

    # Also try reversed attribute order: content=... property=...
    pattern2 = re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        re.IGNORECASE
    )
    match2 = pattern2.search(html)
    if match2:
        return match2.group(1).strip()

    return ""
