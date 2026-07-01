"""Test yardimcilari: gercek e-Irsaliye yapisini taklit eden sentetik PDF'ler.

Gercek PDF'te UC adres bulunur ve sadece SEVK ADRESI kullanilmalidir:
  1. Gonderici (ust)   : ... Esenyurt/Istanbul   <- Aytop "tuzagi"
  2. SEVK ADRESI       : ... Ilce/Il/Turkiye     <- DOGRU adres
  3. FATURA ADRESI     : ... Istanbul/TR         <- Aytop "tuzagi"
Bu fixture ayni tuzaklari icerir; boylece program yanlislikla gonderici/fatura
adresini (Istanbul=Aytop) okursa testler kirilir.

Not: reportlab standart fontu bazi Turkce harfleri (orn. İ) tasiyamadigi icin
fixture metni ASCII'dir; gercek Turkce karakterlerin normalizasyonu test_regions
icinde ayrica test edilir.
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
    il: str = "ADANA",
    ilce: str = "Merkez",
    recipient: str | None = None,
    addr_tail: str | None = None,
    vergi_dairesi: str = "BESIKTAS",
    koli: int | None = 10,
    brut_agirlik: str | None = "100 kg",
    pages: int = 1,
    include_sevk: bool = True,
) -> Path:
    """Tek bir irsaliye PDF'i (1+ sayfa) uretir.

    il          : varsayilan hedef il (recipient/addr_tail verilmezse kullanilir).
    recipient   : SEVK alici adi satiri (sehir genelde burada). Vars: 'A101 {il}'.
    addr_tail   : SEVK 'Adres:' satirinin sonu. Vars: '7 {ilce}/{il}/Turkiye'.
                  Gercek hayatta bazen sadece ILCE icerir (orn.
                  '6515 SULUCA MH./SARICAM/Turkiye') ve il yalnizca recipient'tedir.
    vergi_dairesi: alicinin vergi dairesi sehri; teslimat ilinden FARKLI olabilir,
                  bolge tespitine karismamali.
    brut_agirlik: Toplam Brut Agirlik satiri; None ise yazilmaz.
    include_sevk=False ise SEVK blogu hic yazilmaz (adres okunamadi senaryosu).
    """
    recipient = recipient if recipient is not None else f"A101 {il}"
    addr_tail = addr_tail if addr_tail is not None else f"7 {ilce}/{il}/Turkiye"
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    for page_no in range(pages):
        lines = [
            "PERFETTI VAN MELLE GIDA SAN.VE.TIC.A.S",
            "Adres: Osmangazi Mah. No:15 Esenyurt/Istanbul",   # gonderici (tuzak)
            "Vergi Dairesi: Buyuk Mukellefler VKN: 7280036774",
        ]
        if include_sevk:
            lines += [
                f"SEVK ADRESI Irsaliye No: {pvs or ''}",
                recipient,                                       # alici adi (sehir burada)
                "Ozellestirme No : TR1.2.1",
                "Adres: KORU MAH. SUKRU ALBAYRAK CAD.",
                addr_tail,                                       # bazen sadece ilce
                f"Vergi Dairesi: {vergi_dairesi}",               # farkli sehir olabilir
                "Irsaliye Tipi : SEVK",
            ]
        if belge_no:
            lines.append(f"Belge No : {belge_no}")
        if koli is not None:
            lines.append(f"Toplam Miktar: 100 - Toplam Koli: {koli}")
        if brut_agirlik is not None:
            lines.append(f"Toplam Brut Agirlik: {brut_agirlik}")
        lines += [
            "FATURA ADRESI",
            "A101 YENI MAGAZACILIK A.S.",
            "Adres: Burhaniye Mah. No: 4 Istanbul/TR",          # fatura (tuzak)
            f"(sayfa {page_no + 1}/{pages})",
        ]

        c.setFont("Helvetica", 10)
        y = height - 60
        for line in lines:
            c.drawString(50, y, line)
            y -= 18
        c.showPage()
    c.save()
    return path


@pytest.fixture
def make_pdf():
    return make_irsaliye_pdf
