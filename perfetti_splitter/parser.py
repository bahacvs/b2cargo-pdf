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
Yalnizca SEVK ADRESI ile FATURA ADRESI arasindaki blok kullanilir; gonderici
(blok oncesi) ve fatura (blok sonrasi) adresleri haric tutulur. Bloktan meta
satirlari elenip alici adi + "Adres:" satiri birakilir ve sehir bu metnin
TAMAMINDA aranir. Boylece adres satirinda yalnizca ILCE yazsa bile (orn.
".../SARICAM/Türkiye") sehir, alici adindaki ILDEN (orn. "GRATIS - ADANA DEPO")
bulunur.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from dataclasses import dataclass, field
from typing import Optional

from .regions import normalize

# --- Kalibre edilebilir desenler -------------------------------------------
# PVS kodu, orn: PVS2026000029860
PVS_RE = re.compile(r"PVS\d{4}\S*", re.IGNORECASE)
# Belge numarasi, orn: 0700468911
BELGE_RE = re.compile(r"0700\d+")
# Toplam koli adedi, orn: "Toplam Koli: 24"
KOLI_RE = re.compile(r"Toplam\s*Koli\s*:?\s*(\d+)", re.IGNORECASE)
# Toplam brut agirlik, orn: "Toplam Brüt Ağırlık: 1.234,50 KG"
BRUT_AGIRLIK_RE = re.compile(
    r"toplam\s*brut\s*agirl(?:ik|igi)\s*:?\s*([0-9][0-9.,]*)\s*(kg|kilogram|g|gr|gram)?\b",
    re.IGNORECASE,
)
# Adres bloklarinin etiketleri.
SEVK_LABEL_RE = re.compile(r"SEVK\s*ADRES[İI]", re.IGNORECASE)
FATURA_LABEL_RE = re.compile(r"FATURA\s*ADRES[İI]", re.IGNORECASE)

# SEVK blogunda bolge tespitine YARDIMCI OLMAYAN meta/gurultu satirlari.
# Bu satirlar elenir; ozellikle "Vergi Dairesi" elenir cunku alicinin vergi
# dairesi sehri teslimat ilinden farkli olabilir (orn. BESIKTAS) ve yanlis
# cakisma yaratir. Karsilastirma Turkce-duyarsiz (normalize) yapilir.
_NOISE_PREFIXES = [
    normalize(p)
    for p in [
        "Özelleştirme", "Senaryo", "İrsaliye", "Vergi Dairesi", "VKN",
        "BAYINO", "Sevk Tarihi", "Sevk Zamanı", "Belge No", "ETTN", "Mühür",
        "Müşteri", "M.Sipariş", "Sipariş", "SAP", "Asıl Alıcı", "Taşıyıcı",
        "Toplam", "Araç", "Sayfa", "Ürün", "Mal Hizmet", "Not ", "Özelleştir",
    ]
]


@dataclass
class Document:
    """Tek bir irsaliye PDF'inin cozumlenmis hali."""

    path: str
    text: str = ""
    pvs: Optional[str] = None
    belge_no: Optional[str] = None
    address: Optional[str] = None
    recipient: Optional[str] = None
    koli: Optional[int] = None
    brut_agirlik: Optional[Decimal] = None
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


def _sevk_keep_lines(block: str) -> list[str]:
    """SEVK blogundan meta/gurultu satirlari elenmis anlamli satirlar."""
    keep: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            continue
        nlow = normalize(line)
        if any(nlow.startswith(prefix) for prefix in _NOISE_PREFIXES):
            continue
        keep.append(line)
    return keep


def _dedup_repeat(s: str) -> str:
    """Iki-kolon birlesmesinden gelen tekrari sadelestirir.

    'GRATIS - ADANA DEPO GRATIS - ADANA DEPO' -> 'GRATIS - ADANA DEPO'.
    Metin ortadaki bosluktan ikiye bolundugunde iki yari ayniysa tek yari
    dondurulur.
    """
    s = " ".join(s.split())  # bosluklari sadelestir
    n = len(s)
    if n >= 3 and n % 2 == 1:
        half = n // 2
        if s[:half] == s[half + 1:] and s[half] == " ":
            return s[:half]
    return s


def extract_destination(text: str) -> Optional[str]:
    """SEVK (teslimat) adresinin bolge tespitine yarayan satirlarini dondurur.

    SEVK blogundan meta/gurultu satirlari (_NOISE_PREFIXES) elenir; geriye
    alici adi (orn. 'GRATIS - ADANA DEPO') ve 'Adres:' satiri kalir. Sehir,
    adres satirinda yalnizca ilce yazsa bile (orn. '.../SARICAM/Türkiye')
    alici adindaki ilden (ADANA) bulunabilsin diye blok butun olarak
    `regions.detect()`'e verilir. Bulunamazsa None.
    """
    block = sevk_block(text)
    if block is None:
        return None
    cleaned = " ".join(_sevk_keep_lines(block)).strip()
    return cleaned or None


def extract_recipient(text: str) -> Optional[str]:
    """SEVK adresindeki alici adini dondurur (orn. 'A101 ADANA').

    'Adres:' satirindan ONCEKI anlamli satir(lar) alici adidir. Iki-kolon
    birlesmesinden gelen tekrar sadelestirilir. Bulunamazsa None.
    """
    block = sevk_block(text)
    if block is None:
        return None
    before_adres: list[str] = []
    for line in _sevk_keep_lines(block):
        if normalize(line).startswith("adres"):
            break
        before_adres.append(line)
    name = _dedup_repeat(" ".join(before_adres).strip())
    return name or None


def extract_koli(text: str) -> Optional[int]:
    """'Toplam Koli: N' degerini tamsayi olarak dondurur; bulunamazsa None."""
    m = KOLI_RE.search(text)
    return int(m.group(1)) if m else None


def _parse_decimal(value: str) -> Optional[Decimal]:
    raw = value.strip().replace(" ", "")
    if not raw:
        return None
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def extract_brut_agirlik(text: str) -> Optional[Decimal]:
    """'Toplam Brüt Ağırlık' degerini kg cinsinden Decimal dondurur."""
    m = BRUT_AGIRLIK_RE.search(normalize(text))
    if not m:
        return None
    value = _parse_decimal(m.group(1))
    if value is None:
        return None
    unit = m.group(2) or "kg"
    if unit in {"g", "gr", "gram"}:
        return value / Decimal("1000")
    return value

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

    doc.recipient = extract_recipient(text)
    doc.koli = extract_koli(text)
    doc.brut_agirlik = extract_brut_agirlik(text)

    return doc
