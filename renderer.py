"""调度 Blender 子进程渲染单个模型为 PNG 缩略图。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image


BG_COLOR = "#252525"
WIDTH = 256
MIN_HEIGHT = 210
MAX_HEIGHT = 347
PADDING = 0.08
SAMPLES = 64
HDR_STRENGTH = 1.0

ENGINE_ORDER: tuple[str, ...] = ("BLENDER_EEVEE_NEXT", "CYCLES")
_SCRIPT_PATH = Path(__file__).with_name("blender_script.py")


def render_one(
    model: Path,
    output: Path,
    blender: Path,
    *,
    hdr: Path | None = None,
    engines: tuple[str, ...] = ENGINE_ORDER,
) -> tuple[bool, str]:
    """渲染单个模型；按 engines 顺序依次尝试，首个成功即返回。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    logs: list[str] = []
    for engine in engines:
        if output.exists():
            try:
                output.unlink()
            except OSError:
                pass
        cmd = _build_cmd(model, output, blender, engine, hdr)
        result = subprocess.run(cmd, **_subprocess_kwargs())
        stdout, stderr = (result.stdout or "").strip(), (result.stderr or "").strip()
        if stdout:
            logs.append(f"[engine={engine}]\n{stdout}")
        if stderr:
            logs.append(f"[engine={engine} stderr]\n{stderr}")
        if result.returncode == 0 and output.exists():
            try:
                _composite_background(output, BG_COLOR)
            except Exception as exc:
                logs.append(f"[composite_failed] {exc}")
                return False, "\n\n".join(logs)
            return True, "\n\n".join(logs)
    return False, "\n\n".join(logs)


def _build_cmd(model: Path, output: Path, blender: Path, engine: str, hdr: Path | None) -> list[str]:
    cmd = [
        str(blender), "--background", "--factory-startup",
        "--python", str(_SCRIPT_PATH), "--",
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
        "capture_output": True,
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
