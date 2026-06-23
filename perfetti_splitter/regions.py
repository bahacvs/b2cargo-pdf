"""Sevk adresinden bolge tespiti.

Turkce karakterler ASCII'ye katlanarak (i/I/ı/İ/ş/ğ/ç/ö/ü) buyuk-kucuk ve
aksan farklari yok edilir; ardindan il/ilce token'lari kelime siniriyla aranir.

"Tahmin yapma" ilkesi:
  * tam 1 bolge eslesirse  -> o bolge
  * 0 bolge eslesirse      -> hata ("bölge bulunamadı")
  * >1 farkli bolge        -> hata ("belirsiz/çakışma") - orn. Bilecik
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

# Turkce -> sade ASCII katlama tablosu (hem buyuk hem kucuk).
_TR_FOLD = str.maketrans(
    {
        "ç": "c", "Ç": "c",
        "ğ": "g", "Ğ": "g",
        "ı": "i", "İ": "i", "I": "i",
        "ö": "o", "Ö": "o",
        "ş": "s", "Ş": "s",
        "ü": "u", "Ü": "u",
        "â": "a", "Â": "a",
        "î": "i", "Î": "i",
        "û": "u", "Û": "u",
    }
)


def normalize(s: str) -> str:
    """Bolge eslestirmesi icin metni sade ASCII kucuk harfe cevirir."""
    if not s:
        return ""
    return s.translate(_TR_FOLD).lower()


# Eslestirmeden ONCE adresten temizlenecek gurultu ifadeleri.
# Kritik: firma adi "Perfetti Van Melle" icindeki "Van", Erzurum bolgesindeki
# Van ili ile cakisir ve her belgede yanlis eslesme yaratir. Bu yuzden firma
# adi adres metninden cikarilir. (Gercek PDF ile kalibre edilebilir.)
DEFAULT_IGNORE_PHRASES = ["Perfetti Van Melle"]


class RegionMap:
    """Bolge -> sehir haritasi ve adresten bolge tespiti."""

    def __init__(
        self,
        mapping: dict[str, list[str]],
        ignore_phrases: list[str] | None = None,
    ):
        self.mapping = mapping
        phrases = DEFAULT_IGNORE_PHRASES if ignore_phrases is None else ignore_phrases
        self.ignore_phrases = [normalize(p) for p in phrases if p]
        # token (normalize sehir) -> bu token'in ait oldugu bolgeler kumesi
        self.token_regions: dict[str, set[str]] = {}
        for region, cities in mapping.items():
            for city in cities or []:
                key = normalize(city)
                if key:
                    self.token_regions.setdefault(key, set()).add(region)
        # config seviyesinde birden cok bolgeye dusen sehirler (orn. Bilecik)
        self.conflicts = {
            t: rs for t, rs in self.token_regions.items() if len(rs) > 1
        }

    @classmethod
    def from_yaml(cls, path: str | Path) -> "RegionMap":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(data)

    def detect(self, address: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """(bolge, hata) dondurur. Basarili ise hata None'dir."""
        if not address:
            return None, "adres okunamadı"
        ntext = normalize(address)
        for phrase in self.ignore_phrases:  # firma adi vb. gurultuyu temizle
            ntext = ntext.replace(phrase, " ")
        found: set[str] = set()
        for token, regions in self.token_regions.items():
            if re.search(r"\b" + re.escape(token) + r"\b", ntext):
                found |= regions
        if not found:
            return None, "bölge bulunamadı"
        if len(found) > 1:
            return None, "belirsiz/çakışma: " + ", ".join(sorted(found))
        return next(iter(found)), None
