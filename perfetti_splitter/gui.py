"""Masaustu arayuz (CustomTkinter - B2 Cargo tasarim sistemi).

Cekirdek mantigi degistirmez; `pipeline.run` uzerine ince bir gorsel
sarmalayicidir. Tk'dan bagimsiz yardimcilar ayri tutulur ki ekran
gerektirmeden test edilebilsin.

Gorsel katman "Perfetti Vardiya Ayirma - 1A.dc.html" tasarim referansina
(renkler, tipografi, kart/ekran duzeni, acik/koyu tema) gore kurulmustur.
"""

from __future__ import annotations

import json
import math
import os
import sys
import threading
from dataclasses import dataclass, field as dc_field
from decimal import Decimal
from datetime import datetime
from pathlib import Path

from . import report
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


def dated_shift_name(shift_name: str | None) -> str:
    """Vardiya adinin sonuna 'GG.AA.YYYY' bugunun tarihini ekler.

    Ad girilmemisse "Vardiya" koku kullanilir; boylece Birlesik_PDF altindaki
    her klasor, adi ne olursa olsun, olusturuldugu gunu tasir.
    """
    base = (shift_name or "").strip() or "Vardiya"
    return f"{base} {datetime.now():%d.%m.%Y}"


def run_split(
    input_dir: str | Path,
    shift_name: str | None = None,
    progress_callback=None,
) -> PipelineResult:
    region_map = RegionMap.from_yaml(str(config_path()))
    dsv = DsvMatcher.from_yaml(str(dsv_path())) if dsv_path().exists() else None
    input_dir = Path(input_dir)
    pdf_paths = [p for p in input_dir.iterdir() if p.suffix.lower() == ".pdf"]
    result = run(
        input_dir,
        default_output_dir(),
        region_map,
        shift_name=dated_shift_name(shift_name),
        dsv_matcher=dsv,
        progress_callback=progress_callback,
    )
    # Basariyla islenen PDF'ler cikti klasorlerine kopyalandi (Hata dahil);
    # Gelen_PDF'i bosaltarak kullaniciyi bir sonraki vardiyadan once elle
    # silme isinden kurtarir.
    for path in pdf_paths:
        try:
            path.unlink()
        except OSError:
            pass
    return result


def open_in_explorer(path: str | Path) -> None:
    path = str(path)
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


# --- varlik (font/logo) yollari ve tema tercihi -----------------------------


def assets_dir() -> Path:
    external = base_dir() / "assets"
    if external.exists():
        return external
    return resource_dir() / "assets"


def fonts_dir() -> Path:
    return assets_dir() / "fonts"


def logo_mark_path() -> Path:
    """Yuvarlak 'COOL PARTNER' amblemi (baslik/kenar cubugu/Islem ekrani)."""
    return assets_dir() / "logo-mark.png"


def logo_wordmark_path() -> Path:
    """Yatay 'B2 Cargo Lojistik' kelime-logosu (kenar cubugu, beyaz kutu)."""
    return assets_dir() / "logo-wordmark.png"


def ui_settings_path() -> Path:
    return base_dir() / "ui_ayar.json"


def load_theme() -> str:
    try:
        data = json.loads(ui_settings_path().read_text(encoding="utf-8"))
        if data.get("theme") in ("dark", "light"):
            return data["theme"]
    except Exception:
        pass
    return "dark"


def save_theme(theme: str) -> None:
    try:
        ui_settings_path().write_text(json.dumps({"theme": theme}), encoding="utf-8")
    except Exception:
        pass


_FONT_FILES = (
    "Manrope-Regular.ttf",
    "Manrope-Bold.ttf",
    "Manrope-ExtraBold.ttf",
    "JetBrainsMono-Regular.ttf",
    "JetBrainsMono-Bold.ttf",
)

F_UI = "Manrope"
F_UI_HEAVY = "Manrope ExtraBold"
F_MONO = "JetBrains Mono"


def register_fonts() -> None:
    """Manrope / JetBrains Mono'yu surece ozel (private) olarak yukler.

    Dosyalar bulunamazsa veya platform Windows degilse sessizce gecilir;
    Tk o zaman en yakin sistem fontuna duser (gorunum tasarima yakin kalir).
    """
    folder = fonts_dir()
    if not folder.exists() or not sys.platform.startswith("win"):
        return
    import ctypes

    FR_PRIVATE = 0x10
    for name in _FONT_FILES:
        path = folder / name
        if path.exists():
            try:
                ctypes.windll.gdi32.AddFontResourceExW(str(path), FR_PRIVATE, 0)
            except Exception:
                pass


# --- renk tokenlari ----------------------------------------------------------
# Kaynak: "Perfetti Vardiya Ayirma - 1A.dc.html" (themeVars()).

THEMES: dict[str, dict[str, str]] = {
    "dark": dict(
        bg="#0B1230", panel="#141B3D", panel2="#0F1636", border="#28315E",
        fg="#EBF0FF", muted="#94A0C6",
        brand="#33489E", brand_hover="#4057BB",
        brand2="#F26A21", brand2_hover="#D95B1A",
        gold="#FBA61C", good="#37C98B", warn="#F0B23E", bad="#F26D6D",
        chip="#1B2450",
    ),
    "light": dict(
        bg="#EDF0F8", panel="#FFFFFF", panel2="#F5F7FC", border="#DEE3F0",
        fg="#17255A", muted="#6E7591",
        brand="#1B2A63", brand_hover="#2A3B82",
        brand2="#F26A21", brand2_hover="#D95B1A",
        gold="#F59A1E", good="#129B62", warn="#C9871A", bad="#D64545",
        chip="#EAEEF9",
    ),
}


# --- Tk'dan bagimsiz veri donusumleri (gercek pipeline sonucundan) ----------
# Ayirma KARARLARINA dokunmaz; yalnizca `PipelineResult.targets` (pipeline'in
# zaten urettigi ayni esleme) uzerinden goruntuleme icin gruplar.


def region_stats(result: PipelineResult, region_map: RegionMap | None = None) -> list[dict]:
    """Her B2 bolgesi icin evrak/koli/kg/palet/dokme/en-buyuk-alici."""
    per_region: dict[str, dict] = {}
    for doc in result.documents:
        status, target, bucket = result.targets.get(id(doc), ("", "", ""))
        if status != "B2":
            continue
        stat = per_region.setdefault(
            target,
            {
                "ad": target, "evrak": 0, "koli": 0, "kg": Decimal("0"),
                "palet": 0, "dokme": 0, "top": "", "_top_koli": -1,
            },
        )
        stat["evrak"] += 1
        stat["koli"] += doc.koli or 0
        stat["kg"] += doc.brut_agirlik or Decimal("0")
        if bucket == "Palet":
            stat["palet"] += 1
        elif bucket == "Dökme":
            stat["dokme"] += 1
        koli = doc.koli or 0
        if koli > stat["_top_koli"]:
            stat["_top_koli"] = koli
            stat["top"] = doc.recipient or Path(doc.path).name

    out = []
    for stat in per_region.values():
        bucket_total = stat["palet"] + stat["dokme"]
        stat["pal_pct"] = round(stat["palet"] / bucket_total * 100) if bucket_total else 0
        cities = region_map.mapping.get(stat["ad"], []) if region_map else []
        stat["il"] = " · ".join(cities[:4]) + (" …" if len(cities) > 4 else "")
        del stat["_top_koli"]
        out.append(stat)
    out.sort(key=lambda s: s["ad"])
    return out


def error_rows(result: PipelineResult) -> list[dict]:
    """Hata klasorune giden belgeler icin Alici/Neden/Oneri satirlari."""
    rows = []
    for doc in result.documents:
        status, _target, _bucket = result.targets.get(id(doc), ("", "", ""))
        if status != "Hata":
            continue
        neden, oneri = report.error_hint(doc.errors, doc.address)
        rows.append(
            {
                "alici": doc.recipient or Path(doc.path).name,
                "dosya": Path(doc.path).name,
                "neden": neden or "Bilinmeyen hata",
                "oneri": oneri or ("; ".join(doc.errors) or "Belgeyi kontrol edip tekrar tarayın."),
            }
        )
    return rows


def _fmt_int(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _fmt_kg(value: Decimal) -> str:
    q = value.quantize(Decimal("1")) if value == value.to_integral() else value.quantize(Decimal("0.1"))
    s = f"{q:,}"
    if "." in s:
        whole, frac = s.split(".")
        return f"{whole.replace(',', '.')},{frac}"
    return s.replace(",", ".")


@dataclass
class Overview:
    kpis: list[dict]
    palet: int
    dokme: int
    b2_total: int
    dsv_count: int
    top_regions: list[dict] = dc_field(default_factory=list)


def build_overview(result: PipelineResult, regions: list[dict]) -> Overview:
    b2_total = sum(r["evrak"] for r in regions)
    total = b2_total + result.dsv_count + result.error_count
    toplam_koli = sum(r["koli"] for r in regions)
    toplam_kg = sum((r["kg"] for r in regions), Decimal("0"))
    palet = sum(r["palet"] for r in regions)
    dokme = sum(r["dokme"] for r in regions)
    kpis = [
        {"label": "TOPLAM EVRAK", "value": str(total), "sub": "irsaliye"},
        {"label": "BÖLGE", "value": str(len(regions)), "sub": "B2 dağıtım"},
        {"label": "TOPLAM KOLİ", "value": _fmt_int(toplam_koli), "sub": "palet+dökme"},
        {"label": "AĞIRLIK", "value": _fmt_kg(toplam_kg), "sub": "kg"},
        {"label": "PALET / DÖKME", "value": f"{palet} / {dokme}", "sub": "kova"},
        {"label": "HATA", "value": str(result.error_count), "sub": "temiz" if not result.error_count else "kontrol et"},
    ]
    top_regions = sorted(regions, key=lambda r: r["koli"], reverse=True)[:4]
    return Overview(
        kpis=kpis, palet=palet, dokme=dokme, b2_total=b2_total,
        dsv_count=result.dsv_count, top_regions=top_regions,
    )


# --- Tk aray n uz -----------------------------------------------------------


def main() -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox

    import customtkinter as ctk
    from PIL import Image, ImageDraw, ImageFont

    register_fonts()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("B2CARGO PDF AYIRMA")
    root.geometry("1240x780")
    root.minsize(1080, 680)
    try:
        if icon_path().exists():
            root.iconbitmap(str(icon_path()))
    except Exception:
        pass

    # ------------------------------------------------------------------ #
    # durum
    # ------------------------------------------------------------------ #
    state: dict = {
        "theme": load_theme(),
        "tab": "islem",
        "phase": "idle",
        "result": None,
        "spinner": None,
    }
    folder_var = ctk.StringVar(value=str(default_input_dir()))
    name_var = ctk.StringVar(value="")
    progress_pct = {"v": 0, "drawn": -1}
    nav_buttons: dict[str, ctk.CTkButton] = {}
    view_frames: dict[str, ctk.CTkFrame] = {}

    def C() -> dict[str, str]:
        return THEMES[state["theme"]]

    def hex_to_rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    # ------------------------------------------------------------------ #
    # ikon uretimi (PIL ile vektor benzeri cizim, tema rengine gore)
    # ------------------------------------------------------------------ #
    def _icon(draw_fn, color: str, size: int = 18, stroke: float = 2.2):
        scale = 4
        s = size * scale
        w = max(1, round(stroke * scale))
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        draw_fn(d, s, w, color)
        img = img.resize((size, size), Image.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    def icon_islem(color, size=18):
        return _icon(lambda d, s, w, c: d.polygon(
            [(s * 0.22, s * 0.10), (s * 0.92, s * 0.5), (s * 0.22, s * 0.9)], outline=c, width=w
        ), color, size)

    def icon_ozet(color, size=18):
        def draw(d, s, w, c):
            pad, gap = s * 0.10, s * 0.14
            cell = (s - 2 * pad - gap) / 2
            for rx, ry in ((pad, pad), (pad + cell + gap, pad), (pad, pad + cell + gap), (pad + cell + gap, pad + cell + gap)):
                d.rounded_rectangle([rx, ry, rx + cell, ry + cell], radius=cell * 0.2, outline=c, width=w)
        return _icon(draw, color, size)

    def icon_bolgeler(color, size=18):
        def draw(d, s, w, c):
            d.ellipse([s * 0.14, s * 0.06, s * 0.86, s * 0.62], outline=c, width=w)
            d.polygon([(s * 0.30, s * 0.44), (s * 0.70, s * 0.44), (s * 0.5, s * 0.94)], outline=c, width=w)
            r = s * 0.12
            d.ellipse([s * 0.5 - r, s * 0.34 - r, s * 0.5 + r, s * 0.34 + r], outline=c, width=w)
        return _icon(draw, color, size)

    def icon_hata(color, size=18):
        def draw(d, s, w, c):
            d.polygon([(s * 0.5, s * 0.06), (s * 0.94, s * 0.90), (s * 0.06, s * 0.90)], outline=c, width=w)
            d.line([(s * 0.5, s * 0.38), (s * 0.5, s * 0.64)], fill=c, width=w)
            r = w * 0.85
            d.ellipse([s * 0.5 - r, s * 0.75 - r, s * 0.5 + r, s * 0.75 + r], fill=c)
        return _icon(draw, color, size)

    def icon_check(color, size=32, stroke=3.0):
        return _icon(lambda d, s, w, c: d.line(
            [(s * 0.16, s * 0.52), (s * 0.42, s * 0.78), (s * 0.88, s * 0.22)], fill=c, width=w, joint="curve"
        ), color, size, stroke)

    def icon_folder(color, size=16):
        def draw(d, s, w, c):
            d.rounded_rectangle([s * 0.08, s * 0.30, s * 0.92, s * 0.86], radius=s * 0.08, outline=c, width=w)
            d.line([(s * 0.08, s * 0.34), (s * 0.30, s * 0.34), (s * 0.40, s * 0.18), (s * 0.62, s * 0.18), (s * 0.68, s * 0.30)], fill=c, width=w, joint="curve")
        return _icon(draw, color, size)

    def icon_list(color, size=16):
        def draw(d, s, w, c):
            for y in (0.24, 0.5, 0.76):
                d.line([(s * 0.12, s * y), (s * 0.88, s * y)], fill=c, width=w)
        return _icon(draw, color, size)

    def icon_gear(color, size=16):
        def draw(d, s, w, c):
            cx = cy = s / 2
            r = s * 0.20
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=w)
            for ang in range(0, 360, 45):
                rad = math.radians(ang)
                x1, y1 = cx + (r + w * 0.5) * math.cos(rad), cy + (r + w * 0.5) * math.sin(rad)
                x2, y2 = cx + (r + w * 1.8) * math.cos(rad), cy + (r + w * 1.8) * math.sin(rad)
                d.line([x1, y1, x2, y2], fill=c, width=w)
        return _icon(draw, color, size)

    def icon_refresh(color, size=15):
        def draw(d, s, w, c):
            d.arc([s * 0.12, s * 0.12, s * 0.88, s * 0.88], 25, 300, fill=c, width=w)
            d.polygon([(s * 0.90, s * 0.10), (s * 0.68, s * 0.14), (s * 0.86, s * 0.34)], fill=c)
        return _icon(draw, color, size)

    def icon_chevron(color, size=15):
        return _icon(lambda d, s, w, c: d.line(
            [(s * 0.2, s * 0.35), (s * 0.5, s * 0.68), (s * 0.8, s * 0.35)], fill=c, width=w, joint="curve"
        ), color, size)

    def icon_sun(color, size=15):
        def draw(d, s, w, c):
            r = s * 0.18
            cx = cy = s / 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=w)
            for ang in range(0, 360, 45):
                rad = math.radians(ang)
                x1, y1 = cx + (r + s * 0.08) * math.cos(rad), cy + (r + s * 0.08) * math.sin(rad)
                x2, y2 = cx + (r + s * 0.20) * math.cos(rad), cy + (r + s * 0.20) * math.sin(rad)
                d.line([x1, y1, x2, y2], fill=c, width=w)
        return _icon(draw, color, size)

    def icon_moon(color, size=15):
        def draw(d, s, w, c):
            r = s * 0.34
            d.ellipse([s * 0.5 - r, s * 0.5 - r, s * 0.5 + r, s * 0.5 + r], fill=c)
            r2 = s * 0.30
            ox = s * 0.5 + s * 0.20
            d.ellipse([ox - r2, s * 0.42 - r2, ox + r2, s * 0.42 + r2], fill=(0, 0, 0, 0))
        return _icon(draw, color, size)

    def icon_warn_circle(color, size=18):
        def draw(d, s, w, c):
            d.ellipse([s * 0.06, s * 0.06, s * 0.94, s * 0.94], outline=c, width=w)
            d.line([(s * 0.5, s * 0.32), (s * 0.5, s * 0.58)], fill=c, width=w)
            r = w * 0.85
            d.ellipse([s * 0.5 - r, s * 0.72 - r, s * 0.5 + r, s * 0.72 + r], fill=c)
        return _icon(draw, color, size)

    # ------------------------------------------------------------------ #
    # gradyan / iki-tonlu cubuklar (PIL ile), AYIR butonu ve ilerleme
    # ------------------------------------------------------------------ #
    def _lerp(a, b, t):
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    def gradient_image(width, height, color_a, color_b, radius):
        width, height = max(1, int(width)), max(1, int(height))
        rgb_a, rgb_b = hex_to_rgb(color_a), hex_to_rgb(color_b)
        row = Image.new("RGB", (width, 1))
        for x in range(width):
            row.putpixel((x, 0), _lerp(rgb_a, rgb_b, x / max(1, width - 1)))
        grad = row.resize((width, height)).convert("RGBA")
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
        grad.putalpha(mask)
        return grad

    def two_tone_image(width, height, pct_a, color_a, color_b, radius):
        width, height = max(1, int(width)), max(1, int(height))
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        split = max(0, min(width, round(width * pct_a / 100)))
        if split > 0:
            img.paste(Image.new("RGBA", (split, height), hex_to_rgb(color_a) + (255,)), (0, 0))
        if split < width:
            img.paste(Image.new("RGBA", (width - split, height), hex_to_rgb(color_b) + (255,)), (split, 0))
        mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=255)
        img.putalpha(mask)
        return img

    def pill_image(text, width, height, bg_a, bg_b, text_color, font_path, font_size, icon_draw=None):
        img = gradient_image(width, height, bg_a, bg_b, height // 2)
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(str(font_path), font_size)
        except Exception:
            font = ImageFont.load_default()
        bbox = d.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        icon_w = 0
        if icon_draw:
            icon_w = int(font_size * 1.15) + 12
        total_w = tw + icon_w
        start_x = (width - total_w) / 2
        ty = (height - th) / 2 - bbox[1]
        if icon_draw:
            isz = int(font_size * 1.15)
            icon_draw(d, start_x, (height - isz) / 2, isz, text_color)
            start_x += icon_w
        d.text((start_x, ty), text, font=font, fill=text_color)
        return img

    def progress_image(width, height, pct, colors):
        width, height = max(1, int(width)), max(1, int(height))
        base = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        bg_mask = Image.new("L", (width, height), 0)
        ImageDraw.Draw(bg_mask).rounded_rectangle([0, 0, width - 1, height - 1], radius=height // 2, fill=255)
        bg = Image.new("RGBA", (width, height), hex_to_rgb(colors["panel2"]) + (255,))
        bg.putalpha(bg_mask)
        base.alpha_composite(bg)
        fill_w = max(0, min(width, round(width * pct / 100)))
        if fill_w > 2:
            fill = gradient_image(fill_w, height, colors["brand2"], colors["gold"], height // 2)
            base.alpha_composite(fill, (0, 0))
        ImageDraw.Draw(base).rounded_rectangle(
            [0, 0, width - 1, height - 1], radius=height // 2, outline=hex_to_rgb(colors["border"]) + (255,), width=1
        )
        return base

    # ------------------------------------------------------------------ #
    # dondurulen halka (calisiyor durumu spinner)
    # ------------------------------------------------------------------ #
    class Spinner:
        def __init__(self, parent, colors, size=54, width=4):
            self.canvas = tk.Canvas(parent, width=size, height=size, bg=colors["panel"], highlightthickness=0)
            self.size, self.width, self.angle = size, width, 0
            self.colors = colors
            self._job = None
            self._redraw()

        def _redraw(self):
            c = self.canvas
            c.delete("all")
            pad = self.width
            c.create_oval(pad, pad, self.size - pad, self.size - pad, outline=self.colors["border"], width=self.width)
            c.create_arc(
                pad, pad, self.size - pad, self.size - pad,
                start=self.angle, extent=95, outline=self.colors["brand2"], width=self.width, style="arc",
            )

        def start(self):
            self.stop()

            def tick():
                self.angle = (self.angle - 11) % 360
                self._redraw()
                self._job = self.canvas.after(45, tick)

            tick()

        def stop(self):
            if self._job:
                try:
                    self.canvas.after_cancel(self._job)
                except Exception:
                    pass
                self._job = None

    # ------------------------------------------------------------------ #
    # kucuk yardimcilar (fontlar, kartlar)
    # ------------------------------------------------------------------ #
    def font(size, weight="normal"):
        return ctk.CTkFont(family=F_UI, size=size, weight=weight)

    def title_font(size):
        return ctk.CTkFont(family=F_UI_HEAVY, size=size, weight="normal")

    def mono_font(size, weight="normal"):
        return ctk.CTkFont(family=F_MONO, size=size, weight=weight)

    def card(parent, fg_color=None, border_color=None, radius=12):
        c = C()
        return ctk.CTkFrame(
            parent,
            fg_color=fg_color or c["panel"],
            border_color=border_color or c["border"],
            border_width=1,
            corner_radius=radius,
        )

    def section_label(parent, text):
        return ctk.CTkLabel(parent, text=text.upper(), text_color=C()["muted"], anchor="w", font=font(11, "bold"))

    def secondary_button(parent, text, image=None, command=None, height=36, state="normal"):
        c = C()
        return ctk.CTkButton(
            parent, text=text, image=image, compound="left", height=height,
            fg_color=c["panel"], hover_color=c["panel2"], border_color=c["border"], border_width=1,
            text_color=c["fg"], font=font(12, "bold"), corner_radius=10, command=command, state=state,
        )

    def primary_button(parent, text, image=None, command=None, height=36, state="normal"):
        c = C()
        return ctk.CTkButton(
            parent, text=text, image=image, compound="left", height=height,
            fg_color=c["brand"], hover_color=c["brand_hover"], text_color="white",
            font=font(12, "bold"), corner_radius=10, command=command, state=state,
        )

    def entry(parent, **kwargs):
        c = C()
        opts = dict(
            fg_color=c["panel2"], border_color=c["border"], text_color=c["fg"],
            placeholder_text_color=c["muted"], font=font(12),
        )
        opts.update(kwargs)
        return ctk.CTkEntry(parent, **opts)

    def kpi_card(parent, item):
        c = card(parent, radius=14)
        c.grid_columnconfigure(0, weight=1)
        section_label(c, item["label"]).grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))
        ctk.CTkLabel(row, text=item["value"], text_color=C()["fg"], font=mono_font(24, "bold")).pack(side="left")
        ctk.CTkLabel(row, text="  " + item["sub"], text_color=C()["muted"], font=font(11, "bold")).pack(side="left")
        return c

    # ------------------------------------------------------------------ #
    # bolge haritasi (Bolgeler kartlarindaki il alt basligi icin)
    # ------------------------------------------------------------------ #
    try:
        region_map = RegionMap.from_yaml(str(config_path()))
        conflicts = ", ".join(sorted(region_map.conflicts)) if region_map.conflicts else ""
    except Exception as exc:
        region_map = None
        conflicts = ""
        messagebox.showerror("Bölge haritası okunamadı", f"config/regions.yaml açılamadı:\n{exc}")

    # ------------------------------------------------------------------ #
    # gorunum kurulumu (tema degisince tamamen yeniden cizilir)
    # ------------------------------------------------------------------ #
    TITLES = {
        "islem": ("İşlem", "İrsaliyeleri Ayır"),
        "ozet": ("Genel Bakış", "Vardiya Özeti"),
        "bolgeler": ("Dağıtım", "Bölge Dağılımı"),
        "hata": ("Denetim", "Hata Klasörü"),
    }

    def set_view(name: str) -> None:
        # Onceki vardiya bittikten sonra Islem sekmesine donmek, yeni bir
        # ayirma icin hazir (bosta) ekrani gostermeli; eski "tamamlandi"
        # karti sonsuza kadar kalmamali.
        if name == "islem" and state["phase"] == "done":
            state["phase"] = "idle"
            render_islem_state()
        state["tab"] = name
        c = C()
        crumb_var.set(TITLES[name][0])
        page_title_var.set(TITLES[name][1])
        for key, btn in nav_buttons.items():
            active = key == name
            btn.configure(
                fg_color=c["chip"] if active else "transparent",
                text_color=c["fg"] if active else c["muted"],
                image=nav_icons[key]["active" if active else "inactive"],
            )
        if state["tab"] in view_frames:
            view_frames[name].tkraise()
        accent = nav_accent_holder.get("w")
        if accent is not None:
            accent.place(in_=nav_buttons[name], x=0, rely=0, relheight=1)

    def build() -> None:
        if state["spinner"] is not None:
            state["spinner"].stop()
            state["spinner"] = None
        for w in root.winfo_children():
            w.destroy()
        nav_buttons.clear()
        view_frames.clear()

        c = C()
        root.configure(fg_color=c["bg"])
        is_dark = state["theme"] == "dark"

        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        # ---------------- kenar cubugu ----------------
        sidebar = ctk.CTkFrame(root, width=256, fg_color=c["panel2"], corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(3, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=16, pady=(20, 18))
        brand.grid_columnconfigure(1, weight=1)
        try:
            mark_img = Image.open(logo_mark_path()).convert("RGBA")
            mark_ck = ctk.CTkImage(light_image=mark_img, dark_image=mark_img, size=(42, 42))
            ctk.CTkLabel(brand, image=mark_ck, text="").grid(row=0, column=0, rowspan=2, padx=(0, 12))
        except Exception:
            logo = ctk.CTkFrame(brand, width=42, height=42, fg_color=c["brand"], corner_radius=10)
            logo.grid(row=0, column=0, rowspan=2, padx=(0, 12))
            logo.grid_propagate(False)
            ctk.CTkLabel(logo, text="B2", text_color="white", font=title_font(15)).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(brand, text="B2 CARGO", text_color=c["fg"], anchor="w", font=title_font(15)).grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(brand, text="PDF AYIRMA", text_color=c["muted"], anchor="w", font=font(11, "bold")).grid(row=1, column=1, sticky="ew")

        section_label(sidebar, "Menü").grid(row=1, column=0, sticky="ew", padx=22, pady=(4, 8))

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.grid(row=2, column=0, sticky="new", padx=14, pady=(4, 0))
        nav_icons.clear()
        error_n = state["result"].error_count if state["result"] else 0
        nav_items = [
            ("islem", "İşlem", icon_islem),
            ("ozet", "Özet", icon_ozet),
            ("bolgeler", "Bölgeler", icon_bolgeler),
            ("hata", "Hata", icon_hata),
        ]
        for key, label, icon_fn in nav_items:
            nav_icons[key] = {"active": icon_fn(c["fg"]), "inactive": icon_fn(c["muted"])}
            row = ctk.CTkFrame(nav, fg_color="transparent")
            row.pack(fill="x", pady=3)
            btn = ctk.CTkButton(
                row, text=label, image=nav_icons[key]["inactive"], compound="left", anchor="w",
                height=42, corner_radius=10, fg_color="transparent", hover_color=c["panel"],
                text_color=c["muted"], font=font(13, "bold"), command=lambda k=key: set_view(k),
            )
            btn.pack(fill="x", side="left", expand=True)
            if key == "hata" and error_n:
                ctk.CTkLabel(
                    row, text=str(error_n), text_color=c["warn"], fg_color=c["panel"],
                    corner_radius=6, width=22, height=18, font=mono_font(11, "bold"),
                ).place(in_=btn, relx=0.92, rely=0.5, anchor="e")
            nav_buttons[key] = btn
        nonlocal_accent = ctk.CTkFrame(nav, fg_color=c["brand2"], width=3, corner_radius=0)
        nav_accent_holder["w"] = nonlocal_accent

        footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="sew", padx=14, pady=16)
        wordmark_box = ctk.CTkFrame(footer, fg_color="white", corner_radius=10)
        wordmark_box.pack(fill="x", pady=(0, 10))
        try:
            wm_img = Image.open(logo_wordmark_path()).convert("RGBA")
            ratio = wm_img.height / wm_img.width
            wm_w = 196
            wm_ck = ctk.CTkImage(light_image=wm_img, dark_image=wm_img, size=(wm_w, int(wm_w * ratio)))
            ctk.CTkLabel(wordmark_box, image=wm_ck, text="").pack(padx=10, pady=10)
        except Exception:
            ctk.CTkLabel(wordmark_box, text="B2 CARGO Lojistik", text_color="#17255A", font=title_font(13)).pack(padx=10, pady=12)

        shift_card = card(footer, fg_color=c["panel"], radius=10)
        shift_card.pack(fill="x", pady=(0, 10))
        shift_inner = ctk.CTkFrame(shift_card, fg_color="transparent")
        shift_inner.pack(fill="x", padx=13, pady=10)
        shift_inner.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(shift_inner, text="AKTİF VARDİYA", text_color=c["muted"], anchor="w", font=font(9, "bold")).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(shift_inner, textvariable=shift_name_var, text_color=c["fg"], anchor="w", font=mono_font(14, "bold")).grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(shift_inner, image=icon_chevron(c["muted"]), text="").grid(row=0, column=1, rowspan=2, sticky="e")

        theme_icon = icon_moon(c["brand"]) if is_dark else icon_sun(c["brand"])
        theme_btn = ctk.CTkButton(
            footer, text=f"{'Koyu' if is_dark else 'Açık'} tema", image=theme_icon, compound="left",
            height=40, fg_color=c["panel"], hover_color=c["panel2"], border_color=c["border"], border_width=1,
            text_color=c["fg"], font=font(12, "bold"), corner_radius=10, command=toggle_theme,
        )
        theme_btn.pack(fill="x")

        # ---------------- ana icerik ----------------
        content = ctk.CTkFrame(root, fg_color=c["bg"], corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, textvariable=crumb_var, text_color=c["muted"], anchor="w", font=font(12, "bold")).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, textvariable=page_title_var, text_color=c["fg"], anchor="w", font=title_font(23)).grid(row=1, column=0, sticky="ew")

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=2, sticky="e")
        has_result = state["result"] is not None
        has_error = has_result and state["result"].error_count > 0
        btn_region = secondary_button(actions, "Bölge Ayarları", icon_gear(c["fg"]), open_region_settings)
        btn_region.pack(side="left", padx=(0, 8))
        btn_report = secondary_button(actions, "Vardiya Raporu", icon_list(c["fg"]), open_shift_report, state="normal" if has_result else "disabled")
        btn_report.pack(side="left", padx=8)
        btn_hata = secondary_button(actions, "Hata Klasörü", icon_hata(c["warn"]), open_error_folder, state="normal" if has_error else "disabled")
        btn_hata.pack(side="left", padx=8)
        btn_out = primary_button(actions, "Çıktı Klasörü", icon_folder("white"), open_output, state="normal" if has_result else "disabled")
        btn_out.pack(side="left", padx=(8, 0))

        body = ctk.CTkScrollableFrame(content, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 20))
        body.grid_columnconfigure(0, weight=1)
        for key in ("islem", "ozet", "bolgeler", "hata"):
            f = ctk.CTkFrame(body, fg_color="transparent")
            f.grid(row=0, column=0, sticky="nsew")
            f.grid_columnconfigure(0, weight=1)
            view_frames[key] = f

        build_islem_view(view_frames["islem"])
        render_result_views()
        set_view(state["tab"])

    nav_icons: dict[str, dict] = {}
    nav_accent_holder: dict = {}
    crumb_var = ctk.StringVar(value="İşlem")
    page_title_var = ctk.StringVar(value="İrsaliyeleri Ayır")
    shift_name_var = ctk.StringVar(value="(otomatik)")

    def _update_shift_name(*_args) -> None:
        shift_name_var.set(name_var.get().strip() or "(otomatik)")

    name_var.trace_add("write", _update_shift_name)

    def toggle_theme() -> None:
        state["theme"] = "light" if state["theme"] == "dark" else "dark"
        save_theme(state["theme"])
        build()

    # ------------------------------------------------------------------ #
    # Bolge Ayarlari penceresi (mevcut ozellik; yeni gorsel dile uyarlandi)
    # ------------------------------------------------------------------ #
    def open_region_settings() -> None:
        c = C()
        win = ctk.CTkToplevel(root)
        win.title("Bölge Ayarları")
        win.geometry("820x640")
        win.minsize(680, 500)
        win.configure(fg_color=c["bg"])
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
        ctk.CTkLabel(top, text="Bölge Ayarları", text_color=c["fg"], font=title_font(20)).pack(side="left")
        ctk.CTkLabel(top, text="regions.yaml", text_color=c["muted"], font=mono_font(12)).pack(side="right")

        editor = ctk.CTkTextbox(
            win, wrap="none", fg_color=c["panel2"], border_color=c["border"], border_width=1,
            text_color=c["fg"], corner_radius=10, font=mono_font(12),
        )
        editor.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        editor.insert("1.0", initial)

        status = ctk.StringVar(value=f"Dosya: {target}")
        ctk.CTkLabel(win, textvariable=status, anchor="w", text_color=c["muted"], font=font(12)).pack(fill="x", padx=20, pady=(0, 10))
        actions_row = ctk.CTkFrame(win, fg_color="transparent")
        actions_row.pack(fill="x", padx=20, pady=(0, 16))

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
            status.set("Çakışma var: " + ", ".join(sorted(rm.conflicts)) if rm.conflicts else "YAML geçerli. Çakışma yok.")

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

        secondary_button(actions_row, "Doğrula", command=validate_regions).pack(side="left", padx=(0, 8))
        primary_button(actions_row, "Kaydet", command=save_regions).pack(side="left", padx=(0, 8))
        secondary_button(actions_row, "Kapat", command=win.destroy).pack(side="right")

    # ------------------------------------------------------------------ #
    # Islem ekrani (idle / running / done)
    # ------------------------------------------------------------------ #
    def build_islem_view(parent) -> None:
        c = C()
        source_card = card(parent, radius=14)
        source_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        source_card.grid_columnconfigure(0, weight=1)
        section_label(source_card, "Kaynak klasör ve vardiya").grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(16, 10))

        folder_row = ctk.CTkFrame(source_card, fg_color="transparent")
        folder_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20)
        folder_row.grid_columnconfigure(0, weight=1)
        folder_entry = entry(folder_row, textvariable=folder_var, height=40, font=mono_font(12))
        folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        def pick_folder() -> None:
            start_dir = folder_var.get() if Path(folder_var.get()).is_dir() else str(base_dir())
            chosen = filedialog.askdirectory(initialdir=start_dir, title="İrsaliye klasörünü seç")
            if chosen:
                folder_var.set(chosen)
                refresh_idle_count()

        secondary_button(folder_row, "Klasör Seç", command=pick_folder, height=40).grid(row=0, column=1)

        name_row = ctk.CTkFrame(source_card, fg_color="transparent")
        name_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(12, 18))
        name_row.grid_columnconfigure(0, weight=1)
        entry(name_row, textvariable=name_var, placeholder_text="Vardiya adı (boş = otomatik tarih)", height=40).grid(row=0, column=0, sticky="ew")

        if conflicts:
            warn_row = ctk.CTkFrame(source_card, fg_color=c["panel2"], border_color=c["warn"], border_width=1, corner_radius=10)
            warn_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 18))
            ctk.CTkLabel(
                warn_row, image=icon_warn_circle(c["warn"]), text=f"  Birden çok bölgeye düşen şehir(ler): {conflicts}. Bu belgeler Hata'ya gönderilir.",
                compound="left", text_color=c["fg"], anchor="w", justify="left", wraplength=680, font=font(12),
            ).pack(fill="x", padx=14, pady=10)

        state_container = ctk.CTkFrame(parent, fg_color="transparent")
        state_container.grid(row=1, column=0, sticky="nsew")
        state_container.grid_columnconfigure(0, weight=1)
        islem_refs["state_container"] = state_container
        render_islem_state()

    islem_refs: dict = {}

    def refresh_idle_count() -> None:
        lbl = islem_refs.get("idle_count_label")
        if lbl is None:
            return
        n = 0
        p = Path(folder_var.get())
        if p.is_dir():
            n = len(list(p.glob("*.pdf")))
        vardiya = name_var.get().strip() or "(otomatik)"
        lbl.configure(text=f"irsaliye bekliyor · vardiya {vardiya}")
        islem_refs["idle_count_value"].configure(text=str(n))

    def render_islem_state() -> None:
        c = C()
        container = islem_refs["state_container"]
        for w in container.winfo_children():
            w.destroy()
        if state["spinner"] is not None:
            state["spinner"].stop()
            state["spinner"] = None

        phase = state["phase"]
        if phase == "idle":
            drop = card(container, fg_color=c["panel2"], radius=18)
            drop.configure(border_width=2)
            drop.grid(row=0, column=0, sticky="ew", pady=(0, 18))
            drop.grid_columnconfigure(0, weight=1)
            try:
                mark_img = Image.open(logo_mark_path()).convert("RGBA")
                mark_ck = ctk.CTkImage(light_image=mark_img, dark_image=mark_img, size=(76, 76))
                ctk.CTkLabel(drop, image=mark_ck, text="").grid(row=0, column=0, pady=(40, 16))
            except Exception:
                pass
            ctk.CTkLabel(drop, text="Gelen_PDF klasörü hazır", text_color=c["fg"], font=title_font(18)).grid(row=1, column=0, pady=(0, 8))
            count_row = ctk.CTkFrame(drop, fg_color="transparent")
            count_row.grid(row=2, column=0, pady=(0, 26))
            value_lbl = ctk.CTkLabel(count_row, text="0", text_color=c["fg"], font=mono_font(14, "bold"))
            value_lbl.pack(side="left")
            desc_lbl = ctk.CTkLabel(count_row, text="  irsaliye bekliyor · vardiya (otomatik)", text_color=c["muted"], font=font(13))
            desc_lbl.pack(side="left")
            islem_refs["idle_count_value"] = value_lbl
            islem_refs["idle_count_label"] = desc_lbl

            ayir_w, ayir_h = 300, 60
            ayir_img = pill_image(
                "AYIR", ayir_w, ayir_h, c["brand2"], c["gold"], "white",
                fonts_dir() / "Manrope-ExtraBold.ttf", 18, icon_draw=None,
            )
            ayir_ck = ctk.CTkImage(light_image=ayir_img, dark_image=ayir_img, size=(ayir_w, ayir_h))
            ayir_btn = ctk.CTkLabel(drop, image=ayir_ck, text="", cursor="hand2")
            ayir_btn.grid(row=3, column=0, pady=(0, 40))
            ayir_btn.bind("<Button-1>", lambda _e: start())

            refresh_idle_count()

            info_row = ctk.CTkFrame(container, fg_color="transparent")
            info_row.grid(row=1, column=0, sticky="ew")
            info_row.grid_columnconfigure((0, 1), weight=1, uniform="info")
            rule_card = card(info_row, radius=14)
            rule_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
            section_label(rule_card, "Ayırma kuralı").pack(anchor="w", padx=18, pady=(16, 6))
            ctk.CTkLabel(
                rule_card,
                text="DSV listesindekiler DSV klasörüne; geri kalanlar bölgeye göre B2 altına. Her bölgede Palet (≥9 koli) ve Dökme (≤8 koli) ayrılır.",
                text_color=c["fg"], anchor="w", justify="left", wraplength=380, font=font(13),
            ).pack(anchor="w", padx=18, pady=(0, 16))
            cfg_card = card(info_row, radius=14)
            cfg_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
            section_label(cfg_card, "Yapılandırma").pack(anchor="w", padx=18, pady=(16, 6))
            ctk.CTkLabel(
                cfg_card, text=f"{config_path().name}\n{dsv_path().name}",
                text_color=c["muted"], anchor="w", justify="left", font=mono_font(12),
            ).pack(anchor="w", padx=18, pady=(0, 16))

        elif phase == "running":
            box = card(container, radius=18)
            box.grid(row=0, column=0, sticky="ew")
            box.grid_columnconfigure(0, weight=1)
            spinner = Spinner(box, c, size=54, width=4)
            spinner.canvas.grid(row=0, column=0, pady=(44, 20))
            spinner.start()
            state["spinner"] = spinner
            ctk.CTkLabel(box, text="İrsaliyeler ayrılıyor…", text_color=c["fg"], font=title_font(17)).grid(row=1, column=0, pady=(0, 18))

            bar_w, bar_h = 560, 13
            img = progress_image(bar_w, bar_h, progress_pct["v"], c)
            ck = ctk.CTkImage(light_image=img, dark_image=img, size=(bar_w, bar_h))
            bar_lbl = ctk.CTkLabel(box, image=ck, text="")
            bar_lbl.grid(row=2, column=0)
            islem_refs["progress_label"] = bar_lbl
            progress_pct["drawn"] = progress_pct["v"]
            pct_lbl = ctk.CTkLabel(box, text=f"%{progress_pct['v']} · adres okunuyor & bölge eşleştiriliyor", text_color=c["muted"], font=mono_font(12))
            pct_lbl.grid(row=3, column=0, pady=(11, 44))
            islem_refs["progress_pct_label"] = pct_lbl

        else:  # done
            r = state["result"]
            total = 0
            region_n = 0
            err_n = 0
            out_dir = ""
            if r is not None:
                regions = region_stats(r, region_map)
                total = sum(reg["evrak"] for reg in regions) + r.dsv_count + r.error_count
                region_n = len(regions)
                err_n = r.error_count
                out_dir = r.out_dir
            box = card(container, fg_color=c["panel"], border_color=c["good"], radius=18)
            box.grid(row=0, column=0, sticky="ew")
            box.grid_columnconfigure(0, weight=1)
            circle = ctk.CTkFrame(box, width=58, height=58, fg_color=c["good"], corner_radius=29)
            circle.grid(row=0, column=0, pady=(36, 14))
            circle.grid_propagate(False)
            ctk.CTkLabel(circle, image=icon_check("white", size=28), text="").place(relx=0.5, rely=0.5, anchor="center")
            ctk.CTkLabel(box, text="Ayırma tamamlandı", text_color=c["fg"], font=title_font(18)).grid(row=1, column=0, pady=(0, 4))
            ctk.CTkLabel(
                box, text=f"{total} evrak · {region_n} bölge · {err_n} hata · {out_dir}",
                text_color=c["muted"], font=font(13),
            ).grid(row=2, column=0, padx=20, pady=(0, 18))
            go_btn = primary_button(box, "Özete git →", command=lambda: set_view("ozet"))
            go_btn.grid(row=3, column=0, pady=(0, 34))

    # ------------------------------------------------------------------ #
    # Ozet / Bolgeler / Hata (gercek sonuca gore doldurulur)
    # ------------------------------------------------------------------ #
    def render_result_views() -> None:
        render_ozet_view(view_frames["ozet"])
        render_bolgeler_view(view_frames["bolgeler"])
        render_hata_view(view_frames["hata"])

    def render_ozet_view(parent) -> None:
        for w in parent.winfo_children():
            w.destroy()
        c = C()
        result: PipelineResult | None = state["result"]
        if result is None:
            ctk.CTkLabel(
                parent, text="Henüz işlem yapılmadı. Bir vardiya ayırdıktan sonra özet burada görünecek.",
                text_color=c["muted"], font=font(14),
            ).grid(row=0, column=0, sticky="w", pady=20)
            return

        regions = region_stats(result, region_map)
        overview = build_overview(result, regions)

        kpi_grid = ctk.CTkFrame(parent, fg_color="transparent")
        kpi_grid.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        kpi_grid.grid_columnconfigure((0, 1, 2), weight=1, uniform="kpi")
        for i, item in enumerate(overview.kpis):
            kpi_card(kpi_grid, item).grid(row=i // 3, column=i % 3, sticky="nsew", padx=6, pady=6)

        lower = ctk.CTkFrame(parent, fg_color="transparent")
        lower.grid(row=1, column=0, sticky="ew")
        lower.grid_columnconfigure(0, weight=13, uniform="lower")
        lower.grid_columnconfigure(1, weight=10, uniform="lower")

        bucket_card = card(lower, radius=14)
        bucket_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(bucket_card, text="Kova dağılımı", text_color=c["fg"], font=font(14, "bold")).pack(anchor="w", padx=20, pady=(18, 14))

        def bar_row(parent_, left_text, left_val, right_text, right_val, pct_a, color_a, color_b):
            row = ctk.CTkFrame(parent_, fg_color="transparent")
            row.pack(fill="x", padx=20)
            labels = ctk.CTkFrame(row, fg_color="transparent")
            labels.pack(fill="x")
            ctk.CTkLabel(labels, text=f"{left_text} ", text_color=c["muted"], font=font(12)).pack(side="left")
            ctk.CTkLabel(labels, text=str(left_val), text_color=c["fg"], font=font(12, "bold")).pack(side="left")
            ctk.CTkLabel(labels, text=f"  {right_text} ", text_color=c["muted"], font=font(12)).pack(side="left")
            ctk.CTkLabel(labels, text=str(right_val), text_color=c["fg"], font=font(12, "bold")).pack(side="left")
            bar_w = 400
            img = two_tone_image(bar_w, 14, pct_a, color_a, color_b, 7)
            ck = ctk.CTkImage(light_image=img, dark_image=img, size=(bar_w, 14))
            bar_lbl = ctk.CTkLabel(row, image=ck, text="")
            bar_lbl.pack(fill="x", pady=(6, 16))
            return bar_lbl

        pal_dok_total = overview.palet + overview.dokme
        pal_pct = round(overview.palet / pal_dok_total * 100) if pal_dok_total else 0
        bar_row(bucket_card, "Palet", overview.palet, "Dökme", overview.dokme, pal_pct, c["brand"], c["brand2"])

        b2_dsv_total = overview.b2_total + overview.dsv_count
        b2_pct = round(overview.b2_total / b2_dsv_total * 100) if b2_dsv_total else 100
        bar_row(bucket_card, "B2", overview.b2_total, "DSV", overview.dsv_count, b2_pct, c["brand"], c["good"])

        top_card = card(lower, radius=14)
        top_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(top_card, text="En yoğun bölgeler", text_color=c["fg"], font=font(14, "bold")).pack(anchor="w", padx=20, pady=(18, 12))
        if not overview.top_regions:
            ctk.CTkLabel(top_card, text="Bölge verisi yok.", text_color=c["muted"], font=font(12)).pack(anchor="w", padx=20, pady=(0, 18))
        for r in overview.top_regions:
            row = ctk.CTkFrame(top_card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=(0, 12))
            ctk.CTkFrame(row, width=7, height=7, fg_color=c["brand2"], corner_radius=4).pack(side="left", padx=(0, 10))
            ctk.CTkLabel(row, text=r["ad"], text_color=c["fg"], font=font(13, "bold")).pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(row, text=f"{_fmt_int(r['koli'])} koli", text_color=c["muted"], font=mono_font(11)).pack(side="right")
        ctk.CTkLabel(top_card, text="", height=1).pack(pady=(0, 6))

    def render_bolgeler_view(parent) -> None:
        for w in parent.winfo_children():
            w.destroy()
        c = C()
        result: PipelineResult | None = state["result"]
        if result is None:
            ctk.CTkLabel(parent, text="İşlem tamamlanınca bölge listesi burada oluşur.", text_color=c["muted"], font=font(14)).grid(row=0, column=0, sticky="w", pady=20)
            return
        regions = region_stats(result, region_map)
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.grid(row=0, column=0, sticky="nsew")
        grid.grid_columnconfigure((0, 1), weight=1, uniform="bolge")
        for i, r in enumerate(regions):
            rc = card(grid, radius=14)
            rc.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=6)
            rc.grid_columnconfigure(0, weight=1)
            head = ctk.CTkFrame(rc, fg_color="transparent")
            head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 2))
            head.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(head, text=r["ad"], text_color=c["fg"], font=title_font(16)).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                head, text=f"{r['evrak']} evrak", text_color=c["muted"], fg_color=c["panel2"],
                corner_radius=7, font=mono_font(11), padx=8, pady=2,
            ).grid(row=0, column=1, sticky="e")
            ctk.CTkLabel(rc, text=r["il"] or "—", text_color=c["muted"], anchor="w", font=font(11)).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))

            stats_row = ctk.CTkFrame(rc, fg_color="transparent")
            stats_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))

            def stat_block(parent_, value, label, color=None):
                block = ctk.CTkFrame(parent_, fg_color="transparent")
                ctk.CTkLabel(block, text=value, text_color=color or c["fg"], font=mono_font(18, "bold")).pack(anchor="w")
                ctk.CTkLabel(block, text=label, text_color=c["muted"], font=font(10, "bold")).pack(anchor="w")
                return block

            stat_block(stats_row, str(r["koli"]), "koli").pack(side="left", padx=(0, 22))
            stat_block(stats_row, _fmt_kg(r["kg"]), "kg").pack(side="left", padx=(0, 22))
            stat_block(stats_row, f"{r['palet']}/{r['dokme']}", "palet / dökme", c["brand2"]).pack(side="right")

            bar_w = 300
            bimg = two_tone_image(bar_w, 8, r["pal_pct"], c["brand"], c["brand2"], 4)
            bck = ctk.CTkImage(light_image=bimg, dark_image=bimg, size=(bar_w, 8))
            ctk.CTkLabel(rc, image=bck, text="").grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 10))

            top_row = ctk.CTkFrame(rc, fg_color="transparent")
            top_row.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 16))
            ctk.CTkLabel(top_row, text="En büyük: ", text_color=c["muted"], font=font(11)).pack(side="left")
            ctk.CTkLabel(top_row, text=r["top"] or "—", text_color=c["fg"], font=font(11, "bold")).pack(side="left")

        if not regions:
            ctk.CTkLabel(parent, text="Bu vardiyada B2 bölgesine düşen evrak yok.", text_color=c["muted"], font=font(13)).grid(row=1, column=0, sticky="w", pady=12)

    def render_hata_view(parent) -> None:
        for w in parent.winfo_children():
            w.destroy()
        c = C()
        result: PipelineResult | None = state["result"]
        rows = error_rows(result) if result else []

        if result is None:
            ctk.CTkLabel(parent, text="Hata klasörü temiz.", text_color=c["muted"], font=font(14)).grid(row=0, column=0, sticky="w", pady=20)
            return

        if rows:
            banner = ctk.CTkFrame(parent, fg_color=c["panel2"], border_color=c["warn"], border_width=1, corner_radius=12)
            banner.grid(row=0, column=0, sticky="ew", pady=(0, 14))
            ctk.CTkLabel(
                banner, image=icon_warn_circle(c["warn"]),
                text=f"  {len(rows)} evrak Hata klasöründe — düzeltip Hata Klasörünü Tekrar Tara'ya basın.",
                compound="left", text_color=c["fg"], font=font(13), anchor="w",
            ).pack(fill="x", padx=16, pady=12)
        else:
            banner = ctk.CTkFrame(parent, fg_color=c["panel2"], border_color=c["good"], border_width=1, corner_radius=12)
            banner.grid(row=0, column=0, sticky="ew", pady=(0, 14))
            ctk.CTkLabel(
                banner, image=icon_check(c["good"], size=16), text="  Hata klasörü temiz. Bu vardiya sorunsuz ayrıldı.",
                compound="left", text_color=c["fg"], font=font(13), anchor="w",
            ).pack(fill="x", padx=16, pady=12)

        table = card(parent, radius=14)
        table.grid(row=1, column=0, sticky="ew")
        table.grid_columnconfigure((0, 1, 2), weight=1)
        head = ctk.CTkFrame(table, fg_color=c["panel2"], corner_radius=0)
        head.grid(row=0, column=0, columnspan=3, sticky="ew")
        head.grid_columnconfigure((0, 1, 2), weight=1, uniform="hata")
        for i, text in enumerate(("ALICI", "NEDEN", "ÖNERİ")):
            ctk.CTkLabel(head, text=text, text_color=c["muted"], anchor="w", font=font(10, "bold")).grid(row=0, column=i, sticky="ew", padx=20, pady=10)

        if not rows:
            ctk.CTkLabel(table, text="Gösterilecek hata yok.", text_color=c["muted"], font=font(12)).grid(row=1, column=0, columnspan=3, sticky="w", padx=20, pady=16)
        for i, row in enumerate(rows, start=1):
            ctk.CTkLabel(table, text=row["alici"], text_color=c["fg"], anchor="w", justify="left", font=font(13, "bold"), wraplength=220).grid(row=i, column=0, sticky="new", padx=20, pady=(12, 4))
            ctk.CTkLabel(
                table, text=row["neden"], text_color=c["warn"], fg_color=c["chip"], corner_radius=7,
                font=font(11, "bold"), padx=8, pady=3,
            ).grid(row=i, column=1, sticky="nw", padx=20, pady=(12, 4))
            ctk.CTkLabel(table, text=row["oneri"], text_color=c["muted"], anchor="w", justify="left", wraplength=320, font=font(12)).grid(row=i, column=2, sticky="new", padx=20, pady=(12, 4))
            ctk.CTkFrame(table, fg_color=c["border"], height=1).grid(row=i, column=0, columnspan=3, sticky="ew", padx=0, pady=(10, 0))

        actions_row = ctk.CTkFrame(table, fg_color="transparent")
        actions_row.grid(row=len(rows) + 1, column=0, columnspan=3, sticky="e", padx=16, pady=14)
        secondary_button(actions_row, "Hata Raporu (CSV)", command=open_error_report, state="normal" if rows else "disabled").pack(side="left", padx=(0, 8))
        secondary_button(actions_row, "Hata Klasörünü Tekrar Tara", icon_refresh(c["fg"]), rescan_errors, state="normal" if rows else "disabled").pack(side="left")

    # ------------------------------------------------------------------ #
    # islem akisi (arkaplan thread'i, ilerleme, sonuc)
    # ------------------------------------------------------------------ #
    def update_progress(done: int, total: int, _filename: str) -> None:
        ratio = round((done / total) * 100) if total else 0
        progress_pct["v"] = ratio
        pct_lbl = islem_refs.get("progress_pct_label")
        if pct_lbl is not None:
            pct_lbl.configure(text=f"%{ratio} · adres okunuyor & bölge eşleştiriliyor ({done}/{total})")
        # Metin (islenen/toplam) her belgede guncellenir ama gradyan resmi
        # -pahali piksel-piksel uretim- yalnizca gorunen yuzde gercekten
        # degistiginde yeniden cizilir; buyuk/hizli vardiyalarda ana thread'i
        # gereksiz yere mesgul etmemek icin.
        if ratio == progress_pct.get("drawn"):
            return
        progress_pct["drawn"] = ratio
        lbl = islem_refs.get("progress_label")
        if lbl is not None:
            bar_w, bar_h = 560, 13
            img = progress_image(bar_w, bar_h, ratio, C())
            ck = ctk.CTkImage(light_image=img, dark_image=img, size=(bar_w, bar_h))
            lbl.configure(image=ck)
            lbl.image = ck

    def on_done(result: PipelineResult | None, error: Exception | None) -> None:
        if error is not None:
            state["phase"] = "idle"
            render_islem_state()
            messagebox.showerror("Hata", f"İşlem sırasında hata oluştu:\n{error}")
            return
        assert result is not None
        state["result"] = result
        state["phase"] = "done"
        state["tab"] = "ozet"
        shift_name_var.set(result.shift_name)
        build()

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
        state["phase"] = "running"
        progress_pct["v"] = 0
        set_view("islem")
        render_islem_state()
        threading.Thread(target=worker, args=(input_dir, name_var.get().strip() or None), daemon=True).start()

    def open_output() -> None:
        if state["result"]:
            open_in_explorer(state["result"].out_dir)

    def open_shift_report() -> None:
        if state["result"]:
            open_in_explorer(Path(state["result"].out_dir) / "vardiya_raporu.csv")

    def open_error_report() -> None:
        r = state["result"]
        if r and r.error_count:
            open_in_explorer(Path(r.out_dir) / "Hata" / "Hata_raporu.csv")

    def open_error_folder() -> None:
        r = state["result"]
        if r and r.error_count:
            open_in_explorer(Path(r.out_dir) / "Hata")

    def rescan_errors() -> None:
        r = state["result"]
        if not r or not r.error_count:
            return
        hata_dir = Path(r.out_dir) / "Hata"
        if not hata_dir.is_dir():
            messagebox.showwarning("Hata klasörü yok", f"Bulunamadı:\n{hata_dir}")
            return
        folder_var.set(str(hata_dir))
        name_var.set(f"Hata_tekrar_{datetime.now().strftime('%H%M%S')}")
        start()

    build()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
