from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field

IsoDate = Annotated[
    date | None,
    Field(description="Date in ISO 8601 format (YYYY-MM-DD). Null if not stated."),
]


class ContractType(str, Enum):
    RENTAL = "rental"
    SERVICE = "service"
    OTHER = "other"


class Classification(BaseModel):
    contract_type: ContractType = Field(
        description=(
            "rental: residential or commercial lease (contrato de locação). "
            "service: service agreement (contrato de prestação de serviços). "
            "other: anything else."
        )
    )


class Party(BaseModel):
    name: str = Field(description="Full name of the person or company, as written.")
    document: str | None = Field(
        default=None,
        description="CPF or CNPJ exactly as written in the contract. Null if absent.",
    )


class GuaranteeType(str, Enum):
    DEPOSIT = "deposit"
    GUARANTOR = "guarantor"
    INSURANCE = "insurance"
    NONE = "none"


class RentalContract(BaseModel):
    landlord: Party = Field(description="LOCADOR(A).")
    tenant: Party = Field(description="LOCATÁRIO(A).")
    property_address: str = Field(description="Full address of the leased property.")
    monthly_rent: float = Field(description="Monthly rent in BRL, as a number (e.g. 2350.00).")
    due_day: int | None = Field(
        default=None, ge=1, le=31, description="Day of the month the rent is due."
    )
    start_date: IsoDate = None
    term_months: int | None = Field(default=None, description="Lease term in months.")
    adjustment_index: str | None = Field(
        default=None,
        description="Annual adjustment index, normalized to its acronym (IGP-M, IPCA, INPC...).",
    )
    guarantee_type: GuaranteeType = Field(
        description="deposit = caução, guarantor = fiador, insurance = seguro-fiança, none."
    )
    termination_penalty_months: float | None = Field(
        default=None,
        description="Early-termination penalty expressed as number of monthly rents.",
    )


class ServiceContract(BaseModel):
    client: Party = Field(description="CONTRATANTE.")
    provider: Party = Field(description="CONTRATADA / CONTRATADO.")
    scope: str = Field(description="Short summary (one sentence) of the contracted services.")
    total_value: float = Field(description="Total contract value in BRL, as a number.")
    payment_terms: str | None = Field(
        default=None, description="How payment is made, summarized in one short sentence."
    )
    start_date: IsoDate = None
    end_date: IsoDate = None
    jurisdiction: str | None = Field(
        default=None, description="City of the elected court (foro), without the state."
    )


class ExtractionResponse(BaseModel):
    contract_type: ContractType
    data: RentalContract | ServiceContract | None = Field(
        description="Extracted fields. Null when contract_type is 'other'."
    )
    model: str
    latency_ms: int


SCHEMA_BY_TYPE: dict[ContractType, type[BaseModel]] = {
    ContractType.RENTAL: RentalContract,
    ContractType.SERVICE: ServiceContract,
}
