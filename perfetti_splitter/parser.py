"""Irsaliye metninden alan cikarimi.

Bir dosya = bir irsaliye oldugu icin belge sinir tespiti gerekmez. Her dosya
icin PVS kodu, belge numarasi ve SEVK (teslimat) adresi cikarilir. Zorunlu
alanlardan biri okunamazsa belge `errors` ile isaretlenir ve "tahmin yapma"
ilkesi geregi hicbir bolgeye zorlanmadan Hata ciktisina yonlendirilir.

Adres tespiti (gercek e-Irsaliye yapisina gore kalibre edildi):
Bir belgede UC adres bulunur:
  1. Ust kisim   : PERFETTI VAN MELLE'nin kendi adresi  (... Esenyurt/Istanbul)
  2. SEVK ADRESI : asil teslimat adresi  (... Ilce/Il/Turkiye)   <-- KULLANILAN
  3. FATURA ADRESI: fatura adresi          (... Il/TR)
Yalnizca SEVK ADRESI altindaki "Adres:" blogu kullanilir. Buradaki hedef il,
"Ilce/Il/Turkiye" kalibiyla okunur. (Fatura adresi /TR ile bittigi icin bu
kalibla karismaz; gonderici adresi ise SEVK ADRESI'nden once oldugu icin
blok disinda kalir.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# --- Kalibre edilebilir desenler -------------------------------------------
# PVS kodu, orn: PVS2026000029860
PVS_RE = re.compile(r"PVS\d{4}\S*", re.IGNORECASE)
# Belge numarasi, orn: 0700468911
BELGE_RE = re.compile(r"0700\d+")
# Adres bloklarinin etiketleri.
SEVK_LABEL_RE = re.compile(r"SEVK\s*ADRES[İI]", re.IGNORECASE)
FATURA_LABEL_RE = re.compile(r"FATURA\s*ADRES[İI]", re.IGNORECASE)
# Hedef adresin sonundaki  Ilce/Il/Turkiye  kalibi -> il = son slash'tan onceki.
# (Fatura adresi /TR ile bittiginden bu kalibla eslesmez.)
DEST_PROVINCE_RE = re.compile(r"([^/\n]+)/\s*t[uü]rk[iİ]ye", re.IGNORECASE)


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


def sevk_block(text: str) -> Optional[str]:
    """SEVK ADRESI ile FATURA ADRESI arasindaki metin blogu; yoksa None."""
    m = SEVK_LABEL_RE.search(text)
    if not m:
        return None
    fatura = FATURA_LABEL_RE.search(text, m.end())
    end = fatura.start() if fatura else len(text)
    return text[m.end():end]


def extract_destination(text: str) -> Optional[str]:
    """SEVK adresindeki hedef il'i dondurur (orn. 'TRABZON'); bulunamazsa None.

    Once SEVK blogundaki 'Ilce/Il/Turkiye' kalibi denenir. Kalip yoksa,
    sehir taramasi yapilabilsin diye SEVK blogunun ham metni dondurulur.
    """
    block = sevk_block(text)
    if block is None:
        return None
    m = DEST_PROVINCE_RE.search(block)
    if m:
        return m.group(1).strip()
    cleaned = block.strip()
    return cleaned or None


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

    doc.address = extract_destination(text)
    if not doc.address:
        doc.errors.append("adres okunamadı")

    return doc
