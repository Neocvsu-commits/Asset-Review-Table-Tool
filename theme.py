"""TexTool 系列视觉令牌与 ttk 样式装配。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# TexTool 的语义色转换为 Tk 可直接使用的 sRGB。
PALETTES: dict[str, dict[str, str]] = {
    "dark": {
        "base_100": "#181B1E",
        "base_200": "#0D1013",
        "base_300": "#27292D",
        "border": "#34383E",
        "content": "#D5D4D0",
        "muted": "#8F8E8A",
        "primary": "#248A3F",
        "primary_hover": "#57A364",
        "primary_content": "#F8F8F8",
        "disabled_bg": "#232529",
        "disabled_fg": "#5F6266",
        "success": "#59A36A",
        "warning": "#D2A33B",
        "error": "#C45B55",
    },
    "light": {
        "base_100": "#FFFFFF",
        "base_200": "#F7F7F8",
        "base_300": "#E4E5E7",
        "border": "#D2D4D7",
        "content": "#20242A",
        "muted": "#686D74",
        "primary": "#2879B8",
        "primary_hover": "#3E8BC6",
        "primary_content": "#FFFFFF",
        "disabled_bg": "#ECEDEF",
        "disabled_fg": "#9A9EA4",
        "success": "#348755",
        "warning": "#9A6D12",
        "error": "#B64640",
    },
}

ZOOM_STEPS = (90, 100, 110, 125)
FONT_FAMILY = "Microsoft YaHei UI"


def resolve_theme(preference: str, system_prefers_light: bool) -> str:
    """把 dark / light / system 偏好解析为实际主题。"""
    if preference == "system":
        return "light" if system_prefers_light else "dark"
    return preference if preference in PALETTES else "dark"


def _fonts(zoom: int) -> dict[str, tuple]:
    scale = max(90, min(125, zoom)) / 100
    size = lambda value: max(8, round(value * scale))
    return {
        "title": (FONT_FAMILY, size(15), "bold"),
        "section": (FONT_FAMILY, size(10), "bold"),
        "body": (FONT_FAMILY, size(9)),
        "small": (FONT_FAMILY, size(8)),
        "primary": (FONT_FAMILY, size(10), "bold"),
        "brand": (FONT_FAMILY, size(11), "bold"),
        "log": ("Consolas", size(9)),
    }


def native_widget_options(theme: str = "dark", zoom: int = 100) -> tuple[dict, dict]:
    """返回 Listbox 与 Text 的主题参数，保持裸 Tk 控件同色。"""
    palette = PALETTES[theme]
    fonts = _fonts(zoom)
    common = {
        "bg": palette["base_200"],
        "fg": palette["content"],
        "relief": "flat",
        "highlightthickness": 1,
        "highlightbackground": palette["border"],
        "highlightcolor": palette["primary"],
    }
    listbox = {
        **common,
        "font": fonts["body"],
        "selectbackground": palette["primary"],
        "selectforeground": palette["primary_content"],
        "activestyle": "none",
        "exportselection": False,
    }
    log = {**common, "font": fonts["log"], "wrap": "word", "insertbackground": palette["content"]}
    return listbox, log


def apply_theme(root: tk.Tk, theme: str = "dark", zoom: int = 100) -> dict[str, str]:
    """装配全部语义样式，并返回当前色板。"""
    palette = PALETTES[theme]
    fonts = _fonts(zoom)
    pad = max(4, round(5 * zoom / 100))
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background=palette["base_100"], foreground=palette["content"], font=fonts["body"])
    style.configure("TFrame", background=palette["base_100"])
    style.configure("Sidebar.TFrame", background=palette["base_200"])
    style.configure("Card.TFrame", background=palette["base_100"])
    style.configure("Footer.TFrame", background=palette["base_200"])
    style.configure("TLabel", background=palette["base_100"], foreground=palette["content"])
    style.configure("Sidebar.TLabel", background=palette["base_200"], foreground=palette["content"])
    style.configure("Sidebar.Muted.TLabel", background=palette["base_200"], foreground=palette["muted"], font=fonts["small"])
    style.configure("Brand.TLabel", background=palette["base_200"], foreground=palette["content"], font=fonts["brand"])
    style.configure("Title.TLabel", foreground=palette["content"], font=fonts["title"])
    style.configure("Subtitle.TLabel", foreground=palette["muted"], font=fonts["body"])
    style.configure("Section.TLabel", foreground=palette["content"], font=fonts["section"])
    style.configure("Hint.TLabel", foreground=palette["muted"], font=fonts["small"])
    style.configure("Status.TLabel", background=palette["base_200"], foreground=palette["muted"], font=fonts["small"])
    style.configure("Status.Success.TLabel", background=palette["base_200"], foreground=palette["success"], font=fonts["small"])
    style.configure("Status.Error.TLabel", background=palette["base_200"], foreground=palette["error"], font=fonts["small"])

    style.configure(
        "TLabelframe",
        background=palette["base_100"],
        bordercolor=palette["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure("TLabelframe.Label", background=palette["base_100"], foreground=palette["muted"], font=fonts["small"])

    style.configure(
        "TButton",
        background=palette["base_300"],
        foreground=palette["content"],
        bordercolor=palette["border"],
        padding=(round(11 * zoom / 100), pad),
        relief="flat",
        font=fonts["body"],
    )
    style.map(
        "TButton",
        background=[("active", palette["border"]), ("pressed", palette["base_200"]), ("disabled", palette["disabled_bg"])],
        foreground=[("disabled", palette["disabled_fg"])],
    )
    style.configure(
        "Primary.TButton",
        background=palette["primary"],
        foreground=palette["primary_content"],
        bordercolor=palette["primary"],
        padding=(round(16 * zoom / 100), round(8 * zoom / 100)),
        relief="flat",
        font=fonts["primary"],
    )
    style.map(
        "Primary.TButton",
        background=[("active", palette["primary_hover"]), ("pressed", palette["primary"]), ("disabled", palette["disabled_bg"])],
        foreground=[("disabled", palette["disabled_fg"])],
    )
    style.configure("Nav.TButton", background=palette["base_200"], foreground=palette["muted"], borderwidth=0, anchor="w", padding=(14, 9))
    style.map("Nav.TButton", background=[("active", palette["base_300"])], foreground=[("active", palette["content"])])
    style.configure("Nav.Active.TButton", background=palette["base_300"], foreground=palette["primary"], bordercolor=palette["primary"], borderwidth=1, anchor="w", padding=(14, 9), font=fonts["section"])
    style.map("Nav.Active.TButton", background=[("active", palette["base_300"])], foreground=[("active", palette["primary"])])
    style.configure("Link.TButton", background=palette["base_200"], foreground=palette["muted"], borderwidth=0, padding=(5, 2), font=fonts["small"])
    style.map("Link.TButton", foreground=[("active", palette["content"])], background=[("active", palette["base_300"])])

    style.configure(
        "TEntry",
        fieldbackground=palette["base_200"],
        foreground=palette["content"],
        bordercolor=palette["border"],
        lightcolor=palette["border"],
        darkcolor=palette["border"],
        padding=round(6 * zoom / 100),
        insertcolor=palette["content"],
    )
    style.map("TEntry", bordercolor=[("focus", palette["primary"])], foreground=[("disabled", palette["disabled_fg"])])

    style.configure("Horizontal.TProgressbar", troughcolor=palette["base_300"], background=palette["primary"], bordercolor=palette["base_300"], lightcolor=palette["primary"], darkcolor=palette["primary"], thickness=max(4, round(5 * zoom / 100)))

    style.configure(
        "Vertical.TScrollbar",
        background=palette["base_300"],
        troughcolor=palette["base_200"],
        bordercolor=palette["base_200"],
        arrowcolor=palette["muted"],
        relief="flat",
    )
    style.map("Vertical.TScrollbar", background=[("active", palette["border"])])

    root.configure(background=palette["base_100"])
    return palette
