"""Experimental Bazunk product preview API; external retrieval disabled."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.providers import parse_product_url

app = FastAPI(title="Bazunk Scraper Engine", version="0.2.0")

class PreviewRequest(BaseModel):
    url: str = Field(min_length=12, max_length=2048)

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
