"""PDF metin cikarma.

Her irsaliye kendi PDF dosyasidir (bir dosya = bir irsaliye). Dosya birden
cok sayfa icerebilir; tum sayfalarin metni birlestirilerek dondurulur.

PDF'ler metin tabanli (dijital) varsayilir. Metin bos gelirse cagiran taraf
bunu "adres okunamadi" hatasi olarak ele alir (ileride OCR fallback noktasi).
"""

from __future__ import annotations

import pdfplumber


def extract_text(pdf_path: str) -> str:
    """Bir PDF dosyasinin tum sayfalarindaki metni tek string olarak dondurur."""
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts).strip()
