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


# Adresin sonundaki "Ilce/Il/Turkiye" kalibindan il (son slash'tan onceki) cikar.
_PROVINCE_RE = re.compile(r"([^/\n]+)/\s*t[uü]rk[iİ]ye", re.IGNORECASE)


def _has_word(token: str, ntext: str) -> bool:
    """Normalize edilmis token, normalize metinde kelime butun olarak gecer mi?"""
    return bool(token) and re.search(r"\b" + re.escape(token) + r"\b", ntext) is not None


class DsvMatcher:
    """Bir irsaliyenin DSV'ye mi gidecegini belirler.

    İki kural:
      * iller   : teslimat ili (adresin .../Il/Türkiye kalibindaki il) bu kumede
                  ise DSV (orn. Istanbul komple).
      * noktalar: (ilce, anahtarlar) ciftleri. Teslimat ilcesi 'ilce' ile gecer
                  VE alici adinda 'anahtarlar'dan biri gecerse DSV. Boylece ayni
                  ilcedeki DSV-disi musteriler B2'de kalir.
    Eslestirme normalize (Turkce-duyarsiz) ve kelime-butun yapilir.
    """

    def __init__(self, iller: list[str], noktalar: list[dict] | None = None):
        self.iller = {normalize(x) for x in (iller or []) if normalize(x)}
        self.noktalar: list[tuple[str, list[str]]] = []
        for n in noktalar or []:
            ilce = normalize(n.get("ilce", ""))
            keys = [normalize(k) for k in n.get("anahtarlar", []) if normalize(k)]
            if ilce and keys:
                self.noktalar.append((ilce, keys))

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DsvMatcher":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if isinstance(data, list):  # eski biçim: düz il listesi
            return cls(iller=data, noktalar=[])
        return cls(iller=data.get("iller", []), noktalar=data.get("noktalar", []))

    def province(self, address: Optional[str]) -> str:
        """Adresteki teslimat ilini (normalize) dondurur; yoksa ''."""
        if not address:
            return ""
        m = _PROVINCE_RE.search(address)
        return normalize(m.group(1).strip()) if m else ""

    def matches(self, address: Optional[str]) -> bool:
        if not address:
            return False
        if self.province(address) in self.iller:  # il bazli komple (Istanbul)
            return True
        ntext = normalize(address)
        for ilce, keys in self.noktalar:  # ilce + isim eslesmesi
            if _has_word(ilce, ntext) and any(_has_word(k, ntext) for k in keys):
                return True
        return False
