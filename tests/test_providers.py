import pytest
from app.providers import parse_product_url

@pytest.mark.parametrize("url,provider,product_id,region", [
    ("https://www.amazon.co.uk/dp/B012345678?tag=abc", "amazon", "B012345678", "uk"),
    ("https://amazon.com/gp/product/B012345678/ref=foo", "amazon", "B012345678", "us"),
    ("https://www.aliexpress.com/item/1005001234567890.html?spm=abc", "aliexpress", "1005001234567890", "global"),
    ("https://www.mercadolivre.com.br/example-product", "mercado_livre", None, "www.mercadolivre.com.br"),
    ("https://shopee.sg/example-product", "shopee", None, "shopee.sg"),
])
def test_parse(url, provider, product_id, region):
    target = parse_product_url(url)
    assert (target.provider, target.product_id, target.region) == (provider, product_id, region)
    assert "?" not in target.url

@pytest.mark.parametrize("url", [
    "http://amazon.co.uk/dp/B012345678",
    "https://amazon.co.uk.evil.example/dp/B012345678",
    "https://127.0.0.1/dp/B012345678",
    "https://user:pass@amazon.co.uk/dp/B012345678",
    "https://amazon.co.uk/",
    "https://aliexpress.com/item/not-a-product",
    "https://shopee.sg/",
])
def test_reject(url):
    with pytest.raises(ValueError):
        parse_product_url(url)
