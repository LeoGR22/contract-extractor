CLASSIFY_PROMPT = """\
You are classifying a Brazilian legal contract written in Portuguese.
Read the document and decide which kind of contract it is.
Answer only with the requested JSON.
"""

EXTRACT_PROMPT = """\
You are extracting structured data from a Brazilian {kind} written in Portuguese.

Rules:
- Use only information stated in the document. Never guess or infer missing values; use null.
- Monetary values: return a plain number in BRL (\"R$ 2.350,00\" -> 2350.00). If a value is
  written both in digits and in words, trust the digits.
- Dates: convert to ISO 8601 (\"15 de março de 2025\" -> \"2025-03-15\").
- CPF/CNPJ: copy exactly as written, including punctuation.
- Names: copy exactly as written, keeping accents and capitalization.
Answer only with the requested JSON.
"""

KIND_LABEL = {
    "rental": "residential lease agreement (contrato de locação)",
    "service": "service agreement (contrato de prestação de serviços)",
}
