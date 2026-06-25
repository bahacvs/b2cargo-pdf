"""Bolge klasoru + ayri PDF cikti ve uctan uca pipeline testleri."""

from pathlib import Path

import pytest
from pypdf import PdfReader

from perfetti_splitter.parser import Document
from perfetti_splitter.pipeline import run
from perfetti_splitter.regions import DsvMatcher, RegionMap
from perfetti_splitter.splitter import (
    copy_docs,
    doc_filename,
    koli_bucket,
    safe_filename,
    write_region_folders,
)


def test_koli_bucket():
    assert koli_bucket(9) == "Palet"
    assert koli_bucket(24) == "Palet"
    assert koli_bucket(8) == "Dökme"
    assert koli_bucket(1) == "Dökme"


def test_dsv_matcher_il_bazli():
    # Istanbul komple: teslimat ili Istanbul ise DSV.
    m = DsvMatcher(iller=["İstanbul"], noktalar=[])
    assert m.matches("A101 ISTANBUL Adres: ... Esenyurt/ISTANBUL/Türkiye")
    assert not m.matches("A101 ADANA Adres: Merkez/ADANA/Türkiye")
    assert not m.matches(None)
    # Sirket adinda 'Istanbul' gecse de teslimat ili Ankara ise DSV degil.
    assert not m.matches("ISTANBUL GIDA A.S. Adres: Cankaya/ANKARA/Türkiye")


def test_dsv_matcher_ilce_isim():
    # Diger iller: ilce + isim birlikte eslesmeli.
    m = DsvMatcher(iller=["İstanbul"], noktalar=[{"ilce": "Gebze", "anahtarlar": ["MIGROS", "METRO"]}])
    # Gebze + MIGROS -> DSV
    assert m.matches("MIGROS TICARET A.S. Adres: ... Gebze/KOCAELİ/Türkiye")
    # Gebze ama DSV-disi musteri -> DSV degil (B2)
    assert not m.matches("BAZ GIDA LTD Adres: ... Gebze/KOCAELİ/Türkiye")
    # MIGROS ama baska ilce (Ankara) -> DSV degil
    assert not m.matches("MIGROS TICARET A.S. Adres: ... Cankaya/ANKARA/Türkiye")


@pytest.fixture
def region_map():
    return RegionMap(
        {
            "Adana": ["Adana", "Mersin"],
            "Ankara": ["Ankara", "Konya", "Bilecik"],
            "Aytop": ["İstanbul", "Bilecik"],
        }
    )


def test_safe_filename_strips_invalid_chars():
    assert safe_filename('A101 / ADANA: *DEPO*') == "A101 ADANA DEPO"
    assert safe_filename("   ") == "irsaliye"  # bos -> varsayilan


def test_doc_filename_recipient_plus_pvs():
    doc = Document(path="x.pdf", recipient="A101 ADANA", pvs="PVS2026000123")
    assert doc_filename(doc) == "A101 ADANA - PVS2026000123.pdf"


def test_doc_filename_falls_back_to_original_stem():
    doc = Document(path="/in/orig.pdf", recipient=None, pvs=None)
    assert doc_filename(doc) == "orig.pdf"


def test_copy_docs_handles_name_collision(tmp_path, make_pdf):
    p1 = make_pdf(tmp_path / "1.pdf")
    p2 = make_pdf(tmp_path / "2.pdf")
    docs = [
        Document(path=str(p1), recipient="A101 ADANA", pvs="PVS1"),
        Document(path=str(p2), recipient="A101 ADANA", pvs="PVS1"),  # ayni ad
    ]
    written = copy_docs(docs, tmp_path / "Adana")
    names = sorted(Path(w).name for w in written)
    assert names == ["A101 ADANA - PVS1 (2).pdf", "A101 ADANA - PVS1.pdf"]
    assert all(Path(w).exists() for w in written)


def test_write_region_folders_creates_subfolders(tmp_path, make_pdf):
    p1 = make_pdf(tmp_path / "a.pdf")
    p2 = make_pdf(tmp_path / "b.pdf")
    grouped = {
        "Adana": [Document(path=str(p1), recipient="A101 ADANA", pvs="PVS1")],
        "Ankara": [Document(path=str(p2), recipient="A101 ANKARA", pvs="PVS2")],
    }
    written = write_region_folders(grouped, tmp_path / "out")
    assert (tmp_path / "out" / "Adana" / "A101 ADANA - PVS1.pdf").exists()
    assert (tmp_path / "out" / "Ankara" / "A101 ANKARA - PVS2.pdf").exists()
    # kopyalanan dosya gecerli bir PDF
    assert len(PdfReader(written["Adana"][0]).pages) >= 1


def test_end_to_end_pipeline(tmp_path, make_pdf):
    gelen = tmp_path / "Gelen"
    gelen.mkdir()
    # Adana Palet (koli 24) + Adana Dokme (koli 5), Ankara Palet, DSV (Istanbul),
    # koli okunamayan (Hata), bilinmeyen (Hata), Bilecik cakismasi (Hata).
    make_pdf(gelen / "a1.pdf", il="ADANA", pvs="PVS0001", koli=24)
    make_pdf(gelen / "a2.pdf", il="MERSIN", pvs="PVS0002", koli=5)
    make_pdf(gelen / "ank.pdf", il="ANKARA", pvs="PVS0003", koli=9)
    make_pdf(gelen / "ist.pdf", il="ISTANBUL", pvs="PVS0006", koli=12)  # -> DSV
    make_pdf(gelen / "nokoli.pdf", il="ADANA", pvs="PVS0007", koli=None)  # -> Hata
    make_pdf(gelen / "unknown.pdf", il="ATLANTIS", pvs="PVS0004")
    make_pdf(gelen / "conflict.pdf", il="BILECIK", pvs="PVS0005")

    region_map = RegionMap(
        {
            "Adana": ["Adana", "Mersin"],
            "Ankara": ["Ankara", "Bilecik"],
            "Aytop": ["İstanbul", "Bilecik"],
        }
    )
    dsv = DsvMatcher(iller=["İstanbul"], noktalar=[])
    result = run(
        gelen, tmp_path / "out", region_map,
        shift_name="TestVardiya", dsv_matcher=dsv,
    )

    assert result.region_counts.get("Adana") == 2  # palet + dokme
    assert result.region_counts.get("Ankara") == 1
    assert result.dsv_count == 1
    assert result.error_count == 3  # nokoli + unknown + bilecik cakismasi

    out_dir = Path(result.out_dir)
    # B2 bolge -> "Bolge (N evrak)" / Palet|Dökme alt klasorleri
    assert (out_dir / "B2" / "Adana (2 evrak)" / "Palet" / "A101 ADANA - PVS0001.pdf").exists()
    assert (out_dir / "B2" / "Adana (2 evrak)" / "Dökme" / "A101 MERSIN - PVS0002.pdf").exists()
    assert (out_dir / "B2" / "Ankara (1 evrak)" / "Palet" / "A101 ANKARA - PVS0003.pdf").exists()
    # DSV duz (yaninda sayi), palet/dokme yok
    assert (out_dir / "DSV (1 evrak)" / "A101 ISTANBUL - PVS0006.pdf").exists()
    assert not (out_dir / "DSV (1 evrak)" / "Palet").exists()
    # Hata klasoru sabit adli
    assert len(list((out_dir / "Hata").glob("*.pdf"))) == 3
    assert (out_dir / "Hata" / "Hata_raporu.csv").exists()
    assert (out_dir / "ozet.txt").exists()


def test_pipeline_missing_input_dir_raises(tmp_path, region_map):
    with pytest.raises(NotADirectoryError):
        run(tmp_path / "yok", tmp_path / "out", region_map)
