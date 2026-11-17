from eval.metrics import contains_keywords, digits_equal, normalize, score_document, similar
from eval.run_eval import load_dataset, summarize


def test_normalize_strips_accents_and_case():
    assert normalize("  JOÃO  da Silva. ") == "joao da silva"


def test_digits_equal_ignores_punctuation():
    assert digits_equal("123.456.789-00", "12345678900")
    assert not digits_equal("123.456.789-00", "123.456.789-01")


def test_similar_tolerates_small_differences():
    assert similar(0.9)("Rua A, nº 10, Centro, Curitiba - PR", "Rua A, n° 10, Centro, Curitiba-PR")


def test_keywords_are_accent_insensitive():
    assert contains_keywords(["manutencao", "ar-condicionado"], "Manutenção de ar-condicionado")


def test_score_document_flags_wrong_fields():
    label = {"tenant": {"name": "Ana", "document": "1"}, "monthly_rent": 100.0}
    pred = {"tenant": {"name": "ANA", "document": "2"}, "monthly_rent": 100.001}
    assert score_document(label, pred) == {
        "tenant.name": True,
        "tenant.document": False,
        "monthly_rent": True,
    }


def test_perfect_predictions_score_100_percent():
    rows = load_dataset(limit=None)
    preds = [
        {"id": r["id"], "contract_type": r["contract_type"], "data": r["label"],
         "latency_ms": 1000, "error": None}
        for r in rows
    ]
    report = summarize(rows, preds, "oracle")
    assert "Classification accuracy:** 100.0%" in report
    assert "Field accuracy (overall):** 100.0%" in report
