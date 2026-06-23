"""Test yardimcilari: sentetik irsaliye PDF'leri uretir (reportlab).

Gercek vardiya PDF'i henuz olmadigi icin testler kontrollu sentetik PDF'lerle
calisir. Gercek PDF gelince ayni testler gercek ornek uzerinde kalibre edilir.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def make_irsaliye_pdf(
    path: Path,
    pvs: str | None = "PVS2026000123",
    belge_no: str | None = "0700000456",
    address: str | None = "MIGROS ADANA BOLGE MERKEZ DEPOSU",
    pages: int = 1,
) -> Path:
    """Tek bir irsaliye PDF'i (1+ sayfa) uretir."""
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    for page_no in range(pages):
        y = height - 80
        c.setFont("Helvetica", 11)
        c.drawString(50, y, "PERFETTI VAN MELLE - E-IRSALIYE")
        y -= 30
        if pvs:
            c.drawString(50, y, f"PVS Kodu: {pvs}")
            y -= 20
        if belge_no:
            c.drawString(50, y, f"Belge No: {belge_no}")
            y -= 20
        if address:
            c.drawString(50, y, f"SEVK ADRESI: {address}")
            y -= 20
        c.drawString(50, y, f"(sayfa {page_no + 1}/{pages})")
        c.showPage()
    c.save()
    return path


@pytest.fixture
def make_pdf():
    return make_irsaliye_pdf
