"""AliExpress public-page extraction; no login, CAPTCHA bypass, or proxy rotation."""
import json
import os
import re
from html import unescape
from html.parser import HTMLParser
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def _image_urls(value):
    if isinstance(value, dict):
        value = value.get("url") or value.get("contentUrl") or []
    if isinstance(value, str):
        value = [value]
    return list(dict.fromkeys(v if v.startswith("https://") else "https:" + v
                              for entry in (value if isinstance(value, list) else [])
                              for v in ([entry] if isinstance(entry, str) else [entry.get("url", "")] if isinstance(entry, dict) else [])
                              if v.startswith(("https://", "//"))))[:20]

def _offer_details(raw):
    offers = raw if isinstance(raw, list) else [raw] if isinstance(raw, dict) else []
    parsed = []
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        price = offer.get("price") or offer.get("lowPrice")
        if isinstance(offer.get("priceSpecification"), dict):
            price = price or offer["priceSpecification"].get("price")
        try:
            price = float(str(price).replace(",", "")) if price is not None else None
        except (TypeError, ValueError):
            price = None
        currency = str(offer.get("priceCurrency") or "USD").upper()
        stock = str(offer.get("availability") or "").lower()
        availability = "out_of_stock" if "outofstock" in stock or "soldout" in stock else "in_stock" if "instock" in stock else "unknown"
        parsed.append({"price": {"amount": price, "currency": currency} if price is not None else None,
                       "availability": availability,
                       "shipping": offer.get("shippingDetails") if isinstance(offer.get("shippingDetails"), (dict, list)) else None,
                       "sku": str(offer.get("sku") or "")})
    return parsed

def _extract_product(html, product_id):
    parser = PageParser()
    parser.feed(html)
    data = next((p for block in parser.jsonld for p in _products(block)), None)
    if data is None:
        raise ValueError("Product structured data unavailable (page may require browser verification)")
    offers = _offer_details(data.get("offers"))
    main_offer = next((o for o in offers if o["price"]), offers[0] if offers else {})
    image_list = _image_urls(data.get("image")) or _image_urls(parser.meta.get("og:image"))
    rating = data.get("aggregateRating") or {}
    if not isinstance(rating, dict):
        rating = {}
    variants = []
    for variant in data.get("hasVariant", []) if isinstance(data.get("hasVariant"), list) else []:
        if isinstance(variant, dict):
            variants.append({"name": str(variant.get("name") or "")[:200],
                             "sku": str(variant.get("sku") or "")[:100],
                             "images": [{"url": u} for u in _image_urls(variant.get("image"))[:3]],
                             "offers": _offer_details(variant.get("offers"))})
    shipping = main_offer.get("shipping")
    return {"provider": "aliexpress", "externalId": product_id,
            "sourceUrl": f"https://www.aliexpress.com/item/{product_id}.html",
            "title": unescape(str(data.get("name") or parser.meta.get("og:title") or ""))[:500],
            "description": unescape(str(data.get("description") or "")).strip()[:10000],
            "category": str(data.get("category") or ""),
            "price": main_offer.get("price"), "images": [{"url": i} for i in image_list],
            "features": [], "variants": variants[:100], "shipping": shipping,
            "availability": main_offer.get("availability", "unknown"),
            "rating": rating.get("ratingValue"), "reviewCount": rating.get("reviewCount"),
            "sku": str(data.get("sku") or "")[:100]}

def product_by_id(product_id: str) -> dict:
    if not re.fullmatch(r"\\d{10,20}", product_id):
        raise ValueError("Invalid AliExpress product ID")
    url = f"https://www.aliexpress.com/item/{product_id}.html"
    return _extract_product(fetch_html(url), product_id)

def search_products(query: str, page: int = 1) -> dict:
    if not query.strip() or len(query) > 120 or not 1 <= page <= 100:
        raise ValueError("Invalid search request")
    url = "https://www.aliexpress.com/w/wholesale-" + quote(query.strip().replace(" ", "-"), safe="-") + ".html?page=" + str(page)
    html = fetch_html(url)
    parser = PageParser()
    parser.feed(html)
    # Search pages sometimes expose complete JSON-LD Product entries.
    found = {}
    for block in parser.jsonld:
        for product in _products(block):
            product_url = str(product.get("url") or "")
            match = re.search(r"/item/(\\d{10,20})", product_url)
            if match:
                try:
                    found[match.group(1)] = _extract_product(
                        '<script type="application/ld+json">' + json.dumps(product) + '</script>', match.group(1))
                except ValueError:
                    pass
    ids = list(dict.fromkeys(re.findall(r"/item/(\\d{10,20})", html)))
    for item_id in ids[:30]:
        found.setdefault(item_id, None)
    # Enrich only a small bounded batch to avoid flooding AliExpress.
    missing = [item_id for item_id, item in found.items() if item is None][:8]
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = {pool.submit(product_by_id, item_id): item_id for item_id in missing}
        for future in as_completed(jobs):
            try:
                found[jobs[future]] = future.result()
            except ValueError:
                pass
    items = [p for p in found.values() if p and p.get("title") and p.get("price")]
    return {"provider": "aliexpress", "query": query, "page": page, "items": items[:30],
            "nextPage": page + 1 if len(ids) >= 20 else None,
            "discovered": len(ids), "complete": len(items)}
