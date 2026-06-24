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
from .splitter import copy_docs, write_region_folders


@dataclass
class PipelineResult:
    shift_name: str
    out_dir: str
    documents: list[Document] = field(default_factory=list)
    region_counts: dict[str, int] = field(default_factory=dict)
    error_count: int = 0
    written_files: dict[str, list[str]] = field(default_factory=dict)
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
    grouped: dict[str, list[Document]] = defaultdict(list)
    error_docs: list[Document] = []
    for doc in documents:
        if doc.region:
            grouped[doc.region].append(doc)
        else:
            error_docs.append(doc)

    # Her bolge icin bir klasor, icine ayri PDF'ler.
    written = write_region_folders(grouped, out_dir)

    # Hata klasoru: basarisiz PDF'ler ayri ayri + neden raporu icinde.
    if error_docs:
        hata_dir = out_dir / "Hata"
        written["Hata"] = copy_docs(error_docs, hata_dir)
        report.write_error_report(error_docs, hata_dir / "Hata_raporu.csv")

    # Raporlar.
    region_counts = {r: len(d) for r, d in grouped.items()}
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
