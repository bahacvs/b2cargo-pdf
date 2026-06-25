"""Vardiya ozeti ve rapor uretimi."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from .parser import Document


TargetInfo = tuple[str, str, str]
_LOCATION_RE = re.compile(r"([^/\n]+)/\s*t[uü]rk[iİ]ye", re.IGNORECASE)


def _terminal_location(address: str | None) -> str:
    if not address:
        return ""
    matches = _LOCATION_RE.findall(address)
    return matches[-1].strip() if matches else ""


def error_hint(errors: Iterable[str], address: str | None = None) -> tuple[str, str]:
    """Hata listesinden kisa neden ve kullaniciya donuk oneriyi dondurur."""
    joined = "; ".join(errors)
    text = joined.lower()
    if not joined:
        return "", ""
    if "pdf okunamad" in text:
        return "PDF okunamadı", "PDF dosyası bozuk/şifreli olabilir; dosyayı yeniden indirin veya açılıp açılmadığını kontrol edin."
    if "pvs kodu" in text:
        return "PVS kodu bulunamadı", "PDF üzerinde PVS numarası okunamıyor; belge formatını veya PDF kalitesini kontrol edin."
    if "belge numarası" in text:
        return "Belge numarası bulunamadı", "0700 ile başlayan belge numarası okunamıyor; PDF metnini veya belge formatını kontrol edin."
    if "adres okunamad" in text:
        return "Adres okunamadı", "SEVK ADRESI ve FATURA ADRESI etiketleri okunamıyor; PDF formatı farklı olabilir."
    if "koli adedi" in text:
        return "Koli adedi okunamadı", "Toplam Koli alanı bulunamadı; belgeyi Hata klasöründen kontrol edip koli bilgisini doğrulayın."
    if "bölge bulunamad" in text or "bolge bulunamad" in text:
        location = _terminal_location(address)
        if location:
            return (
                "Bölge bulunamadı",
                f"Teslimat yeri '{location}' config/regions.yaml içinde yoksa doğru bölge altına ekleyin.",
            )
        return "Bölge bulunamadı", "Teslimat il/ilçesi config/regions.yaml içinde yoksa doğru bölge altına ekleyin."
    if "belirsiz" in text or "çakışma" in text or "cakisma" in text:
        location = _terminal_location(address)
        detail = f" Teslimat yeri: {location}." if location else ""
        return "Bölge çakışması", "Aynı il/ilçe birden fazla bölgede olabilir veya adres yol adı şehir adıyla çakışmış olabilir; config'i kontrol edin." + detail
    return "Diğer hata", joined


def _doc_base_row(doc: "Document") -> list[str]:
    short_reason, suggestion = error_hint(doc.errors, doc.address)
    return [
        Path(doc.path).name,
        doc.pvs or "",
        doc.belge_no or "",
        doc.recipient or "",
        "" if doc.koli is None else str(doc.koli),
        doc.region or "",
        short_reason,
        suggestion,
        doc.address or "",
        "; ".join(doc.errors),
    ]


def write_error_report(error_docs: list["Document"], out_path: str | Path) -> str:
    """Hatali belgeleri Excel'de okunabilir CSV olarak yazar."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "dosya", "pvs", "belge_no", "alici", "koli", "bolge",
            "kisa_neden", "oneri", "bulunan_adres", "teknik_neden",
        ])
        for doc in error_docs:
            writer.writerow(_doc_base_row(doc))
    return str(out_path)


def write_shift_report(
    documents: list["Document"],
    targets: dict[int, TargetInfo],
    out_path: str | Path,
) -> str:
    """Tum vardiya icin Excel'de acilabilen detay CSV raporu yazar."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "durum", "hedef", "kova", "dosya", "pvs", "belge_no", "alici",
            "koli", "bolge", "kisa_neden", "oneri", "bulunan_adres", "teknik_neden",
        ])
        for doc in documents:
            status, target, bucket = targets.get(
                id(doc), ("Hata" if doc.errors else "", "", "")
            )
            writer.writerow([status, target, bucket] + _doc_base_row(doc))
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
