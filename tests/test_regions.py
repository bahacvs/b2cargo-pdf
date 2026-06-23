"""Bolge tespiti ve Turkce normalizasyon testleri."""

import pytest

from perfetti_splitter.regions import RegionMap, normalize


@pytest.fixture
def region_map():
    return RegionMap(
        {
            "Adana": ["Adana", "Mersin", "Gaziantep", "Kahramanmaraş"],
            "Ankara": ["Ankara", "Konya", "Niğde", "Bilecik"],
            "Antalya": ["Antalya", "Alanya"],
            "Aytop": ["İstanbul", "Bursa", "Bilecik"],
            "Izmir": ["İzmir", "Muğla", "Fethiye"],
            "Erzurum": ["Erzurum", "Van"],
        }
    )


def test_normalize_folds_turkish_chars():
    assert normalize("GAZİANTEP") == "gaziantep"
    assert normalize("Gaziantep") == "gaziantep"
    assert normalize("ŞANLIURFA") == "sanliurfa"
    assert normalize("İzmir") == "izmir"
    assert normalize("Niğde") == "nigde"


def test_detect_simple_city(region_map):
    region, err = region_map.detect("MIGROS ADANA BOLGE MERKEZ DEPOSU")
    assert region == "Adana"
    assert err is None


def test_detect_is_case_and_accent_insensitive(region_map):
    region, err = region_map.detect("migros gazİantep deposu")
    assert region == "Adana"
    assert err is None


def test_detect_district_maps_to_region(region_map):
    # Alanya (ilce) -> Antalya bolgesi
    region, err = region_map.detect("MIGROS ALANYA SUBE")
    assert region == "Antalya"
    assert err is None
    # Fethiye (ilce) -> Izmir bolgesi
    region, err = region_map.detect("MIGROS FETHIYE DEPO")
    assert region == "Izmir"


def test_unknown_city_is_error(region_map):
    region, err = region_map.detect("MIGROS ATLANTIS DEPOSU")
    assert region is None
    assert err == "bölge bulunamadı"


def test_empty_address_is_error(region_map):
    region, err = region_map.detect("")
    assert region is None
    assert err == "adres okunamadı"


def test_bilecik_conflict_goes_to_error(region_map):
    # Bilecik hem Ankara hem Aytop'ta -> belirsiz -> Hata (tahmin yok)
    region, err = region_map.detect("MIGROS BILECIK DEPOSU")
    assert region is None
    assert err.startswith("belirsiz/çakışma")
    assert "Ankara" in err and "Aytop" in err


def test_config_conflicts_detected(region_map):
    assert "bilecik" in region_map.conflicts
    assert region_map.conflicts["bilecik"] == {"Ankara", "Aytop"}


def test_same_region_two_cities_still_single(region_map):
    # Ayni bolgeden iki sehir -> tek bolge, cakisma degil
    region, err = region_map.detect("ADANA MERSIN ARASI DEPO")
    assert region == "Adana"
    assert err is None


def test_company_name_van_does_not_collide_with_van_city(region_map):
    # "Perfetti Van Melle" firma adindaki 'Van', Erzurum'daki Van ili ile
    # cakismamali; sadece gercek sehir (Adana) bulunmali.
    region, err = region_map.detect("PERFETTI VAN MELLE - MIGROS ADANA DEPO")
    assert region == "Adana"
    assert err is None


def test_real_van_city_still_detected(region_map):
    # Firma adi temizlense de gercek Van ili tespit edilebilmeli.
    region, err = region_map.detect("MIGROS VAN MERKEZ DEPO")
    assert region == "Erzurum"
    assert err is None


def test_word_boundary_avoids_substring_false_match(region_map):
    # "Vanlikoy" icindeki 'van' tam kelime olmadigi icin Erzurum'a dusmemeli
    region, err = region_map.detect("MIGROS VANLIKOY MAH DEPO")
    assert region is None
    assert err == "bölge bulunamadı"
