"""GUI'nin Tk'dan bagimsiz mantik katmani testleri (pencere acilmadan)."""

from decimal import Decimal
from pathlib import Path

import perfetti_splitter.gui as gui


def test_config_path_prefers_external(monkeypatch, tmp_path):
    # base_dir yanindaki config/regions.yaml varsa o tercih edilir.
    cfg = tmp_path / "config" / "regions.yaml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("Adana: [Adana]\n", encoding="utf-8")
    monkeypatch.setattr(gui, "base_dir", lambda: tmp_path)
    assert gui.config_path() == cfg


def test_config_path_falls_back_to_bundled(monkeypatch, tmp_path):
    # base_dir'de config yoksa pakete gomulu (resource_dir) kopya kullanilir.
    bundled = tmp_path / "bundle"
    (bundled / "config").mkdir(parents=True)
    (bundled / "config" / "regions.yaml").write_text("Adana: [Adana]\n", encoding="utf-8")
    monkeypatch.setattr(gui, "base_dir", lambda: tmp_path / "empty")
    monkeypatch.setattr(gui, "resource_dir", lambda: bundled)
    assert gui.config_path() == bundled / "config" / "regions.yaml"


def test_run_split_end_to_end(monkeypatch, tmp_path, make_pdf):
    # Gercek config + pipeline ile uctan uca: gelen klasor -> bolge PDF'leri.
    repo_root = Path(__file__).resolve().parent.parent
    monkeypatch.setattr(gui, "config_path", lambda: repo_root / "config" / "regions.yaml")
    monkeypatch.setattr(gui, "default_output_dir", lambda: tmp_path / "out")

    gelen = tmp_path / "Gelen"
    gelen.mkdir()
    make_pdf(gelen / "a1.pdf", il="ADANA")
    make_pdf(gelen / "a2.pdf", il="MERSIN")
    make_pdf(gelen / "ank.pdf", il="ANKARA")

    result = gui.run_split(gelen, shift_name="GuiTest")

    assert result.region_counts.get("Adana") == 2
    assert result.region_counts.get("Ankara") == 1
    assert result.error_count == 0
    out_dir = Path(result.out_dir)
    # B2/<bolge (N evrak, X kg)>/Palet (N evrak) (fixture varsayilan koli=10 -> Palet)
    assert len(list((out_dir / "B2" / "Adana (2 evrak, 200 kg)" / "Palet (2 evrak)").glob("*.pdf"))) == 2
    assert len(list((out_dir / "B2" / "Ankara (1 evrak, 100 kg)" / "Palet (1 evrak)").glob("*.pdf"))) == 1


def test_region_stats_error_rows_and_overview(monkeypatch, tmp_path, make_pdf):
    # Arayuzun Ozet/Bolgeler/Hata ekranlarinin bagli oldugu saf-python
    # yardimcilar: pipeline'in kararlarini (result.targets) tekrar etmeden
    # dogru gruplayip gercek verilerle KPI/kova/en-buyuk-alici uretmeli.
    repo_root = Path(__file__).resolve().parent.parent
    monkeypatch.setattr(gui, "config_path", lambda: repo_root / "config" / "regions.yaml")
    monkeypatch.setattr(gui, "default_output_dir", lambda: tmp_path / "out")

    gelen = tmp_path / "Gelen"
    gelen.mkdir()
    make_pdf(gelen / "a1.pdf", il="ADANA", koli=12, brut_agirlik="120 kg")  # Palet (>=9)
    make_pdf(gelen / "a2.pdf", il="ADANA", koli=3, brut_agirlik="30 kg")  # Dökme (<=8)
    make_pdf(gelen / "ank.pdf", il="ANKARA", koli=5, brut_agirlik="50 kg")
    make_pdf(gelen / "bad.pdf", il="ADANA", koli=None)  # koli okunamadı -> Hata

    result = gui.run_split(gelen, shift_name="StatsTest")

    regions = gui.region_stats(result, None)
    by_name = {r["ad"]: r for r in regions}
    assert by_name["Adana"]["evrak"] == 2
    assert by_name["Adana"]["koli"] == 15
    assert by_name["Adana"]["kg"] == Decimal("150")
    assert by_name["Adana"]["palet"] == 1
    assert by_name["Adana"]["dokme"] == 1
    assert by_name["Adana"]["top"] == "A101 ADANA"
    assert by_name["Ankara"]["evrak"] == 1

    rows = gui.error_rows(result)
    assert len(rows) == 1
    assert rows[0]["neden"] == "Koli adedi okunamadı"

    overview = gui.build_overview(result, regions)
    assert overview.b2_total == 3
    assert overview.palet == 1
    assert overview.dokme == 2
    kpi_by_label = {k["label"]: k for k in overview.kpis}
    assert kpi_by_label["HATA"]["value"] == "1"
    assert kpi_by_label["BÖLGE"]["value"] == "2"
    assert kpi_by_label["TOPLAM EVRAK"]["value"] == "4"

