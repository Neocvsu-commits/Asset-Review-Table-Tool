"""Tk 图形界面：选择多个资产根目录与输出位置，一键生成 Review 表格。"""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import DISABLED, END, NORMAL, filedialog, messagebox, scrolledtext, ttk

import tkinter as tk

from builder import build_report
from utils import desktop_dir, find_all_blenders, find_blender_exe, resolve_hdr


_TOOL_DIR = Path(__file__).resolve().parent


class ReviewToolApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("资产 Review 表格工具")
        self.minsize(640, 480)
        self.geometry("720x560")

        self._roots: tk.Listbox
        self._out_var = tk.StringVar(value=str(desktop_dir() / "资产Review导出"))
        self._blend_var = tk.StringVar()
        self._log: scrolledtext.ScrolledText
        self._run_btn: ttk.Button
        self._build_ui()

        if (b := find_blender_exe()):
            self._blend_var.set(str(b))

    # --- UI 搭建 ---------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        f0 = ttk.LabelFrame(
            self,
            text="资产根目录（其下为多个资产子文件夹，每个含 BasicInformation 与模型文件）",
        )
        f0.pack(fill=tk.BOTH, expand=True, **pad)
        self._roots = tk.Listbox(f0, height=8, selectmode=tk.EXTENDED)
        self._roots.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        btn_bar = ttk.Frame(f0)
        btn_bar.pack(fill=tk.X, padx=6, pady=4)
        ttk.Button(btn_bar, text="添加文件夹…", command=self._add_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="移除选中", command=self._remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_bar, text="清空", command=self._clear_roots).pack(side=tk.LEFT, padx=2)

        f1 = ttk.LabelFrame(self, text="输出目录（将生成 xlsx 与 thumbnails 子文件夹）")
        f1.pack(fill=tk.X, **pad)
        row = ttk.Frame(f1)
        row.pack(fill=tk.X, padx=6, pady=4)
        ttk.Entry(row, textvariable=self._out_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text="浏览…", command=self._browse_out).pack(side=tk.RIGHT)

        f2 = ttk.LabelFrame(self, text="Blender（blender.exe，用于渲染缩略图）")
        f2.pack(fill=tk.X, **pad)
        row = ttk.Frame(f2)
        row.pack(fill=tk.X, padx=6, pady=4)
        ttk.Entry(row, textvariable=self._blend_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row, text="自动查找", command=self._auto_blender).pack(side=tk.RIGHT, padx=2)
        ttk.Button(row, text="浏览…", command=self._browse_blender).pack(side=tk.RIGHT)

        self._run_btn = ttk.Button(self, text="开始生成表格（全量合并）", command=self._on_run)
        self._run_btn.pack(fill=tk.X, padx=8, pady=6)

        f3 = ttk.LabelFrame(self, text="日志")
        f3.pack(fill=tk.BOTH, expand=True, **pad)
        self._log = scrolledtext.ScrolledText(f3, height=10, state=DISABLED, wrap=tk.WORD)
        self._log.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

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
            self._log_line(f"已添加: {p}")

    def _remove_selected(self) -> None:
        for i in reversed(list(self._roots.curselection())):
            self._roots.delete(i)

    def _clear_roots(self) -> None:
        self._roots.delete(0, END)

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

        self._run_btn.configure(state=DISABLED)
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
                hdr=resolve_hdr(_TOOL_DIR),
                log=log,
            )
        except Exception as exc:
            self.after(0, lambda exc=exc: self._finish_with_error(str(exc)))
            return
        self.after(0, lambda: self._finish_with_success(xlsx_path))

    def _finish_with_success(self, xlsx_path: Path) -> None:
        self._run_btn.configure(state=NORMAL)
        messagebox.showinfo("完成", f"已生成表格:\n{xlsx_path}")

    def _finish_with_error(self, message: str) -> None:
        self._run_btn.configure(state=NORMAL)
        messagebox.showerror("失败", message)


def launch() -> None:
    ReviewToolApp().mainloop()


if __name__ == "__main__":
    launch()
