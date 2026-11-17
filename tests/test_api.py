import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.extractor import ContractExtractor
from app.main import app, get_extractor


@pytest.fixture
def client(fake_client_factory):
    extractor = ContractExtractor(client=fake_client_factory(), settings=Settings(gemini_model="test-model"))
    app.dependency_overrides[get_extractor] = lambda: extractor
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_extract_pdf(client):
    response = client.post("/extract", files={"file": ("c.pdf", b"%PDF-fake", "application/pdf")})

    assert response.status_code == 200
    body = response.json()
    assert body["contract_type"] == "rental"
    assert body["model"] == "test-model"
    assert body["data"]["tenant"]["name"] == "Bruno Lima"
    assert body["data"]["guarantee_type"] == "deposit"


def test_rejects_unsupported_type(client):
    response = client.post("/extract", files={"file": ("c.png", b"\x89PNG", "image/png")})
    assert response.status_code == 415


def test_rejects_empty_file(client):
    response = client.post("/extract", files={"file": ("c.pdf", b"", "application/pdf")})
    assert response.status_code == 400
