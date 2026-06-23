"""Birlestirme/gruplama ve uctan uca pipeline testleri."""

from pathlib import Path

import pytest
from pypdf import PdfReader

from perfetti_splitter.pipeline import run
from perfetti_splitter.regions import RegionMap
from perfetti_splitter.splitter import merge_pdfs, region_filename, write_region_pdfs


@pytest.fixture
def region_map():
    return RegionMap(
        {
            "Adana": ["Adana", "Mersin"],
            "Ankara": ["Ankara", "Konya", "Bilecik"],
            "Aytop": ["İstanbul", "Bilecik"],
        }
    )


def test_region_filename():
    assert region_filename("Adana", 24) == "Adana_24evrak.pdf"
    assert region_filename("Hata", 3) == "Hata_3evrak.pdf"


def test_merge_pdfs_counts_pages(tmp_path, make_pdf):
    a = make_pdf(tmp_path / "a.pdf", pages=2)
    b = make_pdf(tmp_path / "b.pdf", pages=1)
    out = tmp_path / "merged.pdf"
    n = merge_pdfs([str(a), str(b)], out)
    assert n == 3
    assert len(PdfReader(str(out)).pages) == 3


def test_write_region_pdfs_names_by_count(tmp_path, make_pdf):
    p1 = make_pdf(tmp_path / "1.pdf")
    p2 = make_pdf(tmp_path / "2.pdf")
    grouped = {"Adana": [str(p1), str(p2)]}
    written = write_region_pdfs(grouped, tmp_path / "out")
    assert Path(written["Adana"]).name == "Adana_2evrak.pdf"
    assert Path(written["Adana"]).exists()


def test_end_to_end_pipeline(tmp_path, make_pdf):
    gelen = tmp_path / "Gelen"
    gelen.mkdir()
    # 2 Adana, 1 Ankara, 1 bilinmeyen (Hata), 1 Bilecik cakismasi (Hata)
    make_pdf(gelen / "a1.pdf", address="MIGROS ADANA DEPO")
    make_pdf(gelen / "a2.pdf", address="MIGROS MERSIN SUBE")
    make_pdf(gelen / "ank.pdf", address="MIGROS ANKARA MERKEZ")
    make_pdf(gelen / "unknown.pdf", address="MIGROS ATLANTIS DEPO")
    make_pdf(gelen / "conflict.pdf", address="MIGROS BILECIK DEPO")

    region_map = RegionMap(
        {
            "Adana": ["Adana", "Mersin"],
            "Ankara": ["Ankara", "Bilecik"],
            "Aytop": ["İstanbul", "Bilecik"],
        }
    )
    result = run(gelen, tmp_path / "out", region_map, shift_name="TestVardiya")

    assert result.region_counts.get("Adana") == 2
    assert result.region_counts.get("Ankara") == 1
    assert result.error_count == 2  # unknown + bilecik cakismasi

    out_dir = Path(result.out_dir)
    assert (out_dir / "Adana_2evrak.pdf").exists()
    assert (out_dir / "Ankara_1evrak.pdf").exists()
    assert (out_dir / "Hata_2evrak.pdf").exists()
    assert (out_dir / "Hata_raporu.csv").exists()
    assert (out_dir / "ozet.txt").exists()


def test_pipeline_missing_input_dir_raises(tmp_path, region_map):
    with pytest.raises(NotADirectoryError):
        run(tmp_path / "yok", tmp_path / "out", region_map)
