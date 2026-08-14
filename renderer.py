"""调度 Blender 子进程渲染单个模型为 PNG 缩略图。"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from PIL import Image


BG_COLOR = "#252525"
WIDTH = 256
MIN_HEIGHT = 210
MAX_HEIGHT = 347
PADDING = 0.08
SAMPLES = 64
HDR_STRENGTH = 1.0
RENDER_TIMEOUT_SECONDS = 30 * 60

ENGINE_ORDER: tuple[str, ...] = ("BLENDER_EEVEE_NEXT", "CYCLES")
_SCRIPT_PATH = Path(__file__).with_name("blender_script.py")


def _script_path() -> Path:
    """blender_script.py 的磁盘位置：frozen 模式从 PyInstaller 解压目录取。"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "blender_script.py"
    return _SCRIPT_PATH


def render_one(
    model: Path,
    output: Path,
    blender: Path,
    *,
    hdr: Path | None = None,
    engines: tuple[str, ...] = ENGINE_ORDER,
    is_cancelled: Callable[[], bool] | None = None,
    timeout_seconds: float = RENDER_TIMEOUT_SECONDS,
) -> tuple[bool, str]:
    """渲染单个模型；按 engines 顺序依次尝试，首个成功即返回。"""
    is_cancelled = is_cancelled or (lambda: False)
    output.parent.mkdir(parents=True, exist_ok=True)
    logs: list[str] = []
    for engine in engines:
        if output.exists():
            try:
                output.unlink()
            except OSError:
                pass
        cmd = _build_cmd(model, output, blender, engine, hdr)
        if is_cancelled():
            return False, "[cancelled] 用户取消了渲染"
        returncode, stdout, stderr, stop_reason = _run_process(
            cmd, is_cancelled=is_cancelled, timeout_seconds=timeout_seconds
        )
        stdout, stderr = stdout.strip(), stderr.strip()
        if stdout:
            logs.append(f"[engine={engine}]\n{stdout}")
        if stderr:
            logs.append(f"[engine={engine} stderr]\n{stderr}")
        if stop_reason:
            logs.append(f"[engine={engine}] {stop_reason}")
            return False, "\n\n".join(logs)
        if returncode == 0 and output.exists():
            try:
                _composite_background(output, BG_COLOR)
            except Exception as exc:
                logs.append(f"[composite_failed] {exc}")
                return False, "\n\n".join(logs)
            return True, "\n\n".join(logs)
    return False, "\n\n".join(logs)


def _run_process(
    cmd: list[str],
    *,
    is_cancelled: Callable[[], bool],
    timeout_seconds: float,
) -> tuple[int, str, str, str | None]:
    """运行 Blender，并在取消或超时时可靠终止子进程。"""
    process = subprocess.Popen(cmd, **_subprocess_kwargs())
    started = time.monotonic()
    while True:
        try:
            stdout, stderr = process.communicate(timeout=0.25)
            return process.returncode, stdout or "", stderr or "", None
        except subprocess.TimeoutExpired:
            if is_cancelled():
                stdout, stderr = _terminate_process(process)
                return process.returncode or -1, stdout, stderr, "用户取消了渲染"
            if time.monotonic() - started >= timeout_seconds:
                stdout, stderr = _terminate_process(process)
                return process.returncode or -1, stdout, stderr, f"渲染超过 {timeout_seconds:g} 秒，已终止"


def _terminate_process(process: subprocess.Popen) -> tuple[str, str]:
    process.terminate()
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
    return stdout or "", stderr or ""


def _build_cmd(model: Path, output: Path, blender: Path, engine: str, hdr: Path | None) -> list[str]:
    cmd = [
        str(blender), "--background", "--factory-startup",
        "--python", str(_script_path()), "--",
        "--input", str(model),
        "--output", str(output),
        "--width", str(WIDTH),
        "--min-height", str(MIN_HEIGHT),
        "--max-height", str(MAX_HEIGHT),
        "--padding", str(PADDING),
        "--bg-color", BG_COLOR,
        "--hdr-strength", str(HDR_STRENGTH),
        "--engine", engine,
        "--samples", str(SAMPLES),
    ]
    if hdr and hdr.exists():
        cmd.extend(["--hdr", str(hdr)])
    return cmd


def _subprocess_kwargs() -> dict:
    kwargs: dict = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def _composite_background(image_path: Path, bg_color: str) -> None:
    """将透明背景的 PNG 与纯色背景合成。"""
    rgb = _hex_to_rgb(bg_color)
    with Image.open(image_path).convert("RGBA") as rendered:
        bg = Image.new("RGBA", rendered.size, rgb + (255,))
        Image.alpha_composite(bg, rendered).save(image_path)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    s = value.strip().lstrip("#")
    if len(s) != 6:
        raise ValueError(f"无效的颜色: {value}")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
