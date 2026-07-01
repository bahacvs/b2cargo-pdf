"""Pipeline'in tek belgedeki beklenmeyen hatayi izole ettigini dogrular.

Onceden `_process_one_document` yalnizca PDF okuma hatasini yakaliyordu;
ayristirma/bolge tespiti sirasinda beklenmeyen bir hata cikarsa butun
vardiyanin (o ana kadar basariyla islenmis diger belgeler dahil) sonucu
kayboluyordu. Artik boyle bir hata yalnizca o belgeyi Hata'ya dusurmeli,
digerlerini etkilememeli.
"""

from __future__ import annotations

from pathlib import Path

import perfetti_splitter.pipeline as pipeline
from perfetti_splitter.regions import RegionMap


def test_unexpected_parse_error_isolated_to_one_document(tmp_path, monkeypatch, make_pdf):
    gelen = tmp_path / "Gelen"
    gelen.mkdir()
    make_pdf(gelen / "good1.pdf", il="ADANA")
    make_pdf(gelen / "boom.pdf", il="ADANA")
    make_pdf(gelen / "good2.pdf", il="ANKARA")

    real_parse_document = pipeline.parse_document

    def flaky_parse_document(path, text):
        if Path(path).name == "boom.pdf":
            raise RuntimeError("beklenmeyen ayristirma hatasi")
        return real_parse_document(path, text)

    monkeypatch.setattr(pipeline, "parse_document", flaky_parse_document)

    repo_root = Path(__file__).resolve().parent.parent
    region_map = RegionMap.from_yaml(str(repo_root / "config" / "regions.yaml"))

    result = pipeline.run(gelen, tmp_path / "out", region_map, shift_name="FlakyTest")

    # Sorunsuz iki belge normal islenmis olmali (batch iptal olmamis).
    assert result.region_counts.get("Adana") == 1
    assert result.region_counts.get("Ankara") == 1
    # Sorunlu belge Hata'ya dusmus, nedeni goruntulenebilir olmali.
    assert result.error_count == 1
    boom_doc = next(d for d in result.documents if Path(d.path).name == "boom.pdf")
    assert any("işlenemedi" in e for e in boom_doc.errors)
