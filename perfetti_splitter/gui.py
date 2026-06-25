"""Masaustu arayuz (CustomTkinter - modern tema).

Cekirdek mantigi degistirmez; `pipeline.run` uzerine ince bir gorsel
sarmalayicidir (cli.main ile ayni akis). Tek `.exe` olarak paketlenmek uzere
tasarlandi: yol cozumleri hem kaynaktan calistirmada hem PyInstaller donmus
exe'de dogru calisir.

Tk'dan bagimsiz yardimcilar (base_dir / config_path / dsv_path / run_split)
ayri tutulur ki ekran gerektirmeden test edilebilsin. customtkinter yalnizca
main() icinde (lazy) import edilir; boylece modul importu bu bagimliligi
gerektirmez ve testler etkilenmez.
"""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime
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


def icon_path() -> Path:
    """Uygulama simgesi (.ico) yolu; exe yani veya pakete gomulu."""
    external = base_dir() / "assets" / "app.ico"
    if external.exists():
        return external
    return resource_dir() / "assets" / "app.ico"


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


# --- CustomTkinter arayuzu -------------------------------------------------

# Renkler (acik/koyu tema icin (light, dark) ciftleri)
_ACCENT = ("#1565c0", "#1f6feb")
_ACCENT_HOVER = ("#0d47a1", "#388bfd")
_CARD = ("#f2f4f8", "#1e2229")
_OK = ("#1b7f4b", "#2ea043")
_WARN = ("#c0392b", "#f85149")
_MUTED = ("gray40", "gray60")


def main() -> int:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Perfetti Vardiya Ayırıcı")
    root.geometry("780x680")
    root.minsize(680, 600)
    try:
        if icon_path().exists():
            root.iconbitmap(str(icon_path()))
    except Exception:
        pass  # simge yoksa/desteklenmiyorsa onemli degil

    last_result: dict[str, PipelineResult | None] = {"r": None}
    FONT = "Segoe UI"

    # ---- Ust baslik serisi ----
    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=24, pady=(20, 6))
    title_box = ctk.CTkFrame(header, fg_color="transparent")
    title_box.pack(side="left", anchor="w")
    ctk.CTkLabel(
        title_box, text="Perfetti Vardiya Ayırıcı",
        font=ctk.CTkFont(family=FONT, size=24, weight="bold"),
    ).pack(anchor="w")
    ctk.CTkLabel(
        title_box, text="B2  ·  DSV  irsaliye ayırma",
        font=ctk.CTkFont(family=FONT, size=13), text_color=_MUTED,
    ).pack(anchor="w")

    def toggle_theme() -> None:
        ctk.set_appearance_mode("dark" if theme_switch.get() else "light")

    theme_switch = ctk.CTkSwitch(
        header, text="Koyu tema", command=toggle_theme,
        font=ctk.CTkFont(family=FONT, size=12),
    )
    theme_switch.pack(side="right", anchor="e", pady=8)

    # ---- Config cakisma uyarisi (varsa) ----
    try:
        rm = RegionMap.from_yaml(str(config_path()))
        if rm.conflicts:
            ctk.CTkLabel(
                root,
                text="⚠ Birden çok bölgeye düşen şehir(ler): "
                + ", ".join(sorted(rm.conflicts))
                + "  → bu belgeler Hata'ya gönderilir.",
                font=ctk.CTkFont(family=FONT, size=12),
                text_color=_WARN, anchor="w", justify="left",
            ).pack(fill="x", padx=24, pady=(0, 4))
    except Exception as exc:
        messagebox.showerror("Bölge haritası okunamadı",
                             f"config/regions.yaml açılamadı:\n{exc}")

    # ---- Giris karti (klasor + vardiya adi) ----
    card = ctk.CTkFrame(root, corner_radius=14, fg_color=_CARD)
    card.pack(fill="x", padx=24, pady=10)

    ctk.CTkLabel(card, text="İrsaliye klasörü",
                 font=ctk.CTkFont(family=FONT, size=13, weight="bold")
                 ).grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 2))
    folder_var = ctk.StringVar(value=str(default_input_dir()))
    folder_entry = ctk.CTkEntry(card, textvariable=folder_var, height=38,
                                font=ctk.CTkFont(family=FONT, size=12))
    folder_entry.grid(row=1, column=0, sticky="ew", padx=(16, 8), pady=2)

    def pick_folder() -> None:
        start_dir = folder_var.get() if Path(folder_var.get()).is_dir() else str(base_dir())
        chosen = filedialog.askdirectory(initialdir=start_dir, title="İrsaliye klasörünü seç")
        if chosen:
            folder_var.set(chosen)

    ctk.CTkButton(card, text="Klasör Seç", width=120, height=38, command=pick_folder,
                  font=ctk.CTkFont(family=FONT, size=12)
                  ).grid(row=1, column=1, padx=(0, 16), pady=2)

    ctk.CTkLabel(card, text="Vardiya adı (boş = otomatik tarih)",
                 font=ctk.CTkFont(family=FONT, size=13, weight="bold")
                 ).grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(10, 2))
    name_var = ctk.StringVar(value="")
    ctk.CTkEntry(card, textvariable=name_var, height=38,
                 font=ctk.CTkFont(family=FONT, size=12)
                 ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(2, 16))
    card.grid_columnconfigure(0, weight=1)

    # ---- AYIR butonu ----
    ayir_btn = ctk.CTkButton(
        root, text="A Y I R", height=52, corner_radius=12,
        fg_color=_ACCENT, hover_color=_ACCENT_HOVER,
        font=ctk.CTkFont(family=FONT, size=18, weight="bold"),
    )
    ayir_btn.pack(fill="x", padx=24, pady=(4, 8))

    # ---- Durum + ilerleme ----
    status_var = ctk.StringVar(value="Hazır.")
    ctk.CTkLabel(root, textvariable=status_var, text_color=_MUTED,
                 font=ctk.CTkFont(family=FONT, size=12)).pack(padx=24, anchor="w")
    progress = ctk.CTkProgressBar(root, mode="indeterminate", height=8)

    # ---- Sonuc: ozet kartlari + bolge listesi ----
    stats = ctk.CTkFrame(root, fg_color="transparent")
    stats.pack(fill="x", padx=24, pady=(8, 4))
    regions_box = ctk.CTkScrollableFrame(root, corner_radius=12, fg_color=_CARD,
                                         label_text="Bölge dağılımı")
    regions_box.pack(fill="both", expand=True, padx=24, pady=(4, 8))

    def _stat_card(parent, baslik, sayi, renk):
        c = ctk.CTkFrame(parent, corner_radius=12, fg_color=_CARD)
        c.pack(side="left", expand=True, fill="x", padx=4)
        ctk.CTkLabel(c, text=str(sayi), text_color=renk,
                     font=ctk.CTkFont(family=FONT, size=26, weight="bold")
                     ).pack(pady=(12, 0))
        ctk.CTkLabel(c, text=baslik, text_color=_MUTED,
                     font=ctk.CTkFont(family=FONT, size=12)).pack(pady=(0, 12))

    def render_results(result: PipelineResult) -> None:
        for w in stats.winfo_children():
            w.destroy()
        for w in regions_box.winfo_children():
            w.destroy()
        b2_total = sum(result.region_counts.values())
        _stat_card(stats, "B2 evrak", b2_total, _ACCENT)
        _stat_card(stats, "DSV evrak", result.dsv_count, _OK)
        _stat_card(stats, "Hata", result.error_count,
                   _WARN if result.error_count else _MUTED)
        for region in sorted(result.region_counts):
            rowf = ctk.CTkFrame(regions_box, fg_color="transparent")
            rowf.pack(fill="x", padx=6, pady=1)
            ctk.CTkLabel(rowf, text=region, anchor="w",
                         font=ctk.CTkFont(family=FONT, size=13)).pack(side="left")
            ctk.CTkLabel(rowf, text=f"{result.region_counts[region]} evrak", anchor="e",
                         text_color=_MUTED,
                         font=ctk.CTkFont(family=FONT, size=13)).pack(side="right")

    # ---- Aksiyon butonlari ----
    btns = ctk.CTkFrame(root, fg_color="transparent")
    btns.pack(fill="x", padx=24, pady=(0, 18))
    open_out_btn = ctk.CTkButton(btns, text="Çıktıyı Aç", state="disabled", height=40,
                                 font=ctk.CTkFont(family=FONT, size=12))
    open_out_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))
    open_report_btn = ctk.CTkButton(btns, text="Vardiya Raporu", state="disabled", height=40,
                                    font=ctk.CTkFont(family=FONT, size=12))
    open_report_btn.pack(side="left", expand=True, fill="x", padx=6)
    open_err_btn = ctk.CTkButton(btns, text="Hata Raporu", state="disabled", height=40,
                                 fg_color=_WARN, hover_color="#922b21",
                                 font=ctk.CTkFont(family=FONT, size=12))
    open_err_btn.pack(side="left", expand=True, fill="x", padx=6)
    rescan_btn = ctk.CTkButton(btns, text="Hata Klasörünü Tekrar Tara", state="disabled",
                               height=40, fg_color="transparent", border_width=1,
                               text_color=_ACCENT,
                               font=ctk.CTkFont(family=FONT, size=12))
    rescan_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

    # ---- Callback'ler (mantik aynen korunur) ----
    def on_done(result: PipelineResult | None, error: Exception | None) -> None:
        progress.stop()
        progress.pack_forget()
        ayir_btn.configure(state="normal")
        if error is not None:
            status_var.set("Hata oluştu.")
            messagebox.showerror("Hata", f"İşlem sırasında hata oluştu:\n{error}")
            return
        assert result is not None
        last_result["r"] = result
        total = sum(result.region_counts.values()) + result.dsv_count + result.error_count
        status_var.set(f"Tamamlandı — {total} evrak işlendi.  Çıktı: {result.out_dir}")
        render_results(result)
        open_out_btn.configure(state="normal")
        open_report_btn.configure(state="normal")
        has_err = bool(result.error_count)
        open_err_btn.configure(state="normal" if has_err else "disabled")
        rescan_btn.configure(state="normal" if has_err else "disabled")

    def worker(input_dir: str, shift_name: str | None) -> None:
        try:
            result = run_split(input_dir, shift_name)
            root.after(0, lambda: on_done(result, None))
        except Exception as exc:
            root.after(0, lambda: on_done(None, exc))

    def start() -> None:
        input_dir = folder_var.get().strip()
        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showwarning("Klasör yok", "Lütfen geçerli bir irsaliye klasörü seçin.")
            return
        pdfs = list(Path(input_dir).glob("*.pdf"))
        if not pdfs:
            messagebox.showwarning("PDF yok", f"Seçili klasörde PDF bulunamadı:\n{input_dir}")
            return
        for b in (ayir_btn, open_out_btn, open_report_btn, open_err_btn, rescan_btn):
            b.configure(state="disabled")
        status_var.set(f"{len(pdfs)} PDF işleniyor, lütfen bekleyin…")
        progress.pack(fill="x", padx=24, pady=(2, 6))
        progress.start()
        threading.Thread(target=worker,
                         args=(input_dir, name_var.get().strip() or None),
                         daemon=True).start()

    def open_output() -> None:
        r = last_result["r"]
        if r:
            open_in_explorer(r.out_dir)

    def open_shift_report() -> None:
        r = last_result["r"]
        if r:
            open_in_explorer(str(Path(r.out_dir) / "vardiya_raporu.csv"))

    def open_error_report() -> None:
        r = last_result["r"]
        if r and r.error_count:
            open_in_explorer(str(Path(r.out_dir) / "Hata" / "Hata_raporu.csv"))

    def rescan_errors() -> None:
        r = last_result["r"]
        if not r or not r.error_count:
            return
        hata_dir = Path(r.out_dir) / "Hata"
        if not hata_dir.is_dir():
            messagebox.showwarning("Hata klasörü yok", f"Bulunamadı:\n{hata_dir}")
            return
        folder_var.set(str(hata_dir))
        stamp = datetime.now().strftime("%H%M%S")
        name_var.set(f"Hata_tekrar_{stamp}")
        start()

    ayir_btn.configure(command=start)
    open_out_btn.configure(command=open_output)
    open_report_btn.configure(command=open_shift_report)
    open_err_btn.configure(command=open_error_report)
    rescan_btn.configure(command=rescan_errors)

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
