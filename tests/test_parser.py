"""Alan cikarimi (PVS / belge no / adres) testleri."""

from perfetti_splitter.extractor import extract_text
from perfetti_splitter.parser import extract_address, parse_document


def test_parse_full_document(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "irs1.pdf")
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.ok
    assert doc.pvs == "PVS2026000123"
    assert doc.belge_no == "0700000456"
    assert "ADANA" in doc.address
    assert not doc.errors


def test_multipage_document_is_single_irsaliye(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "irs_multi.pdf", pages=3)
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.ok
    assert doc.pvs == "PVS2026000123"


def test_missing_pvs_is_error(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "no_pvs.pdf", pvs=None)
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert not doc.ok
    assert "PVS kodu bulunamadı" in doc.errors


def test_missing_belge_no_is_error(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "no_belge.pdf", belge_no=None)
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert not doc.ok
    assert "belge numarası bulunamadı" in doc.errors


def test_missing_address_is_error(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "no_addr.pdf", address=None)
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert not doc.ok
    assert "adres okunamadı" in doc.errors


def test_empty_text_is_error():
    doc = parse_document("ghost.pdf", "")
    assert not doc.ok
    assert "adres okunamadı" in doc.errors


def test_extract_address_from_label():
    text = "PVS Kodu: PVS2026\nSEVK ADRESI: MIGROS ANKARA DEPO\nDiger satir"
    addr = extract_address(text)
    assert addr is not None
    assert "ANKARA" in addr
