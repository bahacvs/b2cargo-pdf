"""Teshis araci: gercek PDF'lerin yapisini gormek icin.

workdir/Gelen_PDF icindeki PDF'leri okur, her biri icin programin BULDUGU
adresi ve tespit ettigi bolgeyi yazar; ayrica ILK PDF'in tam metnini dokar.
Cikti teshis.txt dosyasina yazilir. Bu dosya kalibrasyon icin gelistiriciye
gonderilir.

NOT: Tam metin gercek sevk adreslerini icerir. Gondermeden once goz atip
gerekirse musteri adlarini karartabilirsin; ama PVS / belge no / "Sevk Adresi"
gibi ETIKETLERIN yapisini gormem kalibrasyon icin sart.
"""

from __future__ import annotations

import glob
from pathlib import Path

from perfetti_splitter.extractor import extract_text
from perfetti_splitter.parser import extract_address
from perfetti_splitter.regions import RegionMap

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "regions.yaml"
GELEN = ROOT / "workdir" / "Gelen_PDF"

# Tam metni dokulecek PDF sayisi (yapiyi gormek icin ilk birkac yeterli).
FULL_TEXT_COUNT = 2
# Adres/bolge ozetinin gosterilecegi PDF sayisi.
SUMMARY_COUNT = 15


def main() -> None:
    region_map = RegionMap.from_yaml(CONFIG)
    files = sorted(glob.glob(str(GELEN / "*.pdf")))

    out: list[str] = []
    out.append(f"workdir/Gelen_PDF icinde {len(files)} PDF bulundu.")
    out.append("")

    if not files:
        out.append("UYARI: Klasor bos. Irsaliye PDF'lerini workdir/Gelen_PDF")
        out.append("icine koyup tekrar calistirin.")
        _write(out)
        return

    out.append("=" * 64)
    out.append("PROGRAMIN BULDUGU ADRES VE TESPIT ETTIGI BOLGE")
    out.append("=" * 64)
    for f in files[:SUMMARY_COUNT]:
        text = extract_text(f)
        addr = extract_address(text)
        region, err = region_map.detect(addr)
        sonuc = region if region else f"HATA: {err}"
        out.append(f"- {Path(f).name}")
        out.append(f"    bulunan adres : {addr!r}")
        out.append(f"    tespit        : {sonuc}")

    out.append("")
    out.append("#" * 64)
    out.append(f"ILK {FULL_TEXT_COUNT} PDF'IN TAM METNI (yapiyi gormem icin)")
    out.append("#" * 64)
    for f in files[:FULL_TEXT_COUNT]:
        out.append("")
        out.append(f">>>>> {Path(f).name} <<<<<")
        out.append("-" * 64)
        out.append(extract_text(f))
        out.append("-" * 64)

    _write(out)


def _write(lines: list[str]) -> None:
    report = "\n".join(lines)
    (ROOT / "teshis.txt").write_text(report, encoding="utf-8")
    print(report)
    print("\n>>> teshis.txt olusturuldu.")


if __name__ == "__main__":
    main()
