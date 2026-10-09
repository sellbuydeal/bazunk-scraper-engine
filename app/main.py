"""Experimental Bazunk product preview API; external retrieval disabled."""
from fastapi import FastAPI, HTTPException, Header, Depends
import os
from app.aliexpress import product_by_id, search_products
from pydantic import BaseModel, Field
from app.providers import parse_product_url

def require_token(authorization: str | None = Header(default=None)):
    token = os.getenv("SCRAPER_API_TOKEN", "")
    if not token or authorization != "Bearer " + token:
        raise HTTPException(status_code=401, detail="Scraper service authentication required")

app = FastAPI(title="Bazunk Scraper Engine", version="0.2.0")

class PreviewRequest(BaseModel):
    url: str = Field(min_length=12, max_length=2048)

@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok", "mode": "experimental", "retrieval_enabled": False}

@app.post("/v1/resolve")
def resolve(request: PreviewRequest):
    try:
        target = parse_product_url(request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "provider": target.provider,
        "canonical_url": target.url,
        "product_id": target.product_id,
        "region": target.region,
        "retrieval_enabled": False,
    }

@app.post("/v1/preview")
def preview(request: PreviewRequest):
    target = resolve(request)
    raise HTTPException(status_code=501, detail={
        "provider": target["provider"],
        "status": "not_implemented",
        "message": "Live product retrieval is not enabled; existing Bazunk imports are unaffected.",
    })

@app.get("/v1/aliexpress/search", dependencies=[Depends(require_token)])
def aliexpress_search(q: str, page: int = 1):
    try:
        return search_products(q, page)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.get("/v1/aliexpress/products/{product_id}", dependencies=[Depends(require_token)])
def aliexpress_product(product_id: str):
    try:
        return product_by_id(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
