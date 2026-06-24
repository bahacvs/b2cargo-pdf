"""Bolge bazinda cikti: her bolge icin bir KLASOR, icine ayri PDF'ler.

Bir dosya = bir irsaliye oldugu icin birlestirme yapilmaz; her irsaliye
PDF'i ilgili bolge klasorune anlamli bir adla (`{alici} - {PVS}.pdf`)
kopyalanir. Orijinal PDF birebir korunur (shutil.copy2).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import Document

# Windows'ta dosya adinda gecersiz karakterler.
_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')
_MAX_STEM = 100


def safe_filename(name: str) -> str:
    """Bir metni Windows-guvenli dosya adi kokune cevirir (uzantisiz)."""
    name = _INVALID_CHARS.sub(" ", name)
    name = " ".join(name.split())          # bosluklari sadelestir
    name = name.strip(" .")                 # bas/sondaki nokta-bosluk
    if len(name) > _MAX_STEM:
        name = name[:_MAX_STEM].strip()
    return name or "irsaliye"


def doc_filename(doc: "Document") -> str:
    """Belge icin '{alici} - {PVS}.pdf' dosya adi.

    Alici yoksa orijinal dosya adi koku; PVS yoksa eklenmez.
    """
    recipient = (doc.recipient or "").strip()
    stem = safe_filename(recipient) if recipient else Path(doc.path).stem
    if doc.pvs:
        stem = f"{stem} - {doc.pvs}"
    return safe_filename(stem) + ".pdf"


def _unique_dest(folder: Path, filename: str) -> Path:
    """Klasor icinde ad cakismasini ' (2)', ' (3)' ekleyerek cozer."""
    dest = folder / filename
    if not dest.exists():
        return dest
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    i = 2
    while True:
        cand = folder / f"{stem} ({i}){suffix}"
        if not cand.exists():
            return cand
        i += 1


def copy_docs(docs: list["Document"], folder: str | Path) -> list[str]:
    """Belgeleri verilen klasore (yoksa olusturur) anlamli adlarla kopyalar.

    Donen: yazilan dosya yollari. Okunamayan/eksik kaynak atlanir.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for doc in docs:
        src = Path(doc.path)
        if not src.exists():
            continue
        dest = _unique_dest(folder, doc_filename(doc))
        shutil.copy2(src, dest)
        written.append(str(dest))
    return written


def write_region_folders(
    grouped: dict[str, list["Document"]], out_dir: str | Path
) -> dict[str, list[str]]:
    """grouped: bolge -> Document listesi. Her bolge icin bir alt klasor acar.

    Donen: bolge -> yazilan dosya yollari.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, list[str]] = {}
    for region, docs in grouped.items():
        if not docs:
            continue
        written[region] = copy_docs(docs, out_dir / region)
    return written
