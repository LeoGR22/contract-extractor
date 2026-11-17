from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from collections import defaultdict
from pathlib import Path

from app.extractor import ContractExtractor
from eval.metrics import score_document

DESCRIPTION = "Avalia o extrator no dataset rotulado."
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
EVAL_DIR = ROOT / "eval"


def load_dataset(limit: int | None) -> list[dict]:
    rows = [json.loads(line) for line in (DATA_DIR / "ground_truth.jsonl").open(encoding="utf-8")]
    return rows[:limit] if limit else rows


async def predict(extractor: ContractExtractor, row: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        content = (DATA_DIR / row["file"]).read_bytes()
        try:
            result = await extractor.extract(content, "application/pdf")
            return {
                "id": row["id"],
                "contract_type": result.contract_type.value,
                "data": result.data.model_dump(mode="json") if result.data else None,
                "latency_ms": result.latency_ms,
                "error": None,
            }
        except Exception as exc:  # noqa: BLE001 - an eval run must survive single failures
            return {"id": row["id"], "contract_type": None, "data": None, "latency_ms": None,
                    "error": f"{type(exc).__name__}: {exc}"}


def summarize(rows: list[dict], preds: list[dict], model: str) -> str:
    by_id = {p["id"]: p for p in preds}
    cls_correct = sum(by_id[r["id"]]["contract_type"] == r["contract_type"] for r in rows)

    field_hits: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["label"] is None:
            continue
        pred = by_id[row["id"]]
        data = pred["data"] if pred["contract_type"] == row["contract_type"] else None
        for field, ok in score_document(row["label"], data).items():
            field_hits[row["contract_type"]][field].append(ok)

    latencies = [p["latency_ms"] for p in preds if p["latency_ms"] is not None]
    errors = [p for p in preds if p["error"]]
    all_hits = [ok for fields in field_hits.values() for hits in fields.values() for ok in hits]

    lines = [
        "# Evaluation results",
        "",
        f"- **Model:** `{model}`",
        f"- **Documents:** {len(rows)} ({sum(r['label'] is not None for r in rows)} labeled contracts)",
        f"- **Classification accuracy:** {cls_correct / len(rows):.1%}",
        f"- **Field accuracy (overall):** {sum(all_hits) / max(len(all_hits), 1):.1%}",
    ]
    if latencies:
        p95 = sorted(latencies)[max(int(len(latencies) * 0.95) - 1, 0)]
        lines.append(f"- **Latency:** mean {statistics.mean(latencies) / 1000:.1f}s · p95 {p95 / 1000:.1f}s")
    lines.append(f"- **Errors:** {len(errors)}")

    for ctype, fields in sorted(field_hits.items()):
        lines += ["", f"## {ctype}", "", "| Field | Accuracy | Correct |", "|---|---:|---:|"]
        for field, hits in sorted(fields.items()):
            lines.append(f"| `{field}` | {sum(hits) / len(hits):.0%} | {sum(hits)}/{len(hits)} |")

    if errors:
        lines += ["", "## Errors", ""] + [f"- `{e['id']}`: {e['error']}" for e in errors]
    return "\n".join(lines) + "\n"


async def main() -> None:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    rows = load_dataset(args.limit)
    extractor = ContractExtractor()
    sem = asyncio.Semaphore(args.concurrency)
    preds = await asyncio.gather(*(predict(extractor, row, sem) for row in rows))

    with (EVAL_DIR / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for p in preds:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    report = summarize(rows, preds, extractor.settings.gemini_model)
    (EVAL_DIR / "results.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
