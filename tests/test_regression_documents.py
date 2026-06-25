"""Gercek irsaliye hatalarindan uretilen regresyon testleri."""

from perfetti_splitter.parser import parse_document
from perfetti_splitter.regions import RegionMap
from perfetti_splitter.report import error_hint


REGION_MAP = RegionMap(
    {
        "Adana": ["Adana", "Mersin", "Gaziantep", "Kahramanmaraş", "Şanlıurfa"],
        "Ankara": ["Ankara", "Konya", "Niğde", "Bilecik"],
        "Antalya": ["Antalya", "Alanya", "Burdur"],
        "Aytop": ["İstanbul", "Bursa", "Bilecik", "Afyonkarahisar", "Çayırova"],
        "Diyarbakir": ["Diyarbakır"],
        "Izmir": ["İzmir", "Muğla", "Fethiye"],
        "Erzurum": ["Erzurum", "Van"],
    }
)


def _irsaliye_text(recipient: str, address: str, koli: int = 12) -> str:
    return f"""
PERFETTI VAN MELLE GIDA SAN. VE TIC. A.S.
PVS2026000099999
Belge No: 0700999999
SEVK ADRESİ
{recipient}
Adres: {address}
Vergi Dairesi: BESIKTAS
FATURA ADRESİ
Fatura Adresi: İstanbul/Türkiye
Toplam Koli: {koli}
"""


def test_problematic_delivery_addresses_keep_correct_region():
    cases = [
        (
            "OZDILEK A.S - NILUFER",
            "ALAADDINBEY MAH. IZMIR YOLU CAD. Nilüfer/BURSA/Türkiye",
            "Aytop",
        ),
        (
            "OZDILEK A.S. - AFYON KARAHISAR SB",
            "AFYON ANTALYA YOLU Merkez/AFYONKARAHISAR/Türkiye",
            "Aytop",
        ),
        (
            "GETİR-DİYARBAKIR MERKEZ DEPO",
            "Şanlıurfa Yolu 20.Km Bağlar/DIYARBAKIR/Türkiye",
            "Diyarbakir",
        ),
        (
            "A101 BURDUR",
            "Kışla Mah. Ankara Bulvarı No:33/1 Merkez/BURDUR/Türkiye",
            "Antalya",
        ),
        (
            "BIZIM TOPTAN SATIS - SEKERPINAR DM",
            "FEVZI CAKMAK CD. SEKERPINAR MH./CAYIROVA/Türkiye",
            "Aytop",
        ),
    ]

    for recipient, address, expected_region in cases:
        doc = parse_document("fixture.pdf", _irsaliye_text(recipient, address))
        assert doc.errors == []
        region, err = REGION_MAP.detect(doc.address)
        assert (region, err) == (expected_region, None)


def test_error_report_suggests_missing_terminal_location():
    reason, suggestion = error_hint(
        ["bölge bulunamadı"],
        "YENI MUSTERI Adres: Organize Sanayi 1. Cadde/GEBZE/Türkiye",
    )

    assert reason == "Bölge bulunamadı"
    assert "GEBZE" in suggestion
    assert "config/regions.yaml" in suggestion
