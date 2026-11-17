from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("GOOGLE_API_KEY", "test-key")

RENTAL_JSON = {
    "landlord": {"name": "Ana Souza", "document": "123.456.789-00"},
    "tenant": {"name": "Bruno Lima", "document": "987.654.321-00"},
    "property_address": "Rua das Flores, nº 10, Centro, Curitiba - PR, CEP 80000-000",
    "monthly_rent": 2350.0,
    "due_day": 10,
    "start_date": "2025-03-15",
    "term_months": 30,
    "adjustment_index": "IGP-M",
    "guarantee_type": "deposit",
    "termination_penalty_months": 3.0,
}


class FakeModels:
    def __init__(self, contract_type: str = "rental", extraction: dict | str | None = None):
        self.contract_type = contract_type
        self.extraction = RENTAL_JSON if extraction is None else extraction
        self.calls: list[dict] = []

    async def generate_content(self, *, model, contents, config):
        schema_title = config.response_json_schema.get("title")
        self.calls.append({"model": model, "schema": schema_title})
        if schema_title == "Classification":
            payload = {"contract_type": self.contract_type}
        else:
            payload = self.extraction
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return SimpleNamespace(text=text)


def make_client(**kwargs) -> SimpleNamespace:
    models = FakeModels(**kwargs)
    return SimpleNamespace(aio=SimpleNamespace(models=models))


@pytest.fixture
def fake_client_factory():
    return make_client
