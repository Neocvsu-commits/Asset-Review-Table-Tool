"""资产 Review 表格工具的轻量单页界面。"""

from __future__ import annotations

import ctypes
import json
import os
import threading
from pathlib import Path
from tkinter import DISABLED, END, NORMAL, filedialog, messagebox, scrolledtext, ttk

import tkinter as tk

from builder import BuildCancelled, build_report
from theme import apply_theme, native_widget_options
from utils import desktop_dir, find_all_blenders, resolve_hdr, tool_dir

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except (AttributeError, OSError):
    pass


APP_TITLE = "资产 Review 表格工具"
SETTINGS_FILE = Path(os.getenv("APPDATA", str(Path.home()))) / "AssetReviewTool" / "settings.json"


class ReviewToolApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(820, 560)

        self._settings = self._load_settings()
        self._settings.pop("theme", None)
        self._settings.pop("zoom", None)
        self._palette = apply_theme(self)

        self._running = False
        self._closing = False
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._detect_revision = 0
        self._last_output: Path | None = None
        self._inputs: list[tk.Widget] = []
        self._roots: tk.Listbox
        self._log: scrolledtext.ScrolledText
        self._run_btn: ttk.Button
        self._cancel_btn: ttk.Button
        self._open_btn: ttk.Button
        self._progress_label: ttk.Label
        self._progress: ttk.Progressbar

        self._out_var = tk.StringVar(
            value=self._settings.get("output_dir") or str(desktop_dir() / "资产Review导出")
        )
        self._blend_var = tk.StringVar(value=str(self._settings.get("blender_path") or ""))
        self._out_var.trace_add("write", self._on_path_edited)
        self._blend_var.trace_add("write", self._on_path_edited)
        self._hint_var = tk.StringVar(value="请先添加资产根目录")
        self._progress_var = tk.StringVar(value="等待开始")
        self._progress_value = tk.DoubleVar(value=0)
        self._root_count_var = tk.StringVar(value="0 个目录")

        self._build_ui()
        self._restore_window()
        self._update_run_state()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-Return>", lambda _event: self._on_run())
        self.bind("<Escape>", lambda _event: self._request_cancel())
        self.after(120, self._start_blender_detection)

    # ─── 布局 ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        content = ttk.Frame(self, padding=14)
        content.pack(fill=tk.BOTH, expand=True)
        content.columnconfigure(0, weight=3, minsize=400)
        content.columnconfigure(1, weight=2, minsize=280)
        content.rowconfigure(0, weight=1)

        left = ttk.Frame(content)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right = ttk.Frame(content)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._build_task_panel(left)
        self._build_feedback_panel(right)

    def _build_task_panel(self, parent: ttk.Frame) -> None:
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        card = ttk.LabelFrame(parent, text=" 任务配置 ", padding=14)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        heading = ttk.Frame(card)
        heading.grid(row=0, column=0, sticky="ew")
        ttk.Label(heading, text="资产根目录", style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Label(heading, textvariable=self._root_count_var, style="Hint.TLabel").pack(side=tk.RIGHT)
        ttk.Label(
            card,
            text="每个资产子文件夹需包含 *_BasicInformation.csv 与 .glb / .fbx 模型",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(3, 8))

        list_opts, _ = native_widget_options()
        list_frame = ttk.Frame(card)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self._roots = tk.Listbox(list_frame, height=9, selectmode=tk.EXTENDED, **list_opts)
        self._roots.grid(row=0, column=0, sticky="nsew")
        roots_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._roots.yview)
        roots_scroll.grid(row=0, column=1, sticky="ns")
        self._roots.configure(yscrollcommand=roots_scroll.set)
        root_actions = ttk.Frame(card)
        root_actions.grid(row=3, column=0, sticky="ew", pady=(8, 14))
        for text, cmd in (
            ("添加文件夹…", self._add_folder),
            ("移除选中", self._remove_selected),
            ("清空", self._clear_roots),
        ):
            button = ttk.Button(root_actions, text=text, command=cmd)
            button.pack(side=tk.LEFT, padx=(0, 7))
            self._inputs.append(button)

        ttk.Label(card, text="输出目录", style="Section.TLabel").grid(row=4, column=0, sticky="w")
        out_row = ttk.Frame(card)
        out_row.grid(row=5, column=0, sticky="ew", pady=(5, 13))
        out_row.columnconfigure(0, weight=1)
        out_entry = ttk.Entry(out_row, textvariable=self._out_var)
        out_entry.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        out_btn = ttk.Button(out_row, text="浏览…", command=self._browse_out)
        out_btn.grid(row=0, column=1)
        self._inputs.extend([out_entry, out_btn])

        ttk.Label(card, text="Blender", style="Section.TLabel").grid(row=6, column=0, sticky="w")
        ttk.Label(card, text="用于渲染模型缩略图，推荐 Blender 4.2 LTS", style="Hint.TLabel").grid(row=7, column=0, sticky="w", pady=(2, 5))
        blender_row = ttk.Frame(card)
        blender_row.grid(row=8, column=0, sticky="ew")
        blender_row.columnconfigure(0, weight=1)
        blend_entry = ttk.Entry(blender_row, textvariable=self._blend_var)
        blend_entry.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        browse_btn = ttk.Button(blender_row, text="浏览…", command=self._browse_blender)
        browse_btn.grid(row=0, column=1, padx=(0, 7))
        auto_btn = ttk.Button(blender_row, text="自动查找", command=self._start_blender_detection)
        auto_btn.grid(row=0, column=2)
        self._inputs.extend([blend_entry, browse_btn, auto_btn])

    def _build_feedback_panel(self, parent: ttk.Frame) -> None:
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        status_card = ttk.LabelFrame(parent, text=" 运行状态 ", padding=14)
        status_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        status_card.columnconfigure(0, weight=1)
        self._progress_label = ttk.Label(
            status_card, textvariable=self._progress_var, style="Section.TLabel"
        )
        self._progress_label.grid(row=0, column=0, sticky="w")
        self._progress = ttk.Progressbar(status_card, variable=self._progress_value, maximum=100)
        self._progress.grid(row=1, column=0, sticky="ew", pady=(9, 8))
        ttk.Label(status_card, textvariable=self._hint_var, style="Hint.TLabel").grid(row=2, column=0, sticky="w")

        log_card = ttk.LabelFrame(parent, text=" 任务日志 ", padding=10)
        log_card.grid(row=1, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(0, weight=1)
        _, log_opts = native_widget_options()
        self._log = scrolledtext.ScrolledText(log_card, state=DISABLED, width=36, height=16, **log_opts)
        self._log.grid(row=0, column=0, sticky="nsew")
        self._log.vbar.configure(
            background=self._palette["base_300"],
            troughcolor=self._palette["base_200"],
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )

        actions = ttk.Frame(parent)
        actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(0, weight=1)
        self._open_btn = ttk.Button(actions, text="打开输出目录", command=self._open_output)
        self._open_btn.grid(row=0, column=0, sticky="w")
        self._cancel_btn = ttk.Button(actions, text="取消", command=self._request_cancel, state=DISABLED)
        self._cancel_btn.grid(row=0, column=1, padx=(8, 0))
        self._run_btn = ttk.Button(
            actions, text="开始生成表格", style="Primary.TButton", command=self._on_run
        )
        self._run_btn.grid(row=0, column=2, padx=(8, 0))

    # ─── 状态 ─────────────────────────────────────────────────────────────

    def _update_run_state(self) -> None:
        count = self._roots.size()
        self._root_count_var.set(f"{count} 个目录")
        out_ready = bool(self._out_var.get().strip())
        blender_ready = Path(self._blend_var.get().strip()).is_file()
        ready = count > 0 and out_ready and blender_ready
        self._run_btn.configure(state=NORMAL if ready and not self._running else DISABLED)
        self._cancel_btn.configure(state=NORMAL if self._running else DISABLED)
        self._open_btn.configure(state=NORMAL if self._out_var.get().strip() else DISABLED)
        if self._running:
            self._hint_var.set("运行期间任务配置已锁定，可随时取消")
        elif not count:
            self._hint_var.set("请先添加资产根目录")
        elif not out_ready:
            self._hint_var.set("请指定输出目录")
        elif not blender_ready:
            self._hint_var.set("正在查找 Blender，或可手动指定 blender.exe")
        else:
            self._hint_var.set("已就绪 · Ctrl+Enter 开始")

    def _set_running(self, running: bool) -> None:
        self._running = running
        for widget in self._inputs:
            widget.configure(state=DISABLED if running else NORMAL)
        self._run_btn.configure(text="生成中…" if running else "开始生成表格")
        self._set_status_style("normal")
        self._update_run_state()

    def _set_status_style(self, kind: str) -> None:
        style = {
            "success": "Section.Success.TLabel",
            "error": "Section.Error.TLabel",
        }.get(kind, "Section.TLabel")
        self._progress_label.configure(style=style)

    def _on_path_edited(self, *_args) -> None:
        if hasattr(self, "_run_btn"):
            self.after_idle(self._update_run_state)

    # ─── 输入操作 ─────────────────────────────────────────────────────────

    def _add_folder(self) -> None:
        selected = filedialog.askdirectory(title="选择资产根目录")
        if not selected:
            return
        normalized = str(Path(selected).resolve())
        existing = {str(Path(path)).casefold() for path in self._roots.get(0, END)}
        if normalized.casefold() in existing:
            self._log_line(f"已忽略重复目录: {normalized}")
            return
        self._roots.insert(END, normalized)
        self._log_line(f"已添加: {normalized}")
        self._update_run_state()

    def _remove_selected(self) -> None:
        for index in reversed(list(self._roots.curselection())):
            self._roots.delete(index)
        self._update_run_state()

    def _clear_roots(self) -> None:
        self._roots.delete(0, END)
        self._update_run_state()

    def _browse_out(self) -> None:
        selected = filedialog.askdirectory(
            title="选择输出目录", initialdir=self._out_var.get() or str(desktop_dir())
        )
        if selected:
            self._out_var.set(selected)
            self._settings["output_dir"] = selected
            self._save_settings()
            self._update_run_state()

    def _browse_blender(self) -> None:
        selected = filedialog.askopenfilename(
            title="选择 blender.exe",
            filetypes=[("Blender", "blender.exe"), ("可执行文件", "*.exe"), ("全部文件", "*.*")],
        )
        if selected:
            self._set_blender_path(selected)

    def _start_blender_detection(self) -> None:
        if self._running or self._closing:
            return
        current = self._blend_var.get().strip()
        if current and Path(current).is_file():
            self._update_run_state()
            return
        self._progress_var.set("正在查找 Blender")
        self._set_status_style("normal")
        self._hint_var.set("正在后台检查常见安装位置…")
        self._detect_revision += 1
        revision = self._detect_revision
        starting_value = current
        threading.Thread(
            target=self._detect_blender,
            args=(revision, starting_value),
            daemon=True,
        ).start()

    def _detect_blender(self, revision: int, starting_value: str) -> None:
        candidates = find_all_blenders()
        if not self._closing:
            self.after(
                0,
                lambda: self._finish_blender_detection(candidates, revision, starting_value),
            )

    def _finish_blender_detection(
        self, candidates: list[Path], revision: int, starting_value: str
    ) -> None:
        if (
            self._closing
            or self._running
            or revision != self._detect_revision
            or self._blend_var.get().strip() != starting_value
        ):
            return
        if candidates:
            self._set_blender_path(str(candidates[0]))
            self._log_line(f"已自动探测到 Blender: {candidates[0]}")
        else:
            self._progress_var.set("未找到 Blender")
            self._set_status_style("error")
            self._hint_var.set("未找到 Blender，请点击“浏览…”手动指定")
        self._update_run_state()

    def _set_blender_path(self, path: str) -> None:
        self._blend_var.set(path)
        self._settings["blender_path"] = path
        self._save_settings()
        self._progress_var.set("等待开始")
        self._set_status_style("normal")
        self._update_run_state()

    # ─── 运行闭环 ─────────────────────────────────────────────────────────

    def _on_run(self) -> None:
        if self._running:
            return
        roots = [Path(path) for path in self._roots.get(0, END)]
        out_text = self._out_var.get().strip()
        blender_text = self._blend_var.get().strip()
        if not roots or not out_text or not blender_text:
            self._update_run_state()
            return
        out_dir = Path(out_text)
        blender = Path(blender_text)
        if not blender.is_file():
            self._update_run_state()
            return
        invalid = next((root for root in roots if not root.is_dir()), None)
        if invalid:
            messagebox.showerror("路径无效", f"不是有效文件夹：\n{invalid}", parent=self)
            return

        self._cancel_event.clear()
        self._progress_value.set(0)
        self._progress_var.set("正在扫描资产目录")
        self._set_running(True)
        self._log_line("—— 开始生成 Review 表格 ——")
        self._worker = threading.Thread(
            target=self._run_in_background,
            args=(roots, out_dir, blender),
            daemon=True,
        )
        self._worker.start()

    def _run_in_background(self, roots: list[Path], out_dir: Path, blender: Path) -> None:
        def log(message: str) -> None:
            self.after(0, lambda message=message: self._log_line(message))

        def progress(done: int, total: int, label: str) -> None:
            self.after(0, lambda: self._show_progress(done, total, label))

        try:
            output = build_report(
                roots=roots,
                out_dir=out_dir,
                blender=blender,
                hdr=resolve_hdr(tool_dir()),
                log=log,
                progress=progress,
                is_cancelled=self._cancel_event.is_set,
            )
        except BuildCancelled:
            self.after(0, self._finish_cancelled)
        except Exception as exc:
            self.after(0, lambda exc=exc: self._finish_with_error(str(exc)))
        else:
            self.after(0, lambda: self._finish_with_success(output))

    def _show_progress(self, done: int, total: int, label: str) -> None:
        percent = (done / total * 100) if total else 0
        self._progress_value.set(percent)
        self._progress_var.set(f"{done}/{total} · {label}")
        if "暂不可取消" in label:
            self._cancel_btn.configure(state=DISABLED)

    def _request_cancel(self) -> None:
        if not self._running or self._cancel_event.is_set():
            return
        self._cancel_event.set()
        self._cancel_btn.configure(state=DISABLED)
        self._progress_var.set("正在停止当前 Blender 任务")
        self._log_line("已请求取消任务…")

    def _finish_with_success(self, output: Path) -> None:
        self._last_output = output
        self._set_running(False)
        self._progress_value.set(100)
        self._progress_var.set("生成完成")
        self._hint_var.set(f"已保存：{output.name}")
        self._set_status_style("success")
        self._log_line(f"已生成表格: {output}")

    def _finish_cancelled(self) -> None:
        self._set_running(False)
        self._progress_var.set("任务已取消")
        self._hint_var.set("已保留当前输出目录中的既有文件")
        self._log_line("任务已取消")

    def _finish_with_error(self, message: str) -> None:
        self._set_running(False)
        self._progress_var.set("生成失败")
        self._hint_var.set("请查看任务日志后修正输入并重试")
        self._set_status_style("error")
        self._log_line(f"[错误] {message}")
        messagebox.showerror("生成失败", message, parent=self)

    def _open_output(self) -> None:
        target = Path(self._out_var.get().strip())
        if not target.exists():
            messagebox.showinfo("目录尚未创建", "输出目录会在首次生成时自动创建。", parent=self)
            return
        try:
            os.startfile(target)
        except OSError as exc:
            messagebox.showerror("无法打开目录", str(exc), parent=self)

    def _log_line(self, message: str) -> None:
        self._log.configure(state=NORMAL)
        self._log.insert(END, message + "\n")
        self._log.see(END)
        self._log.configure(state=DISABLED)

    # ─── 设置持久化与窗口 ─────────────────────────────────────────────────

    @staticmethod
    def _load_settings() -> dict:
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _safe_int(value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _save_settings(self) -> None:
        try:
            SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
            temp = SETTINGS_FILE.with_suffix(".tmp")
            temp.write_text(json.dumps(self._settings, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(SETTINGS_FILE)
        except OSError:
            pass

    def _restore_window(self) -> None:
        if self._settings.get("layout_version") == 2:
            width = max(820, self._safe_int(self._settings.get("window_width"), 980))
            height = max(560, self._safe_int(self._settings.get("window_height"), 660))
        else:
            width, height = 980, 660
        screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
        width = min(width, int(screen_w * 0.94))
        height = min(height, int(screen_h * 0.92))
        x = max((screen_w - width) // 2, 0)
        y = max((screen_h - height) // 3, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _on_close(self) -> None:
        if self._running and not messagebox.askyesno(
            "任务仍在运行", "关闭窗口会请求取消任务。确定关闭吗？", parent=self
        ):
            return
        self._closing = True
        self._detect_revision += 1
        self._cancel_event.set()
        self._settings.update(
            {
                "layout_version": 2,
                "output_dir": self._out_var.get().strip(),
                "blender_path": self._blend_var.get().strip(),
                "window_width": self.winfo_width(),
                "window_height": self.winfo_height(),
            }
        )
        self._save_settings()
        if self._worker and self._worker.is_alive():
            self._progress_var.set("正在停止任务并关闭")
            for widget in self._inputs:
                widget.configure(state=DISABLED)
            self._run_btn.configure(state=DISABLED)
            self._cancel_btn.configure(state=DISABLED)
            self.after(100, self._finish_close_when_idle)
        else:
            self.destroy()

    def _finish_close_when_idle(self) -> None:
        if self._worker and self._worker.is_alive():
            self.after(100, self._finish_close_when_idle)
            return
        self.destroy()


def launch() -> None:
    ReviewToolApp().mainloop()


if __name__ == "__main__":
    launch()
