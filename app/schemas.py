"""Shared contract for future independently validated provider adapters."""
from pydantic import BaseModel, Field, HttpUrl

class ProductPreview(BaseModel):
    provider: str
    source_url: HttpUrl
    product_id: str | None = None
    title: str = Field(min_length=1)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price: float = Field(ge=0)
    images: list[HttpUrl] = Field(default_factory=list)
    available: bool | None = None
    quantity: int | None = Field(default=None, ge=0)
    condition: str | None = None
    description: str | None = None
    retrieved_at: str
    source: str
