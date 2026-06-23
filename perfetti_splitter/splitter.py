"""Bolge bazinda PDF birlestirme.

Ayni bolgeye atanan tum irsaliye PDF'leri (her biri 1+ sayfa) tek bir bolge
PDF'inde birlestirilir. Cikti dosya adi: ``{Bolge}_{adet}evrak.pdf``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pypdf import PdfReader, PdfWriter


def merge_pdfs(paths: Iterable[str], out_path: str | Path) -> int:
    """Verilen PDF'leri sirayla birlestirip out_path'e yazar. Sayfa sayisi doner."""
    writer = PdfWriter()
    for p in paths:
        reader = PdfReader(p)
        for page in reader.pages:
            writer.add_page(page)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        writer.write(f)
    return len(writer.pages)


def region_filename(region: str, count: int) -> str:
    """Bolge ciktisi icin dosya adi: 'Adana_24evrak.pdf'."""
    return f"{region}_{count}evrak.pdf"


def write_region_pdfs(
    grouped: dict[str, list[str]], out_dir: str | Path
) -> dict[str, str]:
    """grouped: bolge -> PDF yollari. Her bolge icin tek PDF yazar.

    Donen: bolge -> yazilan dosya yolu.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for region, paths in grouped.items():
        if not paths:
            continue
        fname = region_filename(region, len(paths))
        dest = out_dir / fname
        merge_pdfs(paths, dest)
        written[region] = str(dest)
    return written
