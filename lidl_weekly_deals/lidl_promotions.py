"""
Scrape the current weekly promotions from lidl.be.

Flow:
  1. Fetch the homepage and find the link to "aanbiedingen-deze-week".
  2. Fetch the promotions page.
  3. For each product tile (data-grid-data attribute on
     AProductGridbox__GridTilePlaceholder divs), parse the embedded JSON:
     - name, id, brand, category from top-level keys.
     - regular / discounted price from price.price / price.oldPrice.
     - quantity from price.basePrice.text (left of " - ").
     - Lidl Plus conditions from the lidlPlus list.
  4. Emit a JSON array to stdout.

Standard library only. Run with: python3 lidl_promotions.py
"""

import gzip
import html
import json
import re
import sys
import urllib.error
import urllib.request
import zlib


HOMEPAGE_URL = "https://www.lidl.be/"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_url(url: str) -> str:
    """Fetch a URL and return the decoded HTML body, handling gzip/deflate."""
    request = urllib.request.Request(url, headers=BROWSER_HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
        encoding = response.headers.get("Content-Encoding", "").lower()
        charset = response.headers.get_content_charset() or "utf-8"

    if encoding == "gzip":
        raw = gzip.decompress(raw)
    elif encoding == "deflate":
        # Some servers send raw deflate, others zlib-wrapped.
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)

    return raw.decode(charset, errors="replace")


# Match the promotions path wherever it appears in the homepage HTML:
#   - in href attributes as a relative path:  href="/c/nl-BE/aanbiedingen-deze-week/a10082242"
#   - in href attributes as an absolute URL:  href="https://www.lidl.be/c/nl-BE/aanbiedingen-deze-week/a10082242"
#   - inside JSON-escaped hydration data:     "url":"https:\u002F\u002Fwww.lidl.be\u002Fc\u002Fnl-BE\u002Faanbiedingen-deze-week\u002Fa10082242"
#                                       or:   "href":"\/c\/nl-BE\/aanbiedingen-deze-week\/a10082242"
# We capture only the trailing slug (e.g. a10082242) so we can rebuild a clean URL.
_PROMO_SLUG_PATTERN = re.compile(
    r"aanbiedingen-deze-week"      # the page name
    r"(?:\\u002F|\\/|/)"           # one separator: literal /, escaped \/, or unicode-escaped \u002F
    r"([a-zA-Z0-9_-]+)"            # the weekly slug, e.g. a10082242
)


def find_promotions_url(homepage_html: str) -> str:
    """Find the URL to this week's promotions page on the Lidl.be homepage.

    Lidl rotates the trailing slug (e.g. a10082242 -> a10082243) every week,
    and ships the homepage as a hybrid of server-rendered HTML and a JSON
    hydration blob, so the same URL may appear with different escapings. We
    extract just the slug and rebuild a canonical URL from it.
    """
    # Prefer slugs that appear in href="" attributes, as those are real links
    # rather than e.g. analytics payloads. Fall back to any match if needed.
    decoded_html = html.unescape(homepage_html)

    for candidate in _PROMO_SLUG_PATTERN.finditer(decoded_html):
        slug = candidate.group(1)
        # Sanity check: the slug shape Lidl uses is a letter prefix + digits
        # (e.g. a10082242). Skip anything that doesn't look like that to avoid
        # accidentally picking up a category or query-param fragment.
        if re.fullmatch(r"[a-z]\d{4,}", slug):
            return f"https://www.lidl.be/c/nl-BE/aanbiedingen-deze-week/{slug}"

    raise ValueError(
        "Could not find the weekly promotions link on the Lidl homepage "
        f"({HOMEPAGE_URL}). The page structure may have changed — inspect "
        "the homepage HTML to find the new href pattern for 'aanbiedingen-deze-week'."
    )


# ---------------------------------------------------------------------------
# Tile extraction
# ---------------------------------------------------------------------------

_GRID_DATA = re.compile(r'data-grid-data="([^"]+)"')


def find_tiles(page_html: str) -> list[dict]:
    """Return parsed JSON data for each product tile on the page.

    The site server-renders product data as HTML-entity-encoded JSON in
    data-grid-data attributes on AProductGridbox__GridTilePlaceholder divs.
    """
    tiles = []
    for m in _GRID_DATA.finditer(page_html):
        try:
            tiles.append(json.loads(html.unescape(m.group(1))))
        except (ValueError, json.JSONDecodeError):
            pass
    return tiles


# ---------------------------------------------------------------------------
# Per-tile parsing
# ---------------------------------------------------------------------------

def _parse_quantity(base_price: dict | None) -> str | None:
    """Extract the quantity/weight from price.basePrice.text.

    The text is like "1 kg - 0,99 EUR/kg" or "per stuk" — we keep the left
    part before " - " which is the quantity descriptor.
    """
    if not base_price:
        return None
    text = base_price.get("text", "")
    if not text:
        return None
    return text.split(" - ", 1)[0].strip() or None


def parse_tile(data: dict) -> dict | None:
    name = data.get("fullTitle") or data.get("title")
    if not name:
        return None

    price_block = data.get("price", {})
    lidl_plus_list = data.get("lidlPlus") or []

    # Normal (non-Lidl-Plus) price
    discounted = _to_float(price_block.get("price"))
    regular = _to_float(price_block.get("oldPrice")) if price_block.get("discount", {}).get("showDiscount") else None
    quantity = _parse_quantity(price_block.get("basePrice"))

    # Lidl Plus: when no normal price is present, the Lidl Plus entry IS the offer.
    special_conditions = None
    if lidl_plus_list:
        lp = lidl_plus_list[0]
        lp_price_block = lp.get("price", {})
        hint = lp.get("lidlPlusText", "Met je Lidl Plus-app")
        if discounted is None:
            discounted = _to_float(lp_price_block.get("price"))
            regular = _to_float(lp_price_block.get("oldPrice")) if lp_price_block.get("discount", {}).get("showDiscount") else None
            if not quantity:
                quantity = _parse_quantity(lp_price_block.get("basePrice"))
        special_conditions = hint

    brand_block = data.get("brand", {})
    brand = brand_block.get("name") if brand_block.get("showBrand") else None

    return {
        "id": str(data["productId"]) if data.get("productId") else None,
        "name": name,
        "brand": brand,
        "category": data.get("category") or (data.get("keyfacts") or {}).get("analyticsCategory"),
        "regular_price": regular,
        "discounted_price": discounted,
        "quantity": quantity,
        "special_conditions": special_conditions,
    }


def _to_float(value) -> float | None:
    """Convert '2,99' / '2.99' / 2.99 to a float; return None on failure."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+[.,]?\d*", str(value))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def scrape() -> list[dict]:
    print(f"Fetching homepage: {HOMEPAGE_URL}", file=sys.stderr)
    homepage = fetch_url(HOMEPAGE_URL)

    promo_url = find_promotions_url(homepage)
    print(f"Fetching promotions page: {promo_url}", file=sys.stderr)
    promo_page = fetch_url(promo_url)

    tiles = find_tiles(promo_page)
    print(f"Found {len(tiles)} product tiles.", file=sys.stderr)

    products: list[dict] = []
    # De-dup by id (tiles can appear in multiple carousels on the same page).
    seen_ids: set[str] = set()
    for tile_data in tiles:
        record = parse_tile(tile_data)
        if not record:
            continue
        tile_id = record.get("id")
        if tile_id and tile_id in seen_ids:
            continue
        if tile_id:
            seen_ids.add(tile_id)
        products.append(record)
    return products


def main() -> int:
    try:
        products = scrape()
    except urllib.error.HTTPError as exc:
        print(f"HTTP error: {exc.code} {exc.reason} ({exc.url})", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not products:
        print(
            "No products extracted. The page structure may have changed — "
            "consider saving the HTML and inspecting it.",
            file=sys.stderr,
        )
        return 2

    json.dump(products, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    print(f"Extracted {len(products)} products.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())