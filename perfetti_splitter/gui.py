"""Masaustu arayuz (Tkinter).

Cekirdek mantigi degistirmez; `pipeline.run` uzerine ince bir gorsel
sarmalayicidir (cli.main ile ayni akis). Tek `.exe` olarak paketlenmek uzere
tasarlandi: yol cozumleri hem kaynaktan calistirmada hem PyInstaller donmus
exe'de dogru calisir.

Tk'dan bagimsiz yardimcilar (base_dir / config_path / run_split) ayri
tutulur ki ekran gerektirmeden test edilebilsin.
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

from .pipeline import PipelineResult, run
from .regions import DsvMatcher, RegionMap


# --- Tk'dan bagimsiz yardimcilar (test edilebilir) -------------------------

def base_dir() -> Path:
    """Uygulamanin calistigi temel klasor.

    PyInstaller ile donmus exe'de exe'nin bulundugu klasor; kaynaktan
    calistirmada repo koku. Kullanici duzenleyebilir dosyalar (config,
    Gelen_PDF, cikti) buna gore cozulur.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """PyInstaller paketinin gomulu kaynak klasoru (varsa); yoksa base_dir."""
    return Path(getattr(sys, "_MEIPASS", base_dir()))


def config_path() -> Path:
    """Bolge haritasi YAML yolu.

    Once exe/repo yanindaki `config/regions.yaml` (kullanici exe'yi yeniden
    derlemeden duzenleyebilsin); yoksa pakete gomulu varsayilan kopya.
    """
    external = base_dir() / "config" / "regions.yaml"
    if external.exists():
        return external
    return resource_dir() / "config" / "regions.yaml"


def dsv_path() -> Path:
    """DSV lokasyon listesi YAML yolu (exe/repo yani; yoksa pakete gomulu)."""
    external = base_dir() / "config" / "dsv_lokasyonlar.yaml"
    if external.exists():
        return external
    return resource_dir() / "config" / "dsv_lokasyonlar.yaml"


def default_input_dir() -> Path:
    return base_dir() / "Gelen_PDF"


def default_output_dir() -> Path:
    return base_dir() / "Birlesik_PDF"


def run_split(input_dir: str | Path, shift_name: str | None = None) -> PipelineResult:
    """Bolge haritasi + DSV listesini yukleyip pipeline'i calistirir."""
    region_map = RegionMap.from_yaml(str(config_path()))
    dsv = DsvMatcher.from_yaml(str(dsv_path())) if dsv_path().exists() else None
    return run(
        input_dir, default_output_dir(), region_map,
        shift_name=shift_name, dsv_matcher=dsv,
    )


def open_in_explorer(path: str | Path) -> None:
    """Bir klasor/dosyayi isletim sisteminin dosya gezgininde acar."""
    path = str(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


# --- Tkinter arayuzu -------------------------------------------------------

def main() -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("Perfetti Vardiya Ayirma")
    root.geometry("640x560")
    root.minsize(560, 480)

    pad = {"padx": 12, "pady": 6}
    last_result: dict[str, PipelineResult | None] = {"r": None}

    # Baslik
    tk.Label(
        root, text="Perfetti Vardiya Ayirma", font=("Segoe UI", 16, "bold")
    ).pack(**pad)

    # Config cakisma uyarisi (varsa)
    try:
        rm = RegionMap.from_yaml(str(config_path()))
        if rm.conflicts:
            tk.Label(
                root,
                text="Uyari: birden cok bolgeye dusen sehir(ler): "
                + ", ".join(sorted(rm.conflicts))
                + "\nBu sehirlerdeki belgeler Hata'ya gonderilir.",
                fg="#b15c00",
                justify="left",
            ).pack(**pad)
    except Exception as exc:  # config okunamadi -> kullaniciya bildir
        messagebox.showerror(
            "Bolge haritasi okunamadi",
            f"config/regions.yaml acilamadi:\n{exc}",
        )

    # Klasor secimi
    frm = tk.Frame(root)
    frm.pack(fill="x", **pad)
    tk.Label(frm, text="Irsaliye klasoru:").pack(anchor="w")
    row = tk.Frame(frm)
    row.pack(fill="x")
    folder_var = tk.StringVar(value=str(default_input_dir()))
    entry = tk.Entry(row, textvariable=folder_var)
    entry.pack(side="left", fill="x", expand=True)

    def pick_folder() -> None:
        start = folder_var.get() if Path(folder_var.get()).is_dir() else str(base_dir())
        chosen = filedialog.askdirectory(initialdir=start, title="Irsaliye klasorunu sec")
        if chosen:
            folder_var.set(chosen)

    tk.Button(row, text="Klasor Sec...", command=pick_folder).pack(side="left", padx=6)

    # Vardiya adi
    frm2 = tk.Frame(root)
    frm2.pack(fill="x", **pad)
    tk.Label(frm2, text="Vardiya adi (bos = otomatik tarih):").pack(anchor="w")
    name_var = tk.StringVar(value="")
    tk.Entry(frm2, textvariable=name_var).pack(fill="x")

    # Durum + ilerleme
    status_var = tk.StringVar(value="Hazir.")
    status_lbl = tk.Label(root, textvariable=status_var, fg="#333")
    status_lbl.pack(**pad)
    progress = ttk.Progressbar(root, mode="indeterminate")

    # Sonuc alani
    result_box = tk.Text(root, height=12, width=64, state="disabled", font=("Consolas", 10))
    result_box.pack(fill="both", expand=True, **pad)

    # Cikti butonlari
    btns = tk.Frame(root)
    btns.pack(fill="x", **pad)
    open_out_btn = tk.Button(btns, text="Cikti Klasorunu Ac", state="disabled")
    open_out_btn.pack(side="left")
    open_err_btn = tk.Button(btns, text="Hata Raporunu Ac", state="disabled")
    open_err_btn.pack(side="left", padx=6)
    rescan_btn = tk.Button(btns, text="Hata Klasorunu Tekrar Tara", state="disabled")
    rescan_btn.pack(side="left")

    def set_result_text(text: str) -> None:
        result_box.configure(state="normal")
        result_box.delete("1.0", "end")
        result_box.insert("1.0", text)
        result_box.configure(state="disabled")

    def on_done(result: PipelineResult | None, error: Exception | None) -> None:
        progress.stop()
        progress.pack_forget()
        ayir_btn.configure(state="normal")
        if error is not None:
            status_var.set("Hata olustu.")
            messagebox.showerror("Hata", f"Islem sirasinda hata olustu:\n{error}")
            return
        assert result is not None
        last_result["r"] = result
        status_var.set("Tamamlandi.")
        set_result_text(result.summary + f"\n\nCikti klasoru:\n{result.out_dir}")
        open_out_btn.configure(state="normal")
        has_err = bool(result.error_count)
        open_err_btn.configure(state="normal" if has_err else "disabled")
        rescan_btn.configure(state="normal" if has_err else "disabled")

    def worker(input_dir: str, shift_name: str | None) -> None:
        try:
            result = run_split(input_dir, shift_name)
            root.after(0, lambda: on_done(result, None))
        except Exception as exc:  # thread icinden UI'ya guvenli aktar
            root.after(0, lambda: on_done(None, exc))

    def start() -> None:
        input_dir = folder_var.get().strip()
        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showwarning(
                "Klasor yok",
                "Lutfen gecerli bir irsaliye klasoru secin.",
            )
            return
        pdfs = list(Path(input_dir).glob("*.pdf"))
        if not pdfs:
            messagebox.showwarning(
                "PDF yok",
                f"Secili klasorde PDF bulunamadi:\n{input_dir}",
            )
            return
        ayir_btn.configure(state="disabled")
        open_out_btn.configure(state="disabled")
        open_err_btn.configure(state="disabled")
        rescan_btn.configure(state="disabled")
        set_result_text("")
        status_var.set(f"{len(pdfs)} PDF isleniyor, lutfen bekleyin...")
        progress.pack(fill="x", padx=12)
        progress.start(12)
        threading.Thread(
            target=worker,
            args=(input_dir, name_var.get().strip() or None),
            daemon=True,
        ).start()

    def open_output() -> None:
        r = last_result["r"]
        if r:
            open_in_explorer(r.out_dir)

    def open_error_report() -> None:
        r = last_result["r"]
        if r and r.error_count:
            open_in_explorer(str(Path(r.out_dir) / "Hata" / "Hata_raporu.csv"))

    def rescan_errors() -> None:
        # config/regions.yaml duzeltildikten sonra Hata klasorunu yeniden isle.
        r = last_result["r"]
        if not r or not r.error_count:
            return
        hata_dir = Path(r.out_dir) / "Hata"
        if not hata_dir.is_dir():
            messagebox.showwarning("Hata klasoru yok", f"Bulunamadi:\n{hata_dir}")
            return
        folder_var.set(str(hata_dir))
        name_var.set("Hata_tekrar")
        start()

    open_out_btn.configure(command=open_output)
    open_err_btn.configure(command=open_error_report)
    rescan_btn.configure(command=rescan_errors)

    ayir_btn = tk.Button(
        root, text="AYIR", command=start,
        font=("Segoe UI", 13, "bold"), bg="#1565c0", fg="white",
        activebackground="#0d47a1", height=2,
    )
    ayir_btn.pack(fill="x", padx=12, pady=10)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
