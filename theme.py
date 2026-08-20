"""资产 Review 表格工具的固定浅色 ttk 样式。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


PALETTE: dict[str, str] = {
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
    "error": "#B64640",
}

FONT_FAMILY = "Microsoft YaHei UI"
FONTS = {
    "section": (FONT_FAMILY, 10, "bold"),
    "body": (FONT_FAMILY, 9),
    "small": (FONT_FAMILY, 8),
    "primary": (FONT_FAMILY, 10, "bold"),
    "log": ("Consolas", 9),
}


def native_widget_options() -> tuple[dict, dict]:
    """返回 Listbox 与 Text 的固定浅色参数。"""
    common = {
        "bg": PALETTE["base_200"],
        "fg": PALETTE["content"],
        "relief": "flat",
        "highlightthickness": 1,
        "highlightbackground": PALETTE["border"],
        "highlightcolor": PALETTE["primary"],
    }
    listbox = {
        **common,
        "font": FONTS["body"],
        "selectbackground": PALETTE["primary"],
        "selectforeground": PALETTE["primary_content"],
        "activestyle": "none",
        "exportselection": False,
    }
    log = {
        **common,
        "font": FONTS["log"],
        "wrap": "word",
        "insertbackground": PALETTE["content"],
    }
    return listbox, log


def apply_theme(root: tk.Tk) -> dict[str, str]:
    """装配工具使用的固定浅色样式，并返回色板。"""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        ".",
        background=PALETTE["base_100"],
        foreground=PALETTE["content"],
        font=FONTS["body"],
    )
    style.configure("TFrame", background=PALETTE["base_100"])
    style.configure(
        "TLabel",
        background=PALETTE["base_100"],
        foreground=PALETTE["content"],
    )
    style.configure(
        "Section.TLabel",
        foreground=PALETTE["content"],
        font=FONTS["section"],
    )
    style.configure(
        "Section.Success.TLabel",
        foreground=PALETTE["success"],
        font=FONTS["section"],
    )
    style.configure(
        "Section.Error.TLabel",
        foreground=PALETTE["error"],
        font=FONTS["section"],
    )
    style.configure(
        "Hint.TLabel",
        foreground=PALETTE["muted"],
        font=FONTS["small"],
    )

    style.configure(
        "TLabelframe",
        background=PALETTE["base_100"],
        bordercolor=PALETTE["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=PALETTE["base_100"],
        foreground=PALETTE["muted"],
        font=FONTS["small"],
    )

    style.configure(
        "TButton",
        background=PALETTE["base_300"],
        foreground=PALETTE["content"],
        bordercolor=PALETTE["border"],
        padding=(11, 5),
        relief="flat",
        font=FONTS["body"],
    )
    style.map(
        "TButton",
        background=[
            ("active", PALETTE["border"]),
            ("pressed", PALETTE["base_200"]),
            ("disabled", PALETTE["disabled_bg"]),
        ],
        foreground=[("disabled", PALETTE["disabled_fg"])],
    )
    style.configure(
        "Primary.TButton",
        background=PALETTE["primary"],
        foreground=PALETTE["primary_content"],
        bordercolor=PALETTE["primary"],
        padding=(16, 8),
        relief="flat",
        font=FONTS["primary"],
    )
    style.map(
        "Primary.TButton",
        background=[
            ("active", PALETTE["primary_hover"]),
            ("pressed", PALETTE["primary"]),
            ("disabled", PALETTE["disabled_bg"]),
        ],
        foreground=[("disabled", PALETTE["disabled_fg"])],
    )

    style.configure(
        "TEntry",
        fieldbackground=PALETTE["base_200"],
        foreground=PALETTE["content"],
        bordercolor=PALETTE["border"],
        lightcolor=PALETTE["border"],
        darkcolor=PALETTE["border"],
        padding=6,
        insertcolor=PALETTE["content"],
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", PALETTE["primary"])],
        foreground=[("disabled", PALETTE["disabled_fg"])],
    )
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=PALETTE["base_300"],
        background=PALETTE["primary"],
        bordercolor=PALETTE["base_300"],
        lightcolor=PALETTE["primary"],
        darkcolor=PALETTE["primary"],
        thickness=5,
    )
    style.configure(
        "Vertical.TScrollbar",
        background=PALETTE["base_300"],
        troughcolor=PALETTE["base_200"],
        bordercolor=PALETTE["base_200"],
        arrowcolor=PALETTE["muted"],
        relief="flat",
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", PALETTE["border"])],
    )

    root.configure(background=PALETTE["base_100"])
    return PALETTE
