"""AliExpress public-page extraction; no login, CAPTCHA bypass, or proxy rotation."""
import json
import os
import re
from html import unescape
from html.parser import HTMLParser
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from urllib.parse import quote

MAX_BYTES = 2_000_000

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.jsonld = []
        self.in_ld = False
        self.parts = []
        self.meta = {}
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self.in_ld = True
            self.parts = []
        if tag == "meta" and a.get("content"):
            key = a.get("property") or a.get("name")
            if key:
                self.meta[key] = a["content"]
    def handle_data(self, data):
        if self.in_ld:
            self.parts.append(data)
    def handle_endtag(self, tag):
        if tag == "script" and self.in_ld:
            self.in_ld = False
            try:
                self.jsonld.append(json.loads("".join(self.parts)))
            except (ValueError, TypeError):
                pass

def fetch_html(url: str) -> str:
    # Callers construct URLs from validated IDs / encoded queries only.
    request = Request(url, headers={"User-Agent": "BazunkProductIndexer/1.0 (+product-data)", "Accept": "text/html"})
    try:
        with build_opener(NoRedirect).open(request, timeout=12) as response:
            if response.status != 200:
                raise ValueError("Upstream HTTP " + str(response.status))
            if "text/html" not in response.headers.get("Content-Type", ""):
                raise ValueError("Upstream returned non-HTML content")
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("Upstream page exceeds size limit")
            return raw.decode("utf-8", "replace")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ValueError("AliExpress page unavailable: " + str(exc)) from exc

def _products(data):
    if isinstance(data, list):
        for value in data:
            yield from _products(value)
    elif isinstance(data, dict):
        typ = data.get("@type", "")
        if typ == "Product" or isinstance(typ, list) and "Product" in typ:
            yield data
        for value in data.get("@graph", []):
            yield from _products(value)

def product_by_id(product_id: str) -> dict:
    if not re.fullmatch(r"\d{10,20}", product_id):
        raise ValueError("Invalid AliExpress product ID")
    url = f"https://www.aliexpress.com/item/{product_id}.html"
    parser = PageParser()
    parser.feed(fetch_html(url))
    data = next((p for block in parser.jsonld for p in _products(block)), None)
    if data is None:
        raise ValueError("Product structured data unavailable (page may require browser verification)")
    offers = data.get("offers", {})
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        offers = {}
    images = data.get("image", [])
    if isinstance(images, str):
        images = [images]
    images = [i for i in images if isinstance(i, str) and i.startswith("https://")][:12]
    price = offers.get("price") or offers.get("lowPrice")
    try:
        price = float(price) if price is not None else None
    except (ValueError, TypeError):
        price = None
    rating = data.get("aggregateRating") or {}
    return {"provider": "aliexpress", "externalId": product_id, "sourceUrl": url,
            "title": str(data.get("name") or parser.meta.get("og:title") or "")[:500],
            "description": str(data.get("description") or "")[:10000],
            "price": {"amount": price, "currency": offers.get("priceCurrency", "USD")} if price is not None else None,
            "images": [{"url": i} for i in images], "features": [], "variants": [],
            "availability": "in_stock" if str(offers.get("availability", "")).endswith("InStock") else "unknown",
            "rating": rating.get("ratingValue") if isinstance(rating, dict) else None,
            "reviewCount": rating.get("reviewCount") if isinstance(rating, dict) else None}

def search_products(query: str, page: int = 1) -> dict:
    if not query.strip() or len(query) > 120 or not 1 <= page <= 100:
        raise ValueError("Invalid search request")
    url = "https://www.aliexpress.com/w/wholesale-" + quote(query.strip().replace(" ", "-"), safe="-") + ".html?page=" + str(page)
    html = fetch_html(url)
    ids = list(dict.fromkeys(re.findall(r"(?:/item/|itemId[\\\"']?\\s*[:=]\\s*[\\\"']?)(\\d{10,20})", html)))
    # Search previews may be sparse; never fabricate titles or prices.
    items = [{"provider": "aliexpress", "externalId": id, "sourceUrl": f"https://www.aliexpress.com/item/{id}.html",
              "title": "", "images": [], "features": [], "variants": [], "availability": "unknown"} for id in ids[:30]]
    return {"provider": "aliexpress", "query": query, "page": page, "items": items, "nextPage": page + 1 if items else None}
