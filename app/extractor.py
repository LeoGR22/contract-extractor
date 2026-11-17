from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.prompts import CLASSIFY_PROMPT, EXTRACT_PROMPT, KIND_LABEL
from app.schemas import SCHEMA_BY_TYPE, Classification, ContractType

logger = logging.getLogger(__name__)


class ExtractionError(RuntimeError):
    pass


@dataclass
class ExtractionResult:
    contract_type: ContractType
    data: BaseModel | None
    model: str
    latency_ms: int


class ContractExtractor:
    def __init__(self, client: genai.Client | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = client or genai.Client()

    def _config(self, schema: type[BaseModel]) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
            thinking_config=types.ThinkingConfig(thinking_level=self.settings.thinking_level),
        )

    async def _generate(self, prompt: str, document: types.Part, schema: type[BaseModel]):
        response = await self.client.aio.models.generate_content(
            model=self.settings.gemini_model,
            contents=[document, prompt],
            config=self._config(schema),
        )
        try:
            return schema.model_validate_json(response.text or "")
        except ValidationError as exc:
            logger.warning("Invalid model output for %s: %s", schema.__name__, response.text)
            raise ExtractionError(f"Model returned an invalid {schema.__name__}") from exc

    @staticmethod
    def _to_part(content: bytes, mime_type: str) -> types.Part:
        if mime_type == "text/plain":
            return types.Part.from_text(text=content.decode("utf-8", errors="replace"))
        return types.Part.from_bytes(data=content, mime_type=mime_type)

    async def classify(self, document: types.Part) -> ContractType:
        result = await self._generate(CLASSIFY_PROMPT, document, Classification)
        return result.contract_type

    async def extract(self, content: bytes, mime_type: str) -> ExtractionResult:
        started = time.perf_counter()
        document = self._to_part(content, mime_type)

        contract_type = await self.classify(document)
        data = None
        if contract_type in SCHEMA_BY_TYPE:
            prompt = EXTRACT_PROMPT.format(kind=KIND_LABEL[contract_type.value])
            data = await self._generate(prompt, document, SCHEMA_BY_TYPE[contract_type])

        return ExtractionResult(
            contract_type=contract_type,
            data=data,
            model=self.settings.gemini_model,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
