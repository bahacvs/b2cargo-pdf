"""PyInstaller / .exe giris noktasi.

Paketi MUTLAK import ile yukler. Dogrudan alt-modul (perfetti_splitter/gui.py)
calistirildiginda goreli import'lar "no known parent package" hatasi verdigi
icin bu sarmalayici kullanilir. Boylece exe sorunsuz acilir.
"""

from perfetti_splitter.gui import main

if __name__ == "__main__":
    raise SystemExit(main())
