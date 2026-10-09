from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["retrieval_enabled"] is False

def test_supported_not_yet_enabled():
    r = client.post("/v1/preview", json={"url": "https://www.amazon.co.uk/dp/B012345678"})
    assert r.status_code == 501
    assert r.json()["detail"]["provider"] == "amazon"

def test_rejects_untrusted_host():
    for url in ("https://amazon.co.uk.evil.example/dp/item", "http://amazon.co.uk/dp/item", "https://127.0.0.1/"):
        assert client.post("/v1/preview", json={"url": url}).status_code == 400
