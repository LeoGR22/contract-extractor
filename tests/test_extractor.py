import pytest

from app.config import Settings
from app.extractor import ContractExtractor, ExtractionError
from app.schemas import ContractType, RentalContract

SETTINGS = Settings(gemini_model="test-model")


async def test_rental_two_step_flow(fake_client_factory):
    client = fake_client_factory(contract_type="rental")
    extractor = ContractExtractor(client=client, settings=SETTINGS)

    result = await extractor.extract(b"%PDF-fake", "application/pdf")

    assert result.contract_type is ContractType.RENTAL
    assert isinstance(result.data, RentalContract)
    assert result.data.monthly_rent == 2350.0
    assert result.data.start_date.isoformat() == "2025-03-15"
    assert [c["schema"] for c in client.aio.models.calls] == ["Classification", "RentalContract"]
    assert all(c["model"] == "test-model" for c in client.aio.models.calls)


async def test_other_document_skips_extraction(fake_client_factory):
    client = fake_client_factory(contract_type="other")
    extractor = ContractExtractor(client=client, settings=SETTINGS)

    result = await extractor.extract(b"declaracao", "text/plain")

    assert result.contract_type is ContractType.OTHER
    assert result.data is None
    assert len(client.aio.models.calls) == 1


async def test_invalid_model_output_raises(fake_client_factory):
    client = fake_client_factory(contract_type="rental", extraction="{not json")
    extractor = ContractExtractor(client=client, settings=SETTINGS)

    with pytest.raises(ExtractionError):
        await extractor.extract(b"%PDF-fake", "application/pdf")
