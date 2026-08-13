"""深色视觉令牌与 ttk 样式装配（对齐 TexTool，oklch 精确转 hex）。

颜色与字号集中定义于此，组件代码禁止写死色值/字号（规则三）。
令牌来源：TexTool apps/desktop/frontend/src/styles/index.css 的 dark 主题。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ─── 色板（TexTool dark 主题，oklch 精确转换） ───
BG = "#181B1E"            # base-100 窗口底
BG_DEEP = "#0D1013"       # base-200 输入区/日志底
CARD = "#27292D"          # base-300 卡片
BORDER = "#34383E"        # 1px 边框
TEXT = "#D5D4D0"          # base-content 主文本
TEXT_SEC = "#8F8E8A"      # 次级文本
ACCENT = "#248A3F"        # primary 主按钮/选中
ACCENT_HOVER = "#57A364"  # accent hover
BTN_BG = "#27292D"        # 普通按钮
BTN_HOVER = "#34383E"
BTN_PRESSED = "#202327"
DISABLED_BG = "#232529"
DISABLED_FG = "#5F6266"

# ─── 字体 ───
FONT_FAMILY = "Microsoft YaHei UI"
FONT_TITLE = (FONT_FAMILY, 14, "bold")
FONT_BODY = (FONT_FAMILY, 9)
FONT_BTN_PRIMARY = (FONT_FAMILY, 10, "bold")
FONT_LOG = (FONT_FAMILY, 9)

# ─── 裸 tk 控件配色（ttk 样式无法覆盖 Listbox / Text / 原生 Scrollbar） ───
LISTBOX_OPTS: dict = {
    "bg": BG_DEEP,
    "fg": TEXT,
    "font": FONT_BODY,
    "selectbackground": ACCENT,
    "selectforeground": "#F8F8F8",
    "activestyle": "none",
    "relief": "flat",
    "highlightthickness": 1,
    "highlightbackground": BORDER,
    "highlightcolor": ACCENT,
    "exportselection": False,
}

LOG_OPTS: dict = {
    "bg": BG_DEEP,
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
        foreground="#F8F8F8",
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
        fieldbackground=BG_DEEP,
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
        background=BTN_BG,
        troughcolor=BG,
        bordercolor=BG,
        arrowcolor=TEXT_SEC,
        relief="flat",
    )
    style.map("Vertical.TScrollbar", background=[("active", BORDER)])
