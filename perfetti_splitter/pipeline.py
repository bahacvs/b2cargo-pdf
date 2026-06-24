"""Tum akisi orkestre eden pipeline.

Gelen klasordeki her PDF -> metin cikar -> alanlari coz -> bolge tespit et
-> bolgeye gore grupla -> bolge basina tek PDF + Hata PDF + raporlar.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import report
from .extractor import extract_text
from .parser import Document, parse_document
from .regions import RegionMap
from .splitter import region_filename, write_region_pdfs


@dataclass
class PipelineResult:
    shift_name: str
    out_dir: str
    documents: list[Document] = field(default_factory=list)
    region_counts: dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    written_files: dict[str, str] = field(default_factory=dict)
    summary: str = ""


def _list_pdfs(input_dir: Path) -> list[Path]:
    return sorted(p for p in input_dir.iterdir() if p.suffix.lower() == ".pdf")


def process_documents(paths: list[Path], region_map: RegionMap) -> list[Document]:
    """Her PDF icin Document uretir (metin, alanlar, bolge/hata)."""
    docs: list[Document] = []
    for path in paths:
        try:
            text = extract_text(str(path))
        except Exception as exc:  # bozuk/okunamayan PDF -> Hata
            doc = Document(path=str(path))
            doc.errors.append(f"PDF okunamadı: {exc}")
            docs.append(doc)
            continue

        doc = parse_document(str(path), text)
        if doc.ok:  # zorunlu alanlar tamam -> bolge dene
            region, err = region_map.detect(doc.address)
            if err:
                doc.errors.append(err)
            else:
                doc.region = region
        docs.append(doc)
    return docs


def run(
    input_dir: str | Path,
    out_base: str | Path,
    region_map: RegionMap,
    shift_name: Optional[str] = None,
) -> PipelineResult:
    """Pipeline'i bastan sona calistirir ve sonuc dondurur."""
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Gelen klasor bulunamadı: {input_dir}")

    # --name verilmezse zaman damgali vardiya adi (klasor adi yerine).
    if not shift_name:
        shift_name = "Vardiya_" + datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir = Path(out_base) / shift_name

    paths = _list_pdfs(input_dir)
    documents = process_documents(paths, region_map)

    # Bolgeye gore grupla; hatali olanlari ayir.
    grouped: dict[str, list[str]] = defaultdict(list)
    error_docs: list[Document] = []
    for doc in documents:
        if doc.region:
            grouped[doc.region].append(doc.path)
        else:
            error_docs.append(doc)

    written = write_region_pdfs(grouped, out_dir)

    # Hata PDF'i (tum hatali dosyalari tek PDF'te topla).
    if error_docs:
        from .splitter import merge_pdfs

        readable = [d.path for d in error_docs if d.path and Path(d.path).exists()]
        if readable:
            hata_path = out_dir / region_filename("Hata", len(error_docs))
            try:
                merge_pdfs(readable, hata_path)
                written["Hata"] = str(hata_path)
            except Exception:
                pass  # bozuk PDF'ler birlestirilemeyebilir; rapor yeterli

    # Raporlar.
    region_counts = {r: len(p) for r, p in grouped.items()}
    if error_docs:
        report.write_error_report(error_docs, out_dir / "Hata_raporu.csv")
    summary = report.format_summary(region_counts, len(error_docs))
    report.write_summary(summary, out_dir / "ozet.txt")

    return PipelineResult(
        shift_name=shift_name,
        out_dir=str(out_dir),
        documents=documents,
        region_counts=region_counts,
        error_count=len(error_docs),
        written_files=written,
        summary=summary,
    )
