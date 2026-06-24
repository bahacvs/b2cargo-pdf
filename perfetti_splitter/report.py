"""Vardiya ozeti ve hata raporu uretimi."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import Document


def write_error_report(error_docs: list["Document"], out_path: str | Path) -> str:
    """Hatali belgeleri CSV olarak yazar: dosya, pvs, belge_no, bulunan_adres, neden.

    `bulunan_adres` programin SEVK adresinden okudugu metindir; "bölge
    bulunamadı" gibi hatalarin nedenini PDF acmadan gormeyi saglar.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["dosya", "pvs", "belge_no", "bulunan_adres", "neden"])
        for doc in error_docs:
            writer.writerow(
                [
                    Path(doc.path).name,
                    doc.pvs or "",
                    doc.belge_no or "",
                    doc.address or "",
                    "; ".join(doc.errors),
                ]
            )
    return str(out_path)


def format_summary(
    region_counts: dict[str, int], error_count: int, dsv_count: int = 0
) -> str:
    """Insan-okur ozet metni uretir (B2 bolgeleri + DSV + Hata)."""
    lines = ["=== Vardiya Ozeti ==="]
    total = 0
    lines.append("  B2:")
    for region in sorted(region_counts):
        n = region_counts[region]
        total += n
        lines.append(f"    {region:<10} {n} evrak")
    if dsv_count:
        total += dsv_count
        lines.append(f"  {'DSV':<12} {dsv_count} evrak")
    lines.append(f"  {'Hata':<12} {error_count} evrak")
    lines.append(f"  {'-' * 20}")
    lines.append(f"  {'TOPLAM':<12} {total + error_count} evrak")
    return "\n".join(lines)


def write_summary(text: str, out_path: str | Path) -> str:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    return str(out_path)
