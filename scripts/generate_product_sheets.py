from __future__ import annotations

import ast
import re
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "index.html"
OUTPUT = ROOT / "assets" / "specs"


def extract_products() -> list[dict]:
    source = HTML.read_text(encoding="utf-8")
    block = re.search(
        r"const PRODUCTS = \[(.*?)\];\s*const CATEGORIES",
        source,
        re.S,
    )
    if not block:
        raise RuntimeError("PRODUCTS block not found")

    products = []
    pattern = re.compile(
        r"\{id:'(?P<id>[^']+)',\s*category:'(?P<category>[^']+)',"
        r"\s*brand:'(?P<brand>[^']+)',\s*model:'(?P<model>[^']+)',"
        r"\s*specs:(?P<specs>\[[^\]]+\]),\s*pack:'(?P<pack>[^']+)'"
    )
    for match in pattern.finditer(block.group(1)):
        data = match.groupdict()
        data["specs"] = ast.literal_eval(data["specs"])
        products.append(data)
    if len(products) != 26:
        raise RuntimeError(f"Expected 26 products, extracted {len(products)}")
    return products


def register_fonts() -> tuple[str, str]:
    regular_candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    bold_candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
    ]
    regular = next((p for p in regular_candidates if p.exists()), None)
    bold = next((p for p in bold_candidates if p.exists()), None)
    if regular and bold:
        pdfmetrics.registerFont(TTFont("WexmorRegular", str(regular)))
        pdfmetrics.registerFont(TTFont("WexmorBold", str(bold)))
        return "WexmorRegular", "WexmorBold"
    return "Helvetica", "Helvetica-Bold"


REGULAR, BOLD = register_fonts()
AMBER = HexColor("#F59E0B")
BLACK = HexColor("#050505")
CARD = HexColor("#171719")
MUTED = HexColor("#A3A3A3")
BORDER = HexColor("#333337")


def background(canvas, doc):
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(BLACK)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(AMBER)
    canvas.rect(0, height - 7 * mm, width, 7 * mm, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#777777"))
    canvas.setFont(REGULAR, 8)
    canvas.drawString(18 * mm, 12 * mm, "WEXMOR ENERGY · FICHA TÉCNICA COMERCIAL")
    canvas.drawRightString(width - 18 * mm, 12 * mm, "sales@wexmorenergy.com · +1 561 312 2929")
    canvas.restoreState()


def build_sheet(product: dict):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"{product['id']}.pdf"
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=23 * mm,
        bottomMargin=22 * mm,
        title=f"{product['brand']} {product['model']} - Wexmor Energy",
        author="Wexmor Energy",
    )

    eyebrow = ParagraphStyle(
        "eyebrow",
        fontName=BOLD,
        fontSize=9,
        leading=12,
        textColor=AMBER,
        spaceAfter=5 * mm,
    )
    title = ParagraphStyle(
        "title",
        fontName=BOLD,
        fontSize=28,
        leading=32,
        textColor=white,
        spaceAfter=3 * mm,
    )
    subtitle = ParagraphStyle(
        "subtitle",
        fontName=REGULAR,
        fontSize=12,
        leading=18,
        textColor=MUTED,
        spaceAfter=9 * mm,
    )
    heading = ParagraphStyle(
        "heading",
        fontName=BOLD,
        fontSize=12,
        leading=16,
        textColor=white,
        spaceAfter=3 * mm,
    )
    body = ParagraphStyle(
        "body",
        fontName=REGULAR,
        fontSize=10,
        leading=16,
        textColor=MUTED,
    )
    body_white = ParagraphStyle(
        "body_white",
        parent=body,
        textColor=white,
    )

    category_names = {
        "panels": "MÓDULOS FOTOVOLTAICOS",
        "inverters": "INVERSORES",
        "batteries": "ALMACENAMIENTO",
        "stations": "ESTACIONES DE ENERGÍA",
    }
    story = [
        Paragraph(f"{category_names[product['category']]} · {product['brand'].upper()}", eyebrow),
        Paragraph(product["model"], title),
        Paragraph(
            "Referencia disponible para propuestas mayoristas y configuración de contenedores. "
            "La versión eléctrica y disponibilidad se confirman en la cotización.",
            subtitle,
        ),
    ]

    rows = [[Paragraph("CARACTERÍSTICAS PRINCIPALES", heading), ""]]
    for spec in product["specs"]:
        rows.append(
            [
                Paragraph("●", ParagraphStyle("dot", parent=body, textColor=AMBER)),
                Paragraph(spec, body_white),
            ]
        )
    spec_table = Table(rows, colWidths=[12 * mm, 146 * mm], hAlign="LEFT")
    spec_table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("BACKGROUND", (0, 0), (-1, -1), CARD),
                ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("INNERGRID", (0, 1), (-1, -1), 0.3, BORDER),
                ("LEFTPADDING", (0, 0), (0, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (0, -1), 2 * mm),
                ("LEFTPADDING", (1, 0), (1, -1), 4 * mm),
                ("RIGHTPADDING", (1, 0), (1, -1), 7 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.extend([spec_table, Spacer(1, 8 * mm)])

    logistics = Table(
        [
            [Paragraph("REFERENCIA LOGÍSTICA", heading)],
            [Paragraph(product["pack"], ParagraphStyle("logistics", parent=body_white, fontSize=14, leading=20))],
            [
                Paragraph(
                    "Esta cantidad es una referencia inicial para que el comprador prepare su solicitud. "
                    "Las unidades reales por pallet deben confirmarse según revisión exacta del producto, "
                    "embalaje de fábrica, peso, origen y naviera.",
                    body,
                )
            ],
        ],
        colWidths=[158 * mm],
    )
    logistics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#211B0F")),
                ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    story.extend([logistics, Spacer(1, 8 * mm)])

    note_text = (
        "TRANSPORTE DE LITIO: este producto requiere validación de documentación, "
        "clasificación, embalaje y aceptación de la naviera."
        if product["category"] in {"batteries", "stations"}
        else "La potencia, tensión, conectividad y accesorios deben validarse para el mercado de destino."
    )
    story.append(
        KeepTogether(
            [
                Paragraph("NOTAS DE COTIZACIÓN", heading),
                Paragraph(note_text, body),
                Spacer(1, 4 * mm),
                Paragraph(
                    "Documento informativo preparado por Wexmor Energy. No constituye una ficha de "
                    "embalaje definitiva, oferta vinculante ni confirmación de inventario. Sin precios.",
                    body,
                ),
            ]
        )
    )
    doc.build(story, onFirstPage=background, onLaterPages=background)
    return path


def main():
    paths = [build_sheet(product) for product in extract_products()]
    print(f"Generated {len(paths)} PDF sheets in {OUTPUT}")


if __name__ == "__main__":
    main()
