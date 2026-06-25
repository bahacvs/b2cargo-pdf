"""Komut satiri arayuzu.

Kullanim:
    python -m perfetti_splitter <gelen_klasor> [--config ...] [--outdir ...] [--name ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import run
from .regions import DsvMatcher, RegionMap

# config/*.yaml -> repo kokunden goreceli varsayilan yollar
_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_DEFAULT_CONFIG = _CONFIG_DIR / "regions.yaml"
_DEFAULT_DSV = _CONFIG_DIR / "dsv_lokasyonlar.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="perfetti-splitter",
        description="Perfetti Van Melle e-irsaliye PDF'lerini bolgelere ayirip birlestirir.",
    )
    parser.add_argument("input_dir", help="Irsaliye PDF'lerinin bulundugu klasor")
    parser.add_argument(
        "--config",
        default=str(_DEFAULT_CONFIG),
        help="Bolge haritasi YAML yolu (varsayilan: config/regions.yaml)",
    )
    parser.add_argument(
        "--outdir",
        default="workdir/Birlesik_PDF",
        help="Cikti taban klasoru (varsayilan: workdir/Birlesik_PDF)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Vardiya adi (varsayilan: gelen klasor adi)",
    )
    parser.add_argument(
        "--dsv",
        default=str(_DEFAULT_DSV),
        help="DSV lokasyon listesi YAML yolu (varsayilan: config/dsv_lokasyonlar.yaml)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    region_map = RegionMap.from_yaml(args.config)
    if region_map.conflicts:
        sys.stderr.write(
            "UYARI: config'te birden cok bolgeye dusen sehir(ler): "
            + ", ".join(sorted(region_map.conflicts)) + "\n"
            "       Bu sehirlerdeki belgeler Hata'ya gonderilecek (tahmin yok).\n"
        )

    dsv_matcher = (
        DsvMatcher.from_yaml(args.dsv) if Path(args.dsv).exists() else None
    )

    result = run(
        args.input_dir, args.outdir, region_map,
        shift_name=args.name, dsv_matcher=dsv_matcher,
    )

    print(result.summary)
    print(f"\nCikti klasoru: {result.out_dir}")
    if result.error_count:
        print(f"Hata raporu:   {Path(result.out_dir) / 'Hata' / 'Hata_raporu.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
