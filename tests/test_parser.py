"""Alan cikarimi (PVS / belge no / SEVK adresi) testleri."""

from decimal import Decimal

from perfetti_splitter.extractor import extract_text
from perfetti_splitter.parser import (
    extract_brut_agirlik,
    extract_destination,
    extract_koli,
    extract_recipient,
    parse_document,
)
from perfetti_splitter.regions import RegionMap

# Testlerde kullanilan kucuk bolge haritasi.
RM = RegionMap(
    {
        "Adana": ["Adana", "Mersin", "Kahramanmaraş"],
        "Ankara": ["Ankara", "Kayseri"],
        "Aytop": ["İstanbul", "Bursa"],
        "Samsun": ["Trabzon"],
    }
)


def _region(text: str):
    return RM.detect(extract_destination(text))


def test_parse_full_document(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "irs1.pdf", il="ADANA")
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.ok
    assert doc.pvs == "PVS2026000123"
    assert doc.belge_no == "0700000456"
    assert doc.brut_agirlik == Decimal("100")
    assert "ADANA" in (doc.address or "").upper()
    assert not doc.errors


def test_sevk_address_used_not_sender_or_billing(tmp_path, make_pdf):
    # KRITIK: gonderici ve fatura adresi Istanbul (Aytop). Program SEVK
    # adresindeki gercek hedefi (TRABZON) okumali, Istanbul'u degil.
    pdf = make_pdf(tmp_path / "trabzon.pdf", il="TRABZON")
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert "TRABZON" in (doc.address or "").upper()
    assert "ISTANBUL" not in (doc.address or "").upper()
    assert _region(text) == ("Samsun", None)


def test_city_from_recipient_when_address_has_only_district(tmp_path, make_pdf):
    # Gercek vaka: SEVK adres satirinda yalnizca ILCE var (SARICAM=Adana ilcesi),
    # il yazmiyor; ama alici adinda ADANA geciyor. Bolge ADANA bulunmali.
    pdf = make_pdf(
        tmp_path / "saricam.pdf",
        recipient="GRATIS - ADANA DEPO GRATIS - ADANA DEPO",
        addr_tail="6515 SULUCA MH./SARICAM/Turkiye",
    )
    text = extract_text(str(pdf))
    assert _region(text) == ("Adana", None)


def test_vergi_dairesi_city_does_not_cause_conflict(tmp_path, make_pdf):
    # Alicinin vergi dairesi farkli bir sehir (BURSA=Aytop) olsa bile teslimat
    # ili (ADANA) ile cakisma yaratmamali; "Vergi Dairesi" satiri elenir.
    pdf = make_pdf(tmp_path / "vd.pdf", il="ADANA", vergi_dairesi="BURSA")
    text = extract_text(str(pdf))
    assert _region(text) == ("Adana", None)


def test_multipage_document_is_single_irsaliye(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "irs_multi.pdf", il="ANKARA", pages=3)
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.ok
    assert "ANKARA" in (doc.address or "").upper()
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


def test_extract_recipient_basic(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "r.pdf", il="ADANA")
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.recipient == "A101 ADANA"


def test_extract_recipient_dedups_doubled_name():
    text = (
        "SEVK ADRESI Irsaliye No: PVS1\n"
        "GRATIS - ADANA DEPO GRATIS - ADANA DEPO\n"
        "Adres: 6515 SULUCA MH./SARICAM/Turkiye\n"
        "FATURA ADRESI\n"
    )
    assert extract_recipient(text) == "GRATIS - ADANA DEPO"


def test_extract_recipient_none_without_sevk():
    assert extract_recipient("hicbir sevk blogu yok") is None


def test_extract_koli():
    assert extract_koli("Toplam Miktar: 170 - Toplam Koli: 24") == 24
    assert extract_koli("Toplam Koli: 9") == 9
    assert extract_koli("koli bilgisi yok") is None


def test_extract_brut_agirlik():
    assert extract_brut_agirlik("Toplam Brüt Ağırlık: 1.234,50 KG") == Decimal("1234.50")
    assert extract_brut_agirlik("Toplam Brut Agirlik: 12.5") == Decimal("12.5")
    assert extract_brut_agirlik("agirlik bilgisi yok") is None

def test_parse_document_sets_koli(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "k.pdf", il="ADANA", koli=15)
    doc = parse_document(str(pdf), extract_text(str(pdf)))
    assert doc.koli == 15


def test_extract_destination_excludes_sender_and_billing():
    text = (
        "Adres: Esenyurt/Istanbul\n"
        "SEVK ADRESI Irsaliye No: PVS2026000123\n"
        "A101 TRABZON\n"
        "Adres: KORU MAH.\n"
        "7 Arsin/TRABZON/Turkiye\n"
        "Vergi Dairesi: ALEMDAG\n"
        "FATURA ADRESI\n"
        "Adres: x/Istanbul/TR"
    )
    dest = extract_destination(text)
    assert "TRABZON" in dest.upper()
    assert "ISTANBUL" not in dest.upper()
    assert "ALEMDAG" not in dest.upper()  # Vergi Dairesi satiri elendi

"""Alan cikarimi (PVS / belge no / SEVK adresi) testleri."""

from perfetti_splitter.extractor import extract_text
from perfetti_splitter.parser import (
    extract_destination,
    extract_koli,
    extract_recipient,
    parse_document,
)
from perfetti_splitter.regions import RegionMap

# Testlerde kullanilan kucuk bolge haritasi.
RM = RegionMap(
    {
        "Adana": ["Adana", "Mersin", "Kahramanmaraş"],
        "Ankara": ["Ankara", "Kayseri"],
        "Aytop": ["İstanbul", "Bursa"],
        "Samsun": ["Trabzon"],
    }
)


def _region(text: str):
    return RM.detect(extract_destination(text))


def test_parse_full_document(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "irs1.pdf", il="ADANA")
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.ok
    assert doc.pvs == "PVS2026000123"
    assert doc.belge_no == "0700000456"
    assert "ADANA" in (doc.address or "").upper()
    assert not doc.errors


def test_sevk_address_used_not_sender_or_billing(tmp_path, make_pdf):
    # KRITIK: gonderici ve fatura adresi Istanbul (Aytop). Program SEVK
    # adresindeki gercek hedefi (TRABZON) okumali, Istanbul'u degil.
    pdf = make_pdf(tmp_path / "trabzon.pdf", il="TRABZON")
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert "TRABZON" in (doc.address or "").upper()
    assert "ISTANBUL" not in (doc.address or "").upper()
    assert _region(text) == ("Samsun", None)


def test_city_from_recipient_when_address_has_only_district(tmp_path, make_pdf):
    # Gercek vaka: SEVK adres satirinda yalnizca ILCE var (SARICAM=Adana ilcesi),
    # il yazmiyor; ama alici adinda ADANA geciyor. Bolge ADANA bulunmali.
    pdf = make_pdf(
        tmp_path / "saricam.pdf",
        recipient="GRATIS - ADANA DEPO GRATIS - ADANA DEPO",
        addr_tail="6515 SULUCA MH./SARICAM/Turkiye",
    )
    text = extract_text(str(pdf))
    assert _region(text) == ("Adana", None)


def test_vergi_dairesi_city_does_not_cause_conflict(tmp_path, make_pdf):
    # Alicinin vergi dairesi farkli bir sehir (BURSA=Aytop) olsa bile teslimat
    # ili (ADANA) ile cakisma yaratmamali; "Vergi Dairesi" satiri elenir.
    pdf = make_pdf(tmp_path / "vd.pdf", il="ADANA", vergi_dairesi="BURSA")
    text = extract_text(str(pdf))
    assert _region(text) == ("Adana", None)


def test_multipage_document_is_single_irsaliye(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "irs_multi.pdf", il="ANKARA", pages=3)
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.ok
    assert "ANKARA" in (doc.address or "").upper()
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


def test_extract_recipient_basic(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "r.pdf", il="ADANA")
    text = extract_text(str(pdf))
    doc = parse_document(str(pdf), text)
    assert doc.recipient == "A101 ADANA"


def test_extract_recipient_dedups_doubled_name():
    text = (
        "SEVK ADRESI Irsaliye No: PVS1\n"
        "GRATIS - ADANA DEPO GRATIS - ADANA DEPO\n"
        "Adres: 6515 SULUCA MH./SARICAM/Turkiye\n"
        "FATURA ADRESI\n"
    )
    assert extract_recipient(text) == "GRATIS - ADANA DEPO"


def test_extract_recipient_none_without_sevk():
    assert extract_recipient("hicbir sevk blogu yok") is None


def test_extract_koli():
    assert extract_koli("Toplam Miktar: 170 - Toplam Koli: 24") == 24
    assert extract_koli("Toplam Koli: 9") == 9
    assert extract_koli("koli bilgisi yok") is None


def test_parse_document_sets_koli(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "k.pdf", il="ADANA", koli=15)
    doc = parse_document(str(pdf), extract_text(str(pdf)))
    assert doc.koli == 15


def test_extract_destination_excludes_sender_and_billing():
    text = (
        "Adres: Esenyurt/Istanbul\n"
        "SEVK ADRESI Irsaliye No: PVS2026000123\n"
        "A101 TRABZON\n"
        "Adres: KORU MAH.\n"
        "7 Arsin/TRABZON/Turkiye\n"
        "Vergi Dairesi: ALEMDAG\n"
        "FATURA ADRESI\n"
        "Adres: x/Istanbul/TR"
    )
    dest = extract_destination(text)
    assert "TRABZON" in dest.upper()
    assert "ISTANBUL" not in dest.upper()
    assert "ALEMDAG" not in dest.upper()  # Vergi Dairesi satiri elendi
