from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from google.genai import errors as genai_errors

from app.config import Settings, get_settings
from app.extractor import ContractExtractor, ExtractionError
from app.schemas import ExtractionResponse

logging.basicConfig(level=logging.INFO)

ALLOWED_MIME_TYPES = {"application/pdf", "text/plain"}

app = FastAPI(
    title="Contract Extractor",
    description=(
        "Extracts structured data from Brazilian rental and service contracts "
        "using Gemini structured output."
    ),
    version="0.1.0",
)


@lru_cache
def get_extractor() -> ContractExtractor:
    return ContractExtractor()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract", response_model=ExtractionResponse)
async def extract(
    file: Annotated[UploadFile, File(description="Contract as PDF or plain text.")],
    extractor: Annotated[ContractExtractor, Depends(get_extractor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ExtractionResponse:
    mime_type = (file.content_type or "").split(";")[0].strip()
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type '{mime_type}'. Send a PDF or a .txt file.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file.")
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, f"File larger than {settings.max_upload_mb} MB."
        )

    try:
        result = await extractor.extract(content, mime_type)
    except ExtractionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except genai_errors.APIError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Gemini API error: {exc}") from exc

    return ExtractionResponse(
        contract_type=result.contract_type,
        data=result.data,
        model=result.model,
        latency_ms=result.latency_ms,
    )
