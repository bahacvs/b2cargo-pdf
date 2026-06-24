"""GUI'nin Tk'dan bagimsiz mantik katmani testleri (pencere acilmadan)."""

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
    # Bolge KLASORLERI + icinde ayri PDF'ler
    assert (out_dir / "Adana").is_dir()
    assert len(list((out_dir / "Adana").glob("*.pdf"))) == 2
    assert (out_dir / "Ankara").is_dir()
    assert len(list((out_dir / "Ankara").glob("*.pdf"))) == 1
