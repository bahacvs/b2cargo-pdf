"""Masaustu arayuz (CustomTkinter - profesyonel konsol tema).

Cekirdek mantigi degistirmez; `pipeline.run` uzerine ince bir gorsel
sarmalayicidir. Tk'dan bagimsiz yardimcilar ayri tutulur ki ekran
gerektirmeden test edilebilsin.
"""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from .pipeline import PipelineResult, run
from .regions import DsvMatcher, RegionMap


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", base_dir()))


def config_path() -> Path:
    external = base_dir() / "config" / "regions.yaml"
    if external.exists():
        return external
    return resource_dir() / "config" / "regions.yaml"


def dsv_path() -> Path:
    external = base_dir() / "config" / "dsv_lokasyonlar.yaml"
    if external.exists():
        return external
    return resource_dir() / "config" / "dsv_lokasyonlar.yaml"


def icon_path() -> Path:
    external = base_dir() / "assets" / "app.ico"
    if external.exists():
        return external
    return resource_dir() / "assets" / "app.ico"


def default_input_dir() -> Path:
    return base_dir() / "Gelen_PDF"


def default_output_dir() -> Path:
    return base_dir() / "Birlesik_PDF"


def run_split(
    input_dir: str | Path,
    shift_name: str | None = None,
    progress_callback=None,
) -> PipelineResult:
    region_map = RegionMap.from_yaml(str(config_path()))
    dsv = DsvMatcher.from_yaml(str(dsv_path())) if dsv_path().exists() else None
    return run(
        input_dir,
        default_output_dir(),
        region_map,
        shift_name=shift_name,
        dsv_matcher=dsv,
        progress_callback=progress_callback,
    )


def open_in_explorer(path: str | Path) -> None:
    path = str(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


_BG = "#080d22"
_PANEL = "#141b3d"
_PANEL_2 = "#0f1636"
_PANEL_3 = "#192147"
_BORDER = "#28315e"
_FG = "#ebf0ff"
_MUTED = "#94a0c6"
_BRAND = "#33489e"
_BRAND_HOVER = "#4057bb"
_ORANGE = "#f26a21"
_ORANGE_HOVER = "#d95b1a"
_GOLD = "#fba61c"
_OK = "#37c98b"
_WARN = "#f0b23e"
_BAD = "#f26d6d"


def main() -> int:
    import customtkinter as ctk
    from tkinter import filedialog, messagebox

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Perfetti Vardiya Ayırma - B2Cargo")
    root.geometry("1180x740")
    root.minsize(1020, 660)
    root.configure(fg_color=_BG)
    try:
        if icon_path().exists():
            root.iconbitmap(str(icon_path()))
    except Exception:
        pass

    FONT = "Segoe UI"
    last_result: dict[str, PipelineResult | None] = {"r": None}
    views: dict[str, ctk.CTkFrame] = {}
    nav_buttons: dict[str, ctk.CTkButton] = {}

    def font(size: int, weight: str = "normal"):
        return ctk.CTkFont(family=FONT, size=size, weight=weight)

    def title_font(size: int):
        return ctk.CTkFont(family=FONT, size=size, weight="bold")

    def mono_font(size: int, weight: str = "normal"):
        return ctk.CTkFont(family="Consolas", size=size, weight=weight)

    def card(parent, fg_color: str = _PANEL, border_color: str = _BORDER):
        return ctk.CTkFrame(
            parent,
            fg_color=fg_color,
            border_color=border_color,
            border_width=1,
            corner_radius=8,
        )

    def entry(parent, **kwargs):
        return ctk.CTkEntry(
            parent,
            fg_color=_PANEL_2,
            border_color=_BORDER,
            text_color=_FG,
            placeholder_text_color=_MUTED,
            font=font(12),
            **kwargs,
        )

    def metric(parent, value: str, label: str, color: str):
        frame = card(parent)
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=value, text_color=color, anchor="w", font=title_font(28)).grid(
            row=0, column=0, sticky="ew", padx=18, pady=(16, 0)
        )
        ctk.CTkLabel(frame, text=label, text_color=_MUTED, anchor="w", font=font(12, "bold")).grid(
            row=1, column=0, sticky="ew", padx=18, pady=(0, 16)
        )
        return frame

    def open_region_settings() -> None:
        win = ctk.CTkToplevel(root)
        win.title("Bölge Ayarları")
        win.geometry("820x640")
        win.minsize(680, 500)
        win.configure(fg_color=_BG)
        win.transient(root)

        target = base_dir() / "config" / "regions.yaml"
        try:
            initial = config_path().read_text(encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Bölge ayarları", f"regions.yaml okunamadı:\n{exc}")
            win.destroy()
            return

        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(18, 10))
        ctk.CTkLabel(top, text="Bölge Ayarları", text_color=_FG, font=title_font(22)).pack(side="left")
        ctk.CTkLabel(top, text="regions.yaml", text_color=_MUTED, font=mono_font(12)).pack(side="right")

        editor = ctk.CTkTextbox(
            win,
            wrap="none",
            fg_color=_PANEL_2,
            border_color=_BORDER,
            border_width=1,
            text_color=_FG,
            corner_radius=8,
            font=mono_font(12),
        )
        editor.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        editor.insert("1.0", initial)

        status = ctk.StringVar(value=f"Dosya: {target}")
        ctk.CTkLabel(win, textvariable=status, anchor="w", text_color=_MUTED, font=font(12)).pack(
            fill="x", padx=20, pady=(0, 10)
        )
        actions = ctk.CTkFrame(win, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 16))

        def validate_text(text: str) -> RegionMap:
            import yaml

            data = yaml.safe_load(text) or {}
            if not isinstance(data, dict):
                raise ValueError("YAML kök seviyesi bölge listesi olmalı.")
            return RegionMap(data)

        def validate_regions() -> None:
            try:
                rm = validate_text(editor.get("1.0", "end-1c"))
            except Exception as exc:
                status.set(f"YAML hatası: {exc}")
                return
            status.set(
                "Çakışma var: " + ", ".join(sorted(rm.conflicts))
                if rm.conflicts
                else "YAML geçerli. Çakışma yok."
            )

        def save_regions() -> None:
            text = editor.get("1.0", "end-1c")
            try:
                rm = validate_text(text)
            except Exception as exc:
                messagebox.showerror("Bölge ayarları", f"YAML doğrulanamadı:\n{exc}")
                return
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            status.set("Kaydedildi. Çakışma var: " + ", ".join(sorted(rm.conflicts)) if rm.conflicts else "Kaydedildi. Çakışma yok.")
            messagebox.showinfo("Bölge ayarları", "Bölge ayarları kaydedildi.")

        ctk.CTkButton(actions, text="Doğrula", height=38, fg_color=_BRAND, hover_color=_BRAND_HOVER, command=validate_regions).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Kaydet", height=38, fg_color=_ORANGE, hover_color=_ORANGE_HOVER, command=save_regions).pack(side="left", padx=(0, 8))
        ctk.CTkButton(actions, text="Kapat", height=38, fg_color="transparent", border_width=1, border_color=_BORDER, text_color=_FG, command=win.destroy).pack(side="right")

    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(0, weight=1)

    sidebar = ctk.CTkFrame(root, width=246, fg_color=_PANEL_2, corner_radius=0)
    sidebar.grid(row=0, column=0, sticky="nsew")
    sidebar.grid_propagate(False)
    sidebar.grid_rowconfigure(3, weight=1)

    content = ctk.CTkFrame(root, fg_color=_BG, corner_radius=0)
    content.grid(row=0, column=1, sticky="nsew")
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(1, weight=1)

    brand = ctk.CTkFrame(sidebar, fg_color="transparent")
    brand.grid(row=0, column=0, sticky="ew", padx=16, pady=(18, 18))
    brand.grid_columnconfigure(1, weight=1)
    logo = ctk.CTkFrame(brand, width=42, height=42, fg_color=_BRAND, corner_radius=8)
    logo.grid(row=0, column=0, rowspan=2, padx=(0, 12))
    logo.grid_propagate(False)
    ctk.CTkLabel(logo, text="B2", text_color="white", font=title_font(16)).place(relx=0.5, rely=0.5, anchor="center")
    ctk.CTkLabel(brand, text="B2 CARGO", text_color=_FG, anchor="w", font=title_font(15)).grid(row=0, column=1, sticky="ew")
    ctk.CTkLabel(brand, text="Vardiya Ayırma", text_color=_MUTED, anchor="w", font=font(11, "bold")).grid(row=1, column=1, sticky="ew")

    crumb_var = ctk.StringVar(value="İşlem")
    page_title_var = ctk.StringVar(value="İrsaliyeleri Ayır")
    side_status_var = ctk.StringVar(value="Hazır")
    side_total_var = ctk.StringVar(value="0 evrak")

    def set_view(name: str) -> None:
        titles = {
            "islem": ("İşlem", "İrsaliyeleri Ayır"),
            "ozet": ("Genel Bakış", "Vardiya Özeti"),
            "bolgeler": ("Dağıtım", "Bölge Dağılımı"),
            "hata": ("Denetim", "Hata Klasörü"),
        }
        crumb_var.set(titles[name][0])
        page_title_var.set(titles[name][1])
        for key, btn in nav_buttons.items():
            active = key == name
            btn.configure(
                fg_color=_BRAND if active else "transparent",
                hover_color=_BRAND_HOVER if active else _PANEL_3,
                text_color=_FG if active else _MUTED,
            )
        views[name].tkraise()

    nav = ctk.CTkFrame(sidebar, fg_color="transparent")
    nav.grid(row=1, column=0, sticky="ew", padx=14)
    for key, label in (("islem", "İşlem"), ("ozet", "Özet"), ("bolgeler", "Bölgeler"), ("hata", "Hata")):
        btn = ctk.CTkButton(
            nav,
            text=label,
            anchor="w",
            height=42,
            corner_radius=8,
            fg_color="transparent",
            hover_color=_PANEL_3,
            text_color=_MUTED,
            font=font(14, "bold"),
            command=lambda k=key: set_view(k),
        )
        btn.pack(fill="x", pady=3)
        nav_buttons[key] = btn

    status_card = card(sidebar, fg_color="#10183a")
    status_card.grid(row=2, column=0, sticky="ew", padx=14, pady=(20, 0))
    ctk.CTkLabel(status_card, text="Sistem Durumu", text_color=_MUTED, anchor="w", font=font(11, "bold")).pack(fill="x", padx=14, pady=(12, 0))
    ctk.CTkLabel(status_card, textvariable=side_status_var, text_color=_OK, anchor="w", font=title_font(18)).pack(fill="x", padx=14, pady=(2, 0))
    ctk.CTkLabel(status_card, textvariable=side_total_var, text_color=_MUTED, anchor="w", font=mono_font(12)).pack(fill="x", padx=14, pady=(0, 12))

    ctk.CTkLabel(sidebar, text="B2 · DSV · Perfetti", text_color=_MUTED, anchor="w", font=mono_font(11)).grid(
        row=4, column=0, sticky="ew", padx=16, pady=16
    )

    header = ctk.CTkFrame(content, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 10))
    header.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(header, textvariable=crumb_var, text_color=_MUTED, anchor="w", font=font(12, "bold")).grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(header, textvariable=page_title_var, text_color=_FG, anchor="w", font=title_font(26)).grid(row=1, column=0, sticky="ew")
    region_settings_btn = ctk.CTkButton(
        header,
        text="Bölge Ayarları",
        width=136,
        height=36,
        fg_color=_PANEL,
        hover_color=_PANEL_3,
        border_color=_BORDER,
        border_width=1,
        command=open_region_settings,
        font=font(12, "bold"),
    )
    region_settings_btn.grid(row=0, column=1, rowspan=2, sticky="e")

    body = ctk.CTkFrame(content, fg_color="transparent")
    body.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 14))
    body.grid_rowconfigure(0, weight=1)
    body.grid_columnconfigure(0, weight=1)
    for name in ("islem", "ozet", "bolgeler", "hata"):
        frame = ctk.CTkFrame(body, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        views[name] = frame

    try:
        rm = RegionMap.from_yaml(str(config_path()))
        conflicts = ", ".join(sorted(rm.conflicts)) if rm.conflicts else ""
    except Exception as exc:
        conflicts = ""
        messagebox.showerror("Bölge haritası okunamadı", f"config/regions.yaml açılamadı:\n{exc}")

    process = views["islem"]
    process.grid_columnconfigure(0, weight=3)
    process.grid_columnconfigure(1, weight=2)
    process.grid_rowconfigure(0, weight=1)

    run_card = card(process)
    run_card.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
    run_card.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(run_card, text="İrsaliye klasörü", text_color=_MUTED, anchor="w", font=font(12, "bold")).grid(row=0, column=0, sticky="ew", padx=22, pady=(24, 6))
    folder_var = ctk.StringVar(value=str(default_input_dir()))
    folder_row = ctk.CTkFrame(run_card, fg_color="transparent")
    folder_row.grid(row=1, column=0, sticky="ew", padx=22)
    folder_row.grid_columnconfigure(0, weight=1)
    folder_entry = entry(folder_row, textvariable=folder_var, height=42)
    folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

    def pick_folder() -> None:
        start_dir = folder_var.get() if Path(folder_var.get()).is_dir() else str(base_dir())
        chosen = filedialog.askdirectory(initialdir=start_dir, title="İrsaliye klasörünü seç")
        if chosen:
            folder_var.set(chosen)

    ctk.CTkButton(folder_row, text="Klasör Seç", width=126, height=42, fg_color=_BRAND, hover_color=_BRAND_HOVER, command=pick_folder, font=font(12, "bold")).grid(row=0, column=1)
    ctk.CTkLabel(run_card, text="Vardiya adı", text_color=_MUTED, anchor="w", font=font(12, "bold")).grid(row=2, column=0, sticky="ew", padx=22, pady=(18, 6))
    name_var = ctk.StringVar(value="")
    entry(run_card, textvariable=name_var, placeholder_text="Boş bırakılırsa otomatik tarih kullanılır", height=42).grid(row=3, column=0, sticky="ew", padx=22)

    if conflicts:
        ctk.CTkLabel(
            run_card,
            text=f"Birden çok bölgeye düşen şehir(ler): {conflicts}. Bu belgeler Hata'ya gönderilir.",
            text_color=_WARN,
            anchor="w",
            justify="left",
            wraplength=650,
            font=font(12),
        ).grid(row=4, column=0, sticky="ew", padx=22, pady=(16, 0))

    info = ctk.CTkFrame(run_card, fg_color="#111a3a", border_color=_BORDER, border_width=1, corner_radius=8)
    info.grid(row=5, column=0, sticky="ew", padx=22, pady=(22, 18))
    ctk.CTkLabel(info, text="Ayırma kuralı", text_color=_MUTED, anchor="w", font=font(11, "bold")).pack(fill="x", padx=18, pady=(16, 4))
    ctk.CTkLabel(
        info,
        text="DSV listesi DSV klasörüne, diğer irsaliyeler B2 içindeki bölge ve Palet/Dökme klasörlerine ayrılır.",
        text_color=_FG,
        anchor="w",
        justify="left",
        wraplength=650,
        font=font(13),
    ).pack(fill="x", padx=18, pady=(0, 16))

    ayir_btn = ctk.CTkButton(run_card, text="AYIR", height=56, corner_radius=10, fg_color=_ORANGE, hover_color=_ORANGE_HOVER, font=title_font(18))
    ayir_btn.grid(row=6, column=0, sticky="ew", padx=22, pady=(0, 16))
    status_var = ctk.StringVar(value="Hazır.")
    live_var = ctk.StringVar(value="")
    ctk.CTkLabel(run_card, textvariable=status_var, text_color=_MUTED, anchor="w", font=font(12)).grid(row=7, column=0, sticky="ew", padx=22)
    ctk.CTkLabel(run_card, textvariable=live_var, text_color=_MUTED, anchor="w", font=mono_font(12)).grid(row=8, column=0, sticky="ew", padx=22, pady=(2, 8))
    progress = ctk.CTkProgressBar(run_card, mode="determinate", height=8, progress_color=_ORANGE, fg_color=_PANEL_2)
    progress.set(0)
    progress.grid(row=9, column=0, sticky="ew", padx=22, pady=(0, 22))
    progress.grid_remove()

    process_side = ctk.CTkFrame(process, fg_color="transparent")
    process_side.grid(row=0, column=1, sticky="nsew")
    process_side.grid_columnconfigure(0, weight=1)
    metric(process_side, "B2", "Bölge bazlı ayırma", _BRAND).grid(row=0, column=0, sticky="ew", pady=(0, 12))
    metric(process_side, "DSV", "Lokasyon listesi eşleşmesi", _OK).grid(row=1, column=0, sticky="ew", pady=(0, 12))
    metric(process_side, "HATA", "Tekrar tarama akışı", _WARN).grid(row=2, column=0, sticky="ew")

    summary = views["ozet"]
    summary.grid_columnconfigure((0, 1, 2, 3), weight=1)
    summary_title = ctk.StringVar(value="Henüz işlem yapılmadı")
    summary_sub = ctk.StringVar(value="Bir vardiya ayırdıktan sonra özet burada görünecek.")
    banner = card(summary, fg_color="#10183a")
    banner.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 14))
    ctk.CTkLabel(banner, textvariable=summary_title, text_color=_FG, anchor="w", font=title_font(20)).pack(fill="x", padx=22, pady=(20, 4))
    ctk.CTkLabel(banner, textvariable=summary_sub, text_color=_MUTED, anchor="w", font=font(13)).pack(fill="x", padx=22, pady=(0, 20))
    summary_stats = ctk.CTkFrame(summary, fg_color="transparent")
    summary_stats.grid(row=1, column=0, columnspan=4, sticky="new")
    summary_stats.grid_columnconfigure((0, 1, 2, 3), weight=1)

    regions_box = ctk.CTkScrollableFrame(
        views["bolgeler"],
        fg_color=_PANEL,
        border_color=_BORDER,
        border_width=1,
        corner_radius=8,
        label_text="Bölge dağılımı",
        label_text_color=_FG,
    )
    regions_box.grid(row=0, column=0, sticky="nsew")
    ctk.CTkLabel(regions_box, text="İşlem tamamlanınca bölge listesi burada oluşur.", text_color=_MUTED, font=font(13)).pack(anchor="w", padx=12, pady=12)

    error_text = ctk.StringVar(value="Hata klasörü temiz.")
    error_panel = card(views["hata"], fg_color="#1c1730", border_color="#4d3b55")
    error_panel.grid(row=0, column=0, sticky="ew")
    ctk.CTkLabel(error_panel, text="Denetim", text_color=_WARN, anchor="w", font=font(12, "bold")).pack(fill="x", padx=20, pady=(18, 4))
    ctk.CTkLabel(error_panel, textvariable=error_text, text_color=_FG, anchor="w", justify="left", wraplength=760, font=title_font(18)).pack(fill="x", padx=20, pady=(0, 18))

    action_bar = ctk.CTkFrame(content, fg_color="transparent")
    action_bar.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 18))
    action_bar.grid_columnconfigure((0, 1, 2, 3), weight=1)
    open_out_btn = ctk.CTkButton(action_bar, text="Çıktı Klasörünü Aç", state="disabled", height=40, fg_color=_BRAND, hover_color=_BRAND_HOVER, font=font(12, "bold"))
    open_out_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))
    open_report_btn = ctk.CTkButton(action_bar, text="Vardiya Raporu", state="disabled", height=40, fg_color=_PANEL, hover_color=_PANEL_3, border_color=_BORDER, border_width=1, font=font(12, "bold"))
    open_report_btn.grid(row=0, column=1, sticky="ew", padx=6)
    open_err_btn = ctk.CTkButton(action_bar, text="Hata Raporu", state="disabled", height=40, fg_color=_BAD, hover_color="#c85252", font=font(12, "bold"))
    open_err_btn.grid(row=0, column=2, sticky="ew", padx=6)
    rescan_btn = ctk.CTkButton(action_bar, text="Hata Klasörünü Tekrar Tara", state="disabled", height=40, fg_color="transparent", hover_color=_PANEL_3, border_color=_BORDER, border_width=1, text_color=_FG, font=font(12, "bold"))
    rescan_btn.grid(row=0, column=3, sticky="ew", padx=(6, 0))

    def render_results(result: PipelineResult) -> None:
        for widget in summary_stats.winfo_children():
            widget.destroy()
        for widget in regions_box.winfo_children():
            widget.destroy()

        b2_total = sum(result.region_counts.values())
        total = b2_total + result.dsv_count + result.error_count
        region_total = len(result.region_counts)
        summary_title.set("Ayırma tamamlandı")
        summary_sub.set(f"{total} evrak · {region_total} bölge · {result.error_count} hata · {result.out_dir}")
        side_status_var.set("Tamamlandı")
        side_total_var.set(f"{total} evrak")

        metric(summary_stats, str(b2_total), "B2 evrak", _BRAND).grid(row=0, column=0, sticky="ew", padx=(0, 10))
        metric(summary_stats, str(result.dsv_count), "DSV evrak", _OK).grid(row=0, column=1, sticky="ew", padx=10)
        metric(summary_stats, str(region_total), "Bölge", _GOLD).grid(row=0, column=2, sticky="ew", padx=10)
        metric(summary_stats, str(result.error_count), "Hata", _BAD if result.error_count else _MUTED).grid(row=0, column=3, sticky="ew", padx=(10, 0))

        for region in sorted(result.region_counts):
            row = card(regions_box, fg_color=_PANEL_2)
            row.pack(fill="x", padx=8, pady=5)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=region, text_color=_FG, anchor="w", font=font(14, "bold")).grid(row=0, column=0, sticky="ew", padx=16, pady=12)
            ctk.CTkLabel(row, text=f"{result.region_counts[region]} evrak", text_color=_MUTED, anchor="e", font=mono_font(13, "bold")).grid(row=0, column=1, padx=16, pady=12)

        error_text.set(
            f"{result.error_count} evrak Hata klasöründe. Düzeltip tekrar tarayabilirsiniz."
            if result.error_count
            else "Hata klasörü temiz. Bu vardiya sorunsuz ayrıldı."
        )

    def on_done(result: PipelineResult | None, error: Exception | None) -> None:
        progress.stop()
        progress.grid_remove()
        ayir_btn.configure(state="normal")
        region_settings_btn.configure(state="normal")
        if error is not None:
            side_status_var.set("Hata")
            status_var.set("Hata oluştu.")
            messagebox.showerror("Hata", f"İşlem sırasında hata oluştu:\n{error}")
            return
        assert result is not None
        last_result["r"] = result
        total = sum(result.region_counts.values()) + result.dsv_count + result.error_count
        status_var.set(f"Tamamlandı - {total} evrak işlendi. Çıktı: {result.out_dir}")
        live_var.set(f"Okunan: {total}/{total} | B2: {sum(result.region_counts.values())}  DSV: {result.dsv_count}  Hata: {result.error_count}")
        render_results(result)
        open_out_btn.configure(state="normal")
        open_report_btn.configure(state="normal")
        has_err = bool(result.error_count)
        open_err_btn.configure(state="normal" if has_err else "disabled")
        rescan_btn.configure(state="normal" if has_err else "disabled")
        set_view("ozet")

    def update_progress(done: int, total: int, filename: str) -> None:
        ratio = done / total if total else 0
        progress.set(ratio)
        side_status_var.set("Çalışıyor")
        side_total_var.set(f"{done}/{total} evrak")
        status_var.set(f"PDF okunuyor: {done}/{total}")
        live_var.set(f"Okunan: {done}/{total} | Son dosya: {filename}")

    def worker(input_dir: str, shift_name: str | None) -> None:
        def progress_cb(done: int, total: int, filename: str) -> None:
            root.after(0, lambda: update_progress(done, total, filename))

        try:
            result = run_split(input_dir, shift_name, progress_callback=progress_cb)
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
        for button in (ayir_btn, region_settings_btn, open_out_btn, open_report_btn, open_err_btn, rescan_btn):
            button.configure(state="disabled")
        set_view("islem")
        side_status_var.set("Çalışıyor")
        side_total_var.set(f"0/{len(pdfs)} evrak")
        status_var.set(f"{len(pdfs)} PDF işleniyor, lütfen bekleyin...")
        live_var.set(f"Okunan: 0/{len(pdfs)}")
        progress.set(0)
        progress.grid()
        threading.Thread(target=worker, args=(input_dir, name_var.get().strip() or None), daemon=True).start()

    def open_output() -> None:
        if last_result["r"]:
            open_in_explorer(last_result["r"].out_dir)

    def open_shift_report() -> None:
        if last_result["r"]:
            open_in_explorer(Path(last_result["r"].out_dir) / "vardiya_raporu.csv")

    def open_error_report() -> None:
        r = last_result["r"]
        if r and r.error_count:
            open_in_explorer(Path(r.out_dir) / "Hata" / "Hata_raporu.csv")

    def rescan_errors() -> None:
        r = last_result["r"]
        if not r or not r.error_count:
            return
        hata_dir = Path(r.out_dir) / "Hata"
        if not hata_dir.is_dir():
            messagebox.showwarning("Hata klasörü yok", f"Bulunamadı:\n{hata_dir}")
            return
        folder_var.set(str(hata_dir))
        name_var.set(f"Hata_tekrar_{datetime.now().strftime('%H%M%S')}")
        start()

    ayir_btn.configure(command=start)
    open_out_btn.configure(command=open_output)
    open_report_btn.configure(command=open_shift_report)
    open_err_btn.configure(command=open_error_report)
    rescan_btn.configure(command=rescan_errors)
    set_view("islem")

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
