"""Irsaliye metninden alan cikarimi.

Bir dosya = bir irsaliye oldugu icin belge sinir tespiti gerekmez. Her dosya
icin PVS kodu, belge numarasi ve sevk adresi cikarilir. Zorunlu alanlardan
biri okunamazsa belge `errors` ile isaretlenir ve "tahmin yapma" ilkesi geregi
hicbir bolgeye zorlanmadan Hata ciktisina yonlendirilir.

Regex desenleri ve adres etiketleri gercek vardiya PDF'i ile kalibre edilmek
uzere burada toplanmistir (PATTERNS / ADDRESS_LABELS).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# --- Kalibre edilebilir desenler -------------------------------------------
# PVS kodu, orn: PVS2026000123
PVS_RE = re.compile(r"PVS\d{4}\S*", re.IGNORECASE)
# Belge numarasi, orn: 0700000456
BELGE_RE = re.compile(r"0700\d+")
# Sevk adresinin onundeki etiketler (normalize edilerek aranir).
ADDRESS_LABELS = ["SEVK ADRESI", "SEVK ADRES", "TESLIMAT ADRESI", "SEVK", "ADRES"]
# Etiket bulunduktan sonra adres olarak alinacak ek satir sayisi.
ADDRESS_EXTRA_LINES = 2


@dataclass
class Document:
    """Tek bir irsaliye PDF'inin cozumlenmis hali."""

    path: str
    text: str = ""
    pvs: Optional[str] = None
    belge_no: Optional[str] = None
    address: Optional[str] = None
    region: Optional[str] = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _fold(s: str) -> str:
    """Etiket karsilastirmasi icin Turkce-duyarsiz sade kucuk harf."""
    from .regions import normalize

    return normalize(s)


def extract_address(text: str, labels: list[str] | None = None) -> Optional[str]:
    """Etiketli sevk adresi blogunu dondurur; bulunamazsa None."""
    labels = labels if labels is not None else ADDRESS_LABELS
    folded_labels = [_fold(lbl) for lbl in labels]
    lines = [ln.strip() for ln in text.splitlines()]
    for i, line in enumerate(lines):
        fline = _fold(line)
        for raw_label, flabel in zip(labels, folded_labels):
            pos = fline.find(flabel)
            if pos == -1:
                continue
            # Etiketten sonra ayni satirda kalan kisim + sonraki satirlar.
            rest = line[pos + len(raw_label):].lstrip(" :\t-")
            block = [rest] + lines[i + 1 : i + 1 + ADDRESS_EXTRA_LINES]
            address = " ".join(p for p in block if p).strip()
            return address or None
    return None


def parse_document(path: str, text: str) -> Document:
    """Metinden bir Document olusturur; zorunlu alan eksikse hata ekler."""
    doc = Document(path=path, text=text)

    if not text:
        doc.errors.append("adres okunamadı")  # bos metin = okunamayan PDF
        return doc

    pvs_match = PVS_RE.search(text)
    doc.pvs = pvs_match.group(0) if pvs_match else None
    if not doc.pvs:
        doc.errors.append("PVS kodu bulunamadı")

    belge_match = BELGE_RE.search(text)
    doc.belge_no = belge_match.group(0) if belge_match else None
    if not doc.belge_no:
        doc.errors.append("belge numarası bulunamadı")

    doc.address = extract_address(text)
    if not doc.address:
        doc.errors.append("adres okunamadı")

    return doc
