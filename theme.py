"""Win11 浅色视觉令牌与 ttk 样式装配。

颜色与字号集中定义于此，组件代码禁止写死色值/字号（规则三）。
未来加深色主题时：增加一套暗色令牌映射，在 apply_theme 中按偏好切换。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ─── 色板（Win11 浅色） ───
BG = "#F3F3F3"            # 窗口底
CARD = "#FFFFFF"          # 卡片 / 输入框
BORDER = "#E5E5E5"        # 1px 边框
TEXT = "#1A1A1A"          # 主文本
TEXT_SEC = "#5F5F5F"      # 次级文本
ACCENT = "#0067C0"        # 强调蓝（主按钮 / 列表选中）
ACCENT_HOVER = "#1975C4"
BTN_BG = "#FFFFFF"        # 普通按钮
BTN_HOVER = "#F7F7F7"
BTN_PRESSED = "#EFEFEF"
DISABLED_BG = "#E5E5E5"
DISABLED_FG = "#9E9E9E"

# ─── 字体 ───
FONT_FAMILY = "Microsoft YaHei UI"
FONT_TITLE = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 9)
FONT_BTN_PRIMARY = (FONT_FAMILY, 10, "bold")
FONT_LOG = (FONT_FAMILY, 9)

# ─── 裸 tk 控件配色（ttk 样式无法覆盖 Listbox / Text / 原生 Scrollbar） ───
LISTBOX_OPTS: dict = {
    "bg": CARD,
    "fg": TEXT,
    "font": FONT_BODY,
    "selectbackground": ACCENT,
    "selectforeground": "#FFFFFF",
    "activestyle": "none",
    "relief": "flat",
    "highlightthickness": 1,
    "highlightbackground": BORDER,
    "highlightcolor": ACCENT,
    "exportselection": False,
}

LOG_OPTS: dict = {
    "bg": CARD,
    "fg": TEXT,
    "font": FONT_LOG,
    "relief": "flat",
    "highlightthickness": 1,
    "highlightbackground": BORDER,
    "wrap": "word",
}


def apply_theme(root: tk.Tk) -> None:
    """在构建任何控件前调用：装配 clam 主题与全部 ttk 样式。"""
    style = ttk.Style(root)
    style.theme_use("clam")

    # 基础
    style.configure(".", background=BG, foreground=TEXT, font=FONT_BODY)
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD)
    style.configure("TLabel", background=BG, foreground=TEXT, font=FONT_BODY)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT, font=FONT_BODY)
    style.configure("Card.Hint.TLabel", background=CARD, foreground=TEXT_SEC, font=FONT_BODY)
    style.configure("Title.TLabel", background=BG, foreground=TEXT, font=FONT_TITLE)
    style.configure("Subtitle.TLabel", background=BG, foreground=TEXT_SEC, font=FONT_BODY)
    style.configure("Hint.TLabel", background=BG, foreground=TEXT_SEC, font=FONT_BODY)
    style.configure("Status.TLabel", background=BG, foreground=TEXT_SEC, font=FONT_BODY)

    # 卡片（LabelFrame）
    style.configure(
        "TLabelframe",
        background=CARD,
        bordercolor=BORDER,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label", background=CARD, foreground=TEXT_SEC, font=FONT_BODY
    )

    # 按钮
    style.configure(
        "TButton",
        background=BTN_BG,
        foreground=TEXT,
        bordercolor=BORDER,
        padding=(12, 5),
        relief="flat",
        font=FONT_BODY,
    )
    style.map(
        "TButton",
        background=[
            ("active", BTN_HOVER),
            ("pressed", BTN_PRESSED),
            ("disabled", DISABLED_BG),
        ],
        foreground=[("disabled", DISABLED_FG)],
    )
    style.configure(
        "Primary.TButton",
        background=ACCENT,
        foreground="#FFFFFF",
        bordercolor=ACCENT,
        padding=(16, 7),
        relief="flat",
        font=FONT_BTN_PRIMARY,
    )
    style.map(
        "Primary.TButton",
        background=[
            ("active", ACCENT_HOVER),
            ("pressed", ACCENT),
            ("disabled", DISABLED_BG),
        ],
        foreground=[("disabled", DISABLED_FG)],
    )

    # 输入框
    style.configure(
        "TEntry",
        fieldbackground=CARD,
        foreground=TEXT,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=6,
        insertcolor=TEXT,
    )
    style.map("TEntry", bordercolor=[("focus", ACCENT)])

    # 滚动条
    style.configure(
        "Vertical.TScrollbar",
        background=BTN_HOVER,
        troughcolor=BG,
        bordercolor=BG,
        arrowcolor=TEXT_SEC,
        relief="flat",
    )
    style.map("Vertical.TScrollbar", background=[("active", BORDER)])
