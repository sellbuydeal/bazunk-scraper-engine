"""Provider identification and URL-only metadata. No external requests."""
from dataclasses import dataclass
from urllib.parse import urlsplit, unquote
import ipaddress
import re

DOMAINS = {
    "amazon": ("amazon.co.uk", "amazon.com", "amazon.com.br"),
    "aliexpress": ("aliexpress.com",),
    "mercado_livre": ("mercadolivre.com.br", "mercadolibre.com", "mercadolibre.com.mx"),
    "shein": ("shein.com", "shein.co.uk"),
    "shopee": ("shopee.com.br", "shopee.sg", "shopee.ph"),
}
AMAZON_ASIN = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", re.I)
ALI_ITEM = re.compile(r"/item/(\d+)\.html(?:$|/)", re.I)

@dataclass(frozen=True)
class ProductTarget:
    provider: str
    url: str
    product_id: str | None
    region: str

def parse_product_url(url: str) -> ProductTarget:
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("Invalid URL")
    try:
        p = urlsplit(url)
        host = (p.hostname or "").rstrip(".").lower()
        port = p.port
    except ValueError as exc:
        raise ValueError("Invalid URL") from exc
    if p.scheme != "https" or not host or p.username or p.password or port not in (None, 443):
        raise ValueError("Only public HTTPS product URLs are supported")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("IP addresses are not permitted")
    provider = next((name for name, domains in DOMAINS.items()
                     if any(host == domain or host.endswith("." + domain) for domain in domains)), None)
    if provider is None:
        raise ValueError("Unsupported product domain")
    path = unquote(p.path)
    if provider == "amazon":
        match = AMAZON_ASIN.search(path)
        if not match:
            raise ValueError("Amazon URL must include /dp/ASIN or /gp/product/ASIN")
        product_id = match.group(1).upper()
        region = "uk" if host.endswith(".co.uk") else "br" if host.endswith(".com.br") else "us"
        canonical = f"https://www.{('amazon.co.uk' if region == 'uk' else 'amazon.com.br' if region == 'br' else 'amazon.com')}/dp/{product_id}"
    elif provider == "aliexpress":
        match = ALI_ITEM.search(path)
        if not match:
            raise ValueError("AliExpress URL must contain /item/123456.html")
        product_id = match.group(1)
        region = "global"
        canonical = f"https://www.aliexpress.com/item/{product_id}.html"
    else:
        if path in ("", "/"):
            raise ValueError("A product path is required")
        product_id = None
        region = host
        canonical = f"https://{host}{p.path}"
    return ProductTarget(provider, canonical, product_id, region)
