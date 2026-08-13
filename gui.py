"""Tk 图形界面：选择多个资产根目录与输出位置，一键生成 Review 表格。

视觉令牌集中在 theme.py；本文件只做布局与交互编排。
"""

from __future__ import annotations

import ctypes
import threading
from pathlib import Path
from tkinter import DISABLED, END, NORMAL, filedialog, messagebox, scrolledtext, ttk

import tkinter as tk

from builder import build_report
from main import __version__
from theme import BG_DEEP, BTN_BG, LISTBOX_OPTS, LOG_OPTS, apply_theme
from utils import desktop_dir, find_all_blenders, find_blender_exe, resolve_hdr, tool_dir

# DPI 感知必须在创建任何 Tk 实例前完成（规则二）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except (AttributeError, OSError):
    pass


class ReviewToolApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("资产 Review 表格工具")
        self.minsize(640, 480)
        apply_theme(self)

        self._running = False
        self._roots: tk.Listbox
        self._out_var = tk.StringVar(value=str(desktop_dir() / "资产Review导出"))
        self._blend_var = tk.StringVar()
        self._status_var = tk.StringVar(value="就绪")
        self._hint_var = tk.StringVar()
        self._log: scrolledtext.ScrolledText
        self._run_btn: ttk.Button
        self._inputs: list = []  # 运行中需要禁用的输入控件
        self._build_ui()
        self._fit_initial_size()
        self._update_run_state()

        if (b := find_blender_exe()):
            self._blend_var.set(str(b))
            self._log_line(f"已自动探测到 Blender: {b}")

    # --- UI 搭建 ---------------------------------------------------------

    def _build_ui(self) -> None:
        # 状态栏（先 pack 占住底部）
        status = ttk.Frame(self, padding=(16, 5))
        status.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(status, textvariable=self._status_var, style="Status.TLabel").pack(side=tk.LEFT)
        ttk.Label(status, text=f"v{__version__}", style="Status.TLabel").pack(side=tk.RIGHT)

        # 标题头
        header = ttk.Frame(self, padding=(16, 14, 16, 8))
        header.pack(fill=tk.X)
        ttk.Label(header, text="资产 Review 表格工具", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            header,
            text="扫描资产目录，自动渲染缩略图，生成带截图的 Excel 验收报表",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(4, 0))

        # 主按钮与提示（先 pack，窗口被压缩时优先保住它们）
        self._run_btn = ttk.Button(
            self,
            text="开始生成表格（全量合并）",
            style="Primary.TButton",
            command=self._on_run,
        )
        self._run_btn.pack(fill=tk.X, padx=16, pady=(10, 0))
        ttk.Label(self, textvariable=self._hint_var, style="Hint.TLabel").pack(pady=(4, 2))

        # 输出目录卡片
        f1 = ttk.LabelFrame(self, text=" 输出目录 ", padding=8)
        f1.pack(fill=tk.X, padx=16, pady=6)
        row = ttk.Frame(f1, style="Card.TFrame")
        row.pack(fill=tk.X)
        out_entry = ttk.Entry(row, textvariable=self._out_var)
        out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        out_btn = ttk.Button(row, text="浏览…", command=self._browse_out)
        out_btn.pack(side=tk.RIGHT)
        self._inputs.extend([out_entry, out_btn])

        # Blender 卡片
        f2 = ttk.LabelFrame(self, text=" Blender（blender.exe，用于渲染缩略图） ", padding=8)
        f2.pack(fill=tk.X, padx=16, pady=6)
        row = ttk.Frame(f2, style="Card.TFrame")
        row.pack(fill=tk.X)
        blend_entry = ttk.Entry(row, textvariable=self._blend_var)
        blend_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        auto_btn = ttk.Button(row, text="自动查找", command=self._auto_blender)
        auto_btn.pack(side=tk.RIGHT, padx=(8, 0))
        browse_btn = ttk.Button(row, text="浏览…", command=self._browse_blender)
        browse_btn.pack(side=tk.RIGHT)
        self._inputs.extend([blend_entry, auto_btn, browse_btn])

        # 资产根目录卡片（最后 pack 的可伸缩区，压缩时优先让位）
        f0 = ttk.LabelFrame(self, text=" 资产根目录 ", padding=8)
        f0.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 6))
        ttk.Label(
            f0,
            text="每个资产子文件夹需含 *_BasicInformation.csv 与模型文件（.glb 优先）",
            style="Card.Hint.TLabel",
        ).pack(anchor=tk.W, pady=(0, 4))
        self._roots = tk.Listbox(f0, height=6, selectmode=tk.EXTENDED, **LISTBOX_OPTS)
        self._roots.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        bar = ttk.Frame(f0, style="Card.TFrame")
        bar.pack(fill=tk.X)
        for text, cmd in (
            ("添加文件夹…", self._add_folder),
            ("移除选中", self._remove_selected),
            ("清空", self._clear_roots),
        ):
            btn = ttk.Button(bar, text=text, command=cmd)
            btn.pack(side=tk.LEFT, padx=(0, 8))
            self._inputs.append(btn)

        # 日志卡片（最末 pack，最优先被压缩）
        f3 = ttk.LabelFrame(self, text=" 日志 ", padding=8)
        f3.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 8))
        self._log = scrolledtext.ScrolledText(f3, height=6, state=DISABLED, width=60, **LOG_OPTS)
        self._log.pack(fill=tk.BOTH, expand=True)
        self._log.vbar.configure(
            background=BTN_BG, troughcolor=BG_DEEP, relief="flat",
            borderwidth=0, highlightthickness=0,
        )

    def _fit_initial_size(self) -> None:
        """按内容自然尺寸开窗（钳制在屏幕 92% 内），任何 DPI 下默认完整显示。"""
        self.update_idletasks()
        req_w, req_h = self.winfo_reqwidth(), self.winfo_reqheight()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(max(req_w, 640), int(sw * 0.92))
        h = min(max(req_h, 480), int(sh * 0.92))
        x = max((sw - w) // 2, 0)
        y = max((sh - h) // 3, 0)
        self.geometry(f"{w}x{h}+{x}+{y}")

    # --- 状态 ------------------------------------------------------------

    def _update_run_state(self) -> None:
        has_roots = self._roots.size() > 0
        self._run_btn.configure(state=NORMAL if (has_roots and not self._running) else DISABLED)
        if self._running:
            self._hint_var.set("生成中，请稍候…")
        elif not has_roots:
            self._hint_var.set("请先添加资产根目录")
        else:
            self._hint_var.set("")

    def _set_running(self, running: bool) -> None:
        self._running = running
        state = DISABLED if running else NORMAL
        for w in self._inputs:
            w.configure(state=state)
        self._run_btn.configure(text="生成中…" if running else "开始生成表格（全量合并）")
        self._status_var.set("生成中…" if running else "就绪")
        self._update_run_state()

    # --- 控件回调 --------------------------------------------------------

    def _log_line(self, msg: str) -> None:
        self._log.configure(state=NORMAL)
        self._log.insert(END, msg + "\n")
        self._log.see(END)
        self._log.configure(state=DISABLED)

    def _add_folder(self) -> None:
        p = filedialog.askdirectory(title="选择资产根目录")
        if p:
            self._roots.insert(END, p)
            self._update_run_state()
            self._log_line(f"已添加: {p}")

    def _remove_selected(self) -> None:
        for i in reversed(list(self._roots.curselection())):
            self._roots.delete(i)
        self._update_run_state()

    def _clear_roots(self) -> None:
        self._roots.delete(0, END)
        self._update_run_state()

    def _browse_out(self) -> None:
        p = filedialog.askdirectory(title="选择输出目录", initialdir=self._out_var.get() or str(desktop_dir()))
        if p:
            self._out_var.set(p)

    def _browse_blender(self) -> None:
        p = filedialog.askopenfilename(
            title="选择 blender.exe",
            filetypes=[("Blender", "blender.exe"), ("可执行文件", "*.exe"), ("全部", "*.*")],
        )
        if p:
            self._blend_var.set(p)

    def _auto_blender(self) -> None:
        cands = find_all_blenders()
        if not cands:
            messagebox.showwarning(
                "未找到",
                "未在常见路径或 PATH 中找到 Blender。\n请使用「浏览」手动选择 blender.exe。",
            )
            return
        self._blend_var.set(str(cands[0]))
        self._log_line(f"已选择 Blender: {cands[0]}")
        if len(cands) > 1:
            self._log_line(f"（另有 {len(cands) - 1} 个候选，当前取首个）")

    # --- 执行 ------------------------------------------------------------

    def _on_run(self) -> None:
        roots = [self._roots.get(i).strip() for i in range(self._roots.size())]
        roots = [r for r in roots if r]
        out = self._out_var.get().strip()
        blend = self._blend_var.get().strip()

        if not roots:
            messagebox.showerror("缺少目录", "请至少添加一个资产根目录。")
            return
        if not out:
            messagebox.showerror("缺少输出目录", "请指定输出目录。")
            return
        if not blend or not Path(blend).is_file():
            messagebox.showerror("Blender 无效", "请指定有效的 blender.exe，或点击「自动查找」。")
            return
        for r in roots:
            if not Path(r).is_dir():
                messagebox.showerror("路径无效", f"不是有效文件夹:\n{r}")
                return

        self._set_running(True)
        self._log_line("—— 开始执行 ——")
        threading.Thread(
            target=self._run_in_background,
            args=([Path(r) for r in roots], Path(out), Path(blend)),
            daemon=True,
        ).start()

    def _run_in_background(self, roots: list[Path], out_dir: Path, blender: Path) -> None:
        def log(msg: str) -> None:
            self.after(0, lambda: self._log_line(msg))

        try:
            xlsx_path = build_report(
                roots=roots,
                out_dir=out_dir,
                blender=blender,
                hdr=resolve_hdr(tool_dir()),
                log=log,
            )
        except Exception as exc:
            self.after(0, lambda exc=exc: self._finish_with_error(str(exc)))
            return
        self.after(0, lambda: self._finish_with_success(xlsx_path))

    def _finish_with_success(self, xlsx_path: Path) -> None:
        self._set_running(False)
        self._status_var.set("已完成")
        self._log_line(f"已生成表格: {xlsx_path}")

    def _finish_with_error(self, message: str) -> None:
        self._set_running(False)
        self._status_var.set("失败")
        self._log_line(f"[错误] {message}")
        messagebox.showerror("失败", message)


def launch() -> None:
    ReviewToolApp().mainloop()


if __name__ == "__main__":
    launch()
