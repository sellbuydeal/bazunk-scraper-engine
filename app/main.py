"""Experimental Bazunk product preview API; no live retrieval enabled."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from urllib.parse import urlsplit
import ipaddress

app = FastAPI(title="Bazunk Scraper Engine", version="0.1.0")

ALLOWED_DOMAINS = {
    "amazon": ("amazon.co.uk", "amazon.com", "amazon.com.br"),
    "aliexpress": ("aliexpress.com",),
    "mercado_livre": ("mercadolivre.com.br", "mercadolibre.com"),
    "shein": ("shein.com",),
    "shopee": ("shopee.com.br", "shopee.sg", "shopee.ph"),
}

class PreviewRequest(BaseModel):
    url: str = Field(min_length=12, max_length=2048)

@app.get("/health")
def health():
    return {"status": "ok", "mode": "experimental", "retrieval_enabled": False}

@app.post("/v1/preview")
def preview(request: PreviewRequest):
    parts = urlsplit(request.url)
    host = (parts.hostname or "").rstrip(".").lower()
    if parts.scheme != "https" or not host or parts.username or parts.password or parts.port not in (None, 443):
        raise HTTPException(status_code=400, detail="A standard public HTTPS product URL is required")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise HTTPException(status_code=400, detail="IP addresses are not allowed")

    for provider, domains in ALLOWED_DOMAINS.items():
        if any(host == domain or host.endswith("." + domain) for domain in domains):
            raise HTTPException(status_code=501, detail={
                "provider": provider,
                "status": "not_implemented",
                "message": "Provider preview is not enabled. Existing Bazunk imports are unaffected."
            })
    raise HTTPException(status_code=400, detail="Unsupported product domain")
