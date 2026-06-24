"""Alan cikarimi (PVS / belge no / SEVK adresi) testleri."""

from perfetti_splitter.extractor import extract_text
from perfetti_splitter.parser import extract_destination, parse_document


def test_parse_full_document(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "irs1.pdf", il="ADANA")
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.ok
    assert doc.pvs == "PVS2026000123"
    assert doc.belge_no == "0700000456"
    assert doc.address == "ADANA"
    assert not doc.errors


def test_sevk_address_used_not_sender_or_billing(tmp_path, make_pdf):
    # KRITIK: gonderici ve fatura adresi Istanbul (Aytop). Program SEVK
    # adresindeki gercek hedefi (TRABZON) okumali, Istanbul'u degil.
    pdf = make_pdf(tmp_path / "trabzon.pdf", il="TRABZON")
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.address == "TRABZON"
    assert "ISTANBUL" not in (doc.address or "").upper()


def test_multipage_document_is_single_irsaliye(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "irs_multi.pdf", il="ANKARA", pages=3)
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.ok
    assert doc.address == "ANKARA"
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


def test_missing_sevk_address_is_error(tmp_path, make_pdf):
    # SEVK blogu yoksa, gonderici/fatura adresi olsa bile adres okunamaz.
    pdf = make_pdf(tmp_path / "no_addr.pdf", include_sevk=False)
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert not doc.ok
    assert "adres okunamadı" in doc.errors


def test_empty_text_is_error():
    doc = parse_document("ghost.pdf", "")
    assert not doc.ok
    assert "adres okunamadı" in doc.errors


def test_extract_destination_from_province_pattern():
    text = "SEVK ADRESI\nAdres: KORU MAH.\n7 Arsin/TRABZON/Turkiye\nFATURA ADRESI\nAdres: x/Istanbul/TR"
    assert extract_destination(text) == "TRABZON"
