"""Tum akisi orkestre eden pipeline.

Gelen klasordeki her PDF -> metin cikar -> alanlari coz -> bolge tespit et
-> bolgeye gore grupla -> bolge basina tek PDF + Hata PDF + raporlar.
"""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
from typing import Callable, Optional

from . import report
from .extractor import extract_text
from .parser import Document, parse_document
from .regions import DsvMatcher, RegionMap
from .splitter import copy_docs, koli_bucket


ProgressCallback = Callable[[int, int, str], None]


@dataclass
class PipelineResult:
    shift_name: str
    out_dir: str
    documents: list[Document] = field(default_factory=list)
    region_counts: dict[str, int] = field(default_factory=dict)
    dsv_count: int = 0
    error_count: int = 0
    written_files: dict[str, list[str]] = field(default_factory=dict)
    summary: str = ""


def _list_pdfs(input_dir: Path) -> list[Path]:
    return sorted(p for p in input_dir.iterdir() if p.suffix.lower() == ".pdf")


def _process_one_document(path: Path, region_map: RegionMap) -> Document:
    try:
        text = extract_text(str(path))
    except Exception as exc:  # bozuk/okunamayan PDF -> Hata
        doc = Document(path=str(path))
        doc.errors.append(f"PDF okunamadı: {exc}")
        return doc

    doc = parse_document(str(path), text)
    if doc.ok:  # zorunlu alanlar tamam -> bolge dene
        region, err = region_map.detect(doc.address)
        if err:
            doc.errors.append(err)
        else:
            doc.region = region
    return doc


def _worker_count(total: int, requested: int | None = None) -> int:
    if total <= 1:
        return 1
    if requested is not None:
        return max(1, min(total, requested))
    cpu = os.cpu_count() or 1
    return max(1, min(total, 8, cpu + 2))


def process_documents(
    paths: list[Path],
    region_map: RegionMap,
    progress_callback: ProgressCallback | None = None,
    max_workers: int | None = None,
) -> list[Document]:
    """Her PDF icin Document uretir; okuma islemini paralel hizlandirir."""
    total = len(paths)
    if total == 0:
        return []

    workers = _worker_count(total, max_workers)
    docs: list[Document | None] = [None] * total

    if workers == 1:
        for index, path in enumerate(paths):
            docs[index] = _process_one_document(path, region_map)
            if progress_callback:
                progress_callback(index + 1, total, path.name)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_process_one_document, path, region_map): (index, path)
                for index, path in enumerate(paths)
            }
            completed = 0
            for future in as_completed(futures):
                index, path = futures[future]
                docs[index] = future.result()
                completed += 1
                if progress_callback:
                    progress_callback(completed, total, path.name)

    return [doc for doc in docs if doc is not None]


def run(
    input_dir: str | Path,
    out_base: str | Path,
    region_map: RegionMap,
    shift_name: Optional[str] = None,
    dsv_matcher: Optional[DsvMatcher] = None,
    progress_callback: ProgressCallback | None = None,
) -> PipelineResult:
    """Pipeline'i bastan sona calistirir ve sonuc dondurur.

    Cikti iki ana klasore ayrilir:
      * DSV/  -> teslimat yeri DSV lokasyon listesinde olan evraklar (duz).
      * B2/<bolge>/ -> geri kalan her evrak, B2 bolgesine gore.
    Bolgesi/adresi okunamayan evraklar <vardiya>/Hata/ altina gider.
    """
    input_dir = Path(input_dir)
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Gelen klasor bulunamadı: {input_dir}")

    # --name verilmezse zaman damgali vardiya adi (klasor adi yerine).
    if not shift_name:
        shift_name = "Vardiya_" + datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir = Path(out_base) / shift_name

    paths = _list_pdfs(input_dir)
    documents = process_documents(paths, region_map, progress_callback=progress_callback)

    # DSV once: teslimat yeri DSV listesindeyse DSV'ye (duz); degilse B2'de
    # bolge + koli kovasina (Palet/Dökme). Koli okunamayan B2 evraki Hata'ya.
    dsv_docs: list[Document] = []
    # bolge -> kova (Palet/Dökme) -> belgeler
    grouped: dict[str, dict[str, list[Document]]] = defaultdict(
        lambda: defaultdict(list)
    )
    error_docs: list[Document] = []
    doc_targets: dict[int, report.TargetInfo] = {}
    for doc in documents:
        if dsv_matcher is not None and dsv_matcher.matches(doc.address):
            dsv_docs.append(doc)
            doc_targets[id(doc)] = ("DSV", "DSV", "")
        elif doc.region:
            if doc.koli is None:
                doc.errors.append("koli adedi okunamadı")
                error_docs.append(doc)
                doc_targets[id(doc)] = ("Hata", "Hata", "")
            else:
                bucket = koli_bucket(doc.koli)
                grouped[doc.region][bucket].append(doc)
                doc_targets[id(doc)] = ("B2", doc.region, bucket)
        else:
            error_docs.append(doc)
            doc_targets[id(doc)] = ("Hata", "Hata", "")

    written: dict[str, list[str]] = {}
    # B2: her bolge -> "Bolge (N evrak)" / "Palet|Dökme (N evrak)".
    for region, buckets in grouped.items():
        region_total = sum(len(d) for d in buckets.values())
        region_dir = out_dir / "B2" / f"{region} ({region_total} evrak)"
        for bucket, docs in buckets.items():
            bucket_dir_name = f"{bucket} ({len(docs)} evrak)"
            files = copy_docs(docs, region_dir / bucket_dir_name)
            written[f"B2/{region}/{bucket_dir_name}"] = files
    # DSV: duz tek klasor (yaninda evrak sayisi).
    if dsv_docs:
        written["DSV"] = copy_docs(dsv_docs, out_dir / f"DSV ({len(dsv_docs)} evrak)")

    # Hata klasoru: basarisiz PDF'ler ayri ayri + neden raporu icinde.
    # (Klasor adi sabit "Hata" - arayuzdeki 'Tekrar Tara'/'Rapor' butonlari buna bakar.)
    if error_docs:
        hata_dir = out_dir / "Hata"
        written["Hata"] = copy_docs(error_docs, hata_dir)
        report.write_error_report(error_docs, hata_dir / "Hata_raporu.csv")

    # Raporlar.
    report_path = report.write_shift_report(
        documents, doc_targets, out_dir / "vardiya_raporu.csv"
    )
    written["Rapor"] = [report_path]
    region_counts = {
        r: sum(len(d) for d in buckets.values()) for r, buckets in grouped.items()
    }
    summary = report.format_summary(region_counts, len(error_docs), len(dsv_docs))
    report.write_summary(summary, out_dir / "ozet.txt")

    return PipelineResult(
        shift_name=shift_name,
        out_dir=str(out_dir),
        documents=documents,
        region_counts=region_counts,
        dsv_count=len(dsv_docs),
        error_count=len(error_docs),
        written_files=written,
        summary=summary,
    )
