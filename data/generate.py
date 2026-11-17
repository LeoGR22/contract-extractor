from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from faker import Faker
from num2words import num2words
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

DESCRIPTION = "Gera contratos sintéticos (PDF) com gabarito."
ROOT = Path(__file__).parent
OUT_DIR = ROOT / "contracts"
GT_FILE = ROOT / "ground_truth.jsonl"

MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

GUARANTEES = {
    "deposit": "caução no valor equivalente a 3 (três) aluguéis, depositada em conta poupança",
    "guarantor": "fiança prestada por {guarantor}, que assina o presente na qualidade de FIADOR",
    "insurance": "seguro-fiança contratado pelo LOCATÁRIO junto a seguradora de sua escolha",
}

SERVICES = [
    ("desenvolvimento de um aplicativo mobile para agendamento de consultas, incluindo "
     "versões Android e iOS e painel administrativo web", ["aplicativo", "agendamento"]),
    ("consultoria contábil e fiscal mensal, incluindo apuração de tributos e entrega de "
     "obrigações acessórias", ["contabil", "fiscal"]),
    ("manutenção preventiva e corretiva dos aparelhos de ar-condicionado instalados na "
     "sede da CONTRATANTE", ["manutencao", "ar-condicionado"]),
    ("criação de identidade visual, incluindo logotipo, paleta de cores e manual da marca",
     ["identidade visual", "logotipo"]),
    ("limpeza e conservação das áreas comuns do edifício, com equipe de duas pessoas em "
     "dias úteis", ["limpeza"]),
    ("treinamento em análise de dados com Python para a equipe comercial da CONTRATANTE, "
     "com carga horária de 40 horas", ["treinamento", "python"]),
]

PAYMENT_TERMS = [
    ("em {n} parcelas mensais e iguais, mediante boleto bancário", ["{n}", "parcela"]),
    ("à vista, via PIX, em até 5 (cinco) dias após a assinatura deste contrato", ["vista", "pix"]),
    ("50% (cinquenta por cento) na assinatura e 50% (cinquenta por cento) na entrega final",
     ["50%", "entrega"]),
]


@dataclass
class Generated:
    doc_id: str
    contract_type: str
    paragraphs: list[tuple[str, str]]
    label: dict | None


def brl(value: float) -> str:
    s = f"{value:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def brl_with_words(value: float) -> str:
    words = num2words(int(value), lang="pt_BR")
    return f"{brl(value)} ({words} reais)"


def long_date(d: date) -> str:
    return f"{d.day} de {MONTHS[d.month - 1]} de {d.year}"


def short_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def address(fake: Faker) -> str:
    cep = fake.postcode(formatted=False)
    return (
        f"{fake.street_name()}, nº {fake.building_number()}, {fake.bairro()}, "
        f"{fake.city()} - {fake.estado_sigla()}, CEP {cep[:5]}-{cep[5:]}"
    )


def person(fake: Faker) -> dict:
    return {"name": f"{fake.first_name()} {fake.last_name()}", "document": fake.cpf()}


COMPANY_SEGMENTS = ["Tecnologia", "Serviços", "Consultoria", "Engenharia", "Soluções", "Comércio"]


def company(fake: Faker) -> dict:
    segment = fake.random_element(COMPANY_SEGMENTS)
    suffix = fake.random_element(["Ltda.", "S.A.", "ME", "EIRELI"])
    last = fake.last_name()
    return {"name": f"{last[0].upper()}{last[1:]} {segment} {suffix}", "document": fake.cnpj()}


def random_date(rng: random.Random) -> date:
    return date(2025, 1, 1) + timedelta(days=rng.randint(0, 600))


def rental(fake: Faker, rng: random.Random, doc_id: str) -> Generated:
    landlord, tenant = person(fake), person(fake)
    prop = address(fake)
    rent = float(rng.randrange(900, 8000, 50))
    due_day = rng.choice([5, 10, 15, 20])
    start = random_date(rng)
    term = rng.choice([12, 24, 30, 36])
    index = rng.choice(["IGP-M", "IPCA", "INPC"])
    guarantee = rng.choice(["deposit", "guarantor", "insurance", "none"])
    penalty = rng.choice([2.0, 3.0])
    city = fake.city()
    template = rng.choice(["A", "B"])

    if guarantee == "none":
        guarantee_text = "Fica dispensada a apresentação de garantia locatícia, nos termos do art. 42 da Lei nº 8.245/91."
    else:
        guarantee_text = "Em garantia das obrigações assumidas, o LOCATÁRIO oferece " + GUARANTEES[guarantee].format(
            guarantor=fake.name()
        ) + "."

    if template == "A":
        paragraphs = [
            ("title", "CONTRATO DE LOCAÇÃO RESIDENCIAL"),
            ("body", f"<b>LOCADOR:</b> {landlord['name']}, brasileiro(a), inscrito(a) no CPF sob o nº {landlord['document']}, residente em {address(fake)}."),
            ("body", f"<b>LOCATÁRIO:</b> {tenant['name']}, brasileiro(a), inscrito(a) no CPF sob o nº {tenant['document']}."),
            ("body", "As partes acima identificadas têm entre si justo e contratado o seguinte:"),
            ("body", f"<b>CLÁUSULA 1ª – DO OBJETO.</b> O LOCADOR dá em locação ao LOCATÁRIO o imóvel residencial situado na {prop}."),
            ("body", f"<b>CLÁUSULA 2ª – DO PRAZO.</b> A locação terá prazo de {term} meses, iniciando-se em {short_date(start)}."),
            ("body", f"<b>CLÁUSULA 3ª – DO ALUGUEL.</b> O aluguel mensal é de {brl(rent)}, a ser pago até o dia {due_day} de cada mês."),
            ("body", f"<b>CLÁUSULA 4ª – DO REAJUSTE.</b> O aluguel será reajustado anualmente pela variação do {index}."),
            ("body", f"<b>CLÁUSULA 5ª – DA GARANTIA.</b> {guarantee_text}"),
            ("body", f"<b>CLÁUSULA 6ª – DA RESCISÃO.</b> A rescisão antecipada pelo LOCATÁRIO implicará multa equivalente a {int(penalty)} aluguéis vigentes, proporcional ao tempo restante."),
            ("body", f"<b>CLÁUSULA 7ª – DO FORO.</b> Fica eleito o foro da comarca de {city}."),
        ]
    else:
        paragraphs = [
            ("title", "INSTRUMENTO PARTICULAR DE CONTRATO DE LOCAÇÃO DE IMÓVEL"),
            ("body", f"Pelo presente instrumento particular, de um lado {landlord['name'].upper()}, CPF {landlord['document']}, doravante denominado(a) LOCADORA, e de outro lado {tenant['name'].upper()}, CPF {tenant['document']}, doravante denominado(a) LOCATÁRIA, celebram o presente contrato, que se regerá pela Lei nº 8.245/91 e pelas cláusulas seguintes."),
            ("body", f"Primeira. O imóvel objeto desta locação localiza-se na {prop} e destina-se exclusivamente a fins residenciais."),
            ("body", f"Segunda. O valor do aluguel é de {brl_with_words(rent)} mensais, com vencimento todo dia {due_day}, corrigido a cada doze meses pelo índice {index}."),
            ("body", f"Terceira. O prazo da locação é de {term} ({num2words(term, lang='pt_BR')}) meses, contados a partir de {long_date(start)}."),
            ("body", f"Quarta. {guarantee_text}"),
            ("body", f"Quinta. Em caso de devolução do imóvel antes do término do prazo, a LOCATÁRIA pagará multa correspondente a {int(penalty)} ({num2words(int(penalty), lang='pt_BR')}) meses de aluguel, reduzida proporcionalmente."),
            ("body", "Sexta. Correrão por conta da LOCATÁRIA as despesas de consumo de água, energia elétrica e gás."),
            ("body", f"E por estarem assim justas e contratadas, assinam o presente em duas vias. {city}, {long_date(start - timedelta(days=rng.randint(3, 20)))}."),
        ]

    paragraphs += [("sign", "______________________________<br/>LOCADOR(A)"), ("sign", "______________________________<br/>LOCATÁRIO(A)")]

    label = {
        "landlord": landlord,
        "tenant": tenant,
        "property_address": prop,
        "monthly_rent": rent,
        "due_day": due_day,
        "start_date": start.isoformat(),
        "term_months": term,
        "adjustment_index": index,
        "guarantee_type": guarantee,
        "termination_penalty_months": penalty,
    }
    return Generated(doc_id, "rental", paragraphs, label)


def service(fake: Faker, rng: random.Random, doc_id: str) -> Generated:
    client, provider = company(fake), company(fake)
    if rng.random() < 0.3:
        client = person(fake)
    scope_text, scope_keywords = rng.choice(SERVICES)
    total = float(rng.randrange(3000, 120000, 500))
    n = rng.choice([2, 3, 4, 6, 10, 12])
    terms_text, terms_keywords = rng.choice(PAYMENT_TERMS)
    terms_text = terms_text.format(n=n)
    terms_keywords = [k.format(n=n) for k in terms_keywords]
    start = random_date(rng)
    end = start + timedelta(days=rng.choice([30, 60, 90, 180, 365]))
    jurisdiction = fake.city()
    uf = fake.estado_sigla()
    template = rng.choice(["A", "B"])

    if template == "A":
        paragraphs = [
            ("title", "CONTRATO DE PRESTAÇÃO DE SERVIÇOS"),
            ("body", f"<b>CONTRATANTE:</b> {client['name']}, inscrita sob o nº {client['document']}, com sede em {address(fake)}."),
            ("body", f"<b>CONTRATADA:</b> {provider['name']}, CNPJ {provider['document']}, com sede em {address(fake)}."),
            ("body", f"<b>1. OBJETO.</b> O presente contrato tem por objeto a prestação, pela CONTRATADA, de serviços de {scope_text}."),
            ("body", f"<b>2. VIGÊNCIA.</b> Este contrato vigora de {short_date(start)} a {short_date(end)}."),
            ("body", f"<b>3. PREÇO.</b> Pelos serviços, a CONTRATANTE pagará o valor total de {brl(total)}, {terms_text}."),
            ("body", "<b>4. OBRIGAÇÕES.</b> A CONTRATADA executará os serviços com zelo e diligência, observando as normas técnicas aplicáveis."),
            ("body", "<b>5. RESCISÃO.</b> Qualquer das partes poderá rescindir este contrato mediante aviso prévio de 30 dias."),
            ("body", f"<b>6. FORO.</b> As partes elegem o foro da comarca de {jurisdiction}/{uf} para dirimir quaisquer dúvidas."),
        ]
    else:
        paragraphs = [
            ("title", "CONTRATO PARTICULAR DE PRESTAÇÃO DE SERVIÇOS PROFISSIONAIS"),
            ("body", f"São partes neste instrumento: (i) {client['name']}, documento {client['document']}, adiante CONTRATANTE; e (ii) {provider['name']}, inscrita no CNPJ/MF sob o nº {provider['document']}, adiante CONTRATADA."),
            ("body", "Cláusula Primeira – As partes declaram que o presente contrato não gera vínculo empregatício de qualquer natureza."),
            ("body", f"Cláusula Segunda – A CONTRATADA obriga-se a realizar {scope_text}, conforme proposta comercial anexa."),
            ("body", f"Cláusula Terceira – Como contraprestação, será pago o montante de {brl_with_words(total)}, {terms_text}."),
            ("body", f"Cláusula Quarta – Os serviços terão início em {long_date(start)} e deverão ser concluídos até {long_date(end)}."),
            ("body", f"Cláusula Quinta – Fica eleito o foro de {jurisdiction}, Estado de {uf}, com renúncia a qualquer outro."),
        ]

    paragraphs += [("sign", "______________________________<br/>CONTRATANTE"), ("sign", "______________________________<br/>CONTRATADA")]

    label = {
        "client": client,
        "provider": provider,
        "scope": scope_text,
        "total_value": total,
        "payment_terms": terms_text,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "jurisdiction": jurisdiction,
        "_keywords": {"scope": scope_keywords, "payment_terms": terms_keywords},
    }
    return Generated(doc_id, "service", paragraphs, label)


def other(fake: Faker, rng: random.Random, doc_id: str) -> Generated:
    name = fake.name()
    kind = rng.choice(["procuracao", "declaracao"])
    if kind == "procuracao":
        paragraphs = [
            ("title", "PROCURAÇÃO"),
            ("body", f"OUTORGANTE: {name}, CPF {fake.cpf()}. OUTORGADO: {fake.name()}, CPF {fake.cpf()}."),
            ("body", "PODERES: para representar o outorgante perante repartições públicas federais, estaduais e municipais, podendo requerer, assinar e retirar documentos."),
            ("body", f"{fake.city()}, {long_date(random_date(rng))}."),
        ]
    else:
        paragraphs = [
            ("title", "DECLARAÇÃO DE RESIDÊNCIA"),
            ("body", f"Eu, {name}, CPF {fake.cpf()}, declaro para os devidos fins que resido no endereço {address(fake)}."),
            ("body", "Declaro ainda estar ciente de que a falsidade desta declaração configura crime previsto no Código Penal."),
            ("body", f"{fake.city()}, {long_date(random_date(rng))}."),
        ]
    paragraphs.append(("sign", f"______________________________<br/>{name}"))
    return Generated(doc_id, "other", paragraphs, None)


def render_pdf(gen: Generated, path: Path) -> None:
    styles = getSampleStyleSheet()
    style_map = {
        "title": ParagraphStyle("t", parent=styles["Title"], fontSize=14, spaceAfter=18),
        "body": ParagraphStyle("b", parent=styles["BodyText"], fontSize=10.5, leading=15,
                               alignment=TA_JUSTIFY, spaceAfter=8),
        "sign": ParagraphStyle("s", parent=styles["BodyText"], alignment=TA_CENTER, spaceBefore=28),
    }
    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                            topMargin=2.5 * cm, bottomMargin=2.5 * cm, title=gen.doc_id)
    story = []
    for style, text in gen.paragraphs:
        story.append(Paragraph(text, style_map[style]))
    story.append(Spacer(1, 12))
    doc.build(story)


def main() -> None:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--rental", type=int, default=15)
    parser.add_argument("--service", type=int, default=15)
    parser.add_argument("--other", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    fake = Faker("pt_BR")
    Faker.seed(args.seed)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.pdf"):
        old.unlink()

    plan = [("rental", rental, args.rental), ("service", service, args.service), ("other", other, args.other)]
    with GT_FILE.open("w", encoding="utf-8") as gt:
        for prefix, fn, count in plan:
            for i in range(1, count + 1):
                gen = fn(fake, rng, f"{prefix}_{i:03d}")
                render_pdf(gen, OUT_DIR / f"{gen.doc_id}.pdf")
                gt.write(json.dumps({
                    "id": gen.doc_id,
                    "file": f"contracts/{gen.doc_id}.pdf",
                    "contract_type": gen.contract_type,
                    "label": gen.label,
                }, ensure_ascii=False) + "\n")

    total = args.rental + args.service + args.other
    print(f"Generated {total} contracts in {OUT_DIR} and labels in {GT_FILE}")


if __name__ == "__main__":
    main()
