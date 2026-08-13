"""通用工具：CSV 解析、字节大小格式化、模型/Blender/HDR 路径定位。"""

from __future__ import annotations

import csv
import os
import re
import shutil
import sys
from pathlib import Path


TEXTURE_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff",
    ".exr", ".webp", ".bmp", ".dds", ".ktx", ".ktx2",
})

NON_TEXTURE_SUFFIXES = frozenset({
    ".fbx", ".glb", ".gltf", ".obj", ".blend",
    ".csv", ".json", ".xlsx", ".txt", ".hdr", ".pdf",
})

SKIP_DIRS = frozenset({"thumbnails", ".git", "__pycache__"})

HDR_NAME = "aristea_wreck_puresky_1k.hdr"

_AFFIRMATIVE = frozenset({"是", "yes", "true", "1", "有", "开启", "含", "包含"})


def tool_dir() -> Path:
    """工具根目录：源码模式为仓库目录，frozen（PyInstaller）模式为 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    kb = n / 1024
    if kb < 1024:
        return f"{kb:.1f} KB"
    return f"{kb / 1024:.2f} MB"


def parse_basic_csv(path: Path) -> dict[str, str]:
    """读取 *_BasicInformation.csv，跳过表头行，返回字段字典。"""
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    out: dict[str, str] = {}
    for i, row in enumerate(csv.reader(raw.splitlines())):
        if i == 0 or len(row) < 2:
            continue
        key, value = row[0].strip(), row[1].strip()
        if key:
            out[key] = value
    return out


def is_affirmative(value: str) -> bool:
    return (value or "").strip().lower() in _AFFIRMATIVE


def normalize_animation_type(raw: str) -> str:
    s = (raw or "").strip().replace("｜", "|")
    if not s or s == "无":
        return "无"
    has_bone = "骨骼" in s
    has_shape = "形态" in s
    if has_bone and has_shape:
        return "骨骼动画、形态键动画"
    if has_bone:
        return "骨骼动画"
    if has_shape:
        return "形态键动画"
    return "无"


def skeleton_animation(info: dict[str, str]) -> tuple[str, str, str]:
    """从基础信息中提取 (骨骼, 动画, 动画类型) 三列。"""
    skel = "是" if is_affirmative(info.get("是否绑定骨骼", "")) else "否"
    anim = "是" if is_affirmative(info.get("是否包含动画", "")) else "否"
    return skel, anim, normalize_animation_type(info.get("动画类型", ""))


def texture_size_summary(csv_path: Path) -> str:
    """扫描 CSV 文本中形如 1024x1024 的尺寸串，去重后给出摘要。"""
    raw = csv_path.read_text(encoding="utf-8-sig", errors="replace")
    sizes = [f"{m.group(1)}x{m.group(2)}" for m in re.finditer(r"(\d+)\s*[x×]\s*(\d+)", raw)]
    if not sizes:
        return ""
    uniq = sorted(set(sizes), key=lambda s: (int(s.split("x")[0]), int(s.split("x")[1])))
    head = ", ".join(uniq[:8])
    return head + (f" …(共{len(uniq)}种)" if len(uniq) > 8 else "")


def sum_loose_texture_bytes(folder: Path) -> int:
    """统计资产目录中散贴图文件体积之和（不含 glb/fbx 内嵌字节）。"""
    total = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath, name)
            suf = path.suffix.lower()
            if suf in NON_TEXTURE_SUFFIXES:
                continue
            if suf in TEXTURE_SUFFIXES:
                try:
                    total += path.stat().st_size
                except OSError:
                    pass
    return total


def find_model_files(folder: Path) -> tuple[Path | None, Path | None]:
    """在资产目录中查找 (fbx, glb)，同名文件优先。"""
    fbx = glb = fbx_named = glb_named = None
    stem = folder.name.lower()
    for p in folder.iterdir():
        if not p.is_file():
            continue
        suf = p.suffix.lower()
        if suf == ".fbx":
            fbx = fbx or p
            if p.stem.lower() == stem:
                fbx_named = p
        elif suf == ".glb":
            glb = glb or p
            if p.stem.lower() == stem:
                glb_named = p
    return (fbx_named or fbx), (glb_named or glb)


def find_render_model(folder: Path) -> Path | None:
    """选择用于渲染缩略图的最佳模型：优先 GLB（含嵌入贴图），否则 FBX。"""
    fbx, glb = find_model_files(folder)
    return glb or fbx


def desktop_dir() -> Path:
    if sys.platform == "win32":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(1024)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0, None, 0, buf) == 0:
                return Path(buf.value)
        except Exception:
            pass
    home_desk = Path.home() / "Desktop"
    return home_desk if home_desk.is_dir() else Path.home()


def find_all_blenders() -> list[Path]:
    """全方位搜索 blender.exe 候选；4.2 LTS > 其他 4.x > 未知 > 5.x（脚本针对 4.2 调优）。

    覆盖：环境变量 / PATH / 标准安装目录 / Steam / 注册表 /
    所有可用盘符根目录与用户常用目录下的 *blender* 文件夹（绿色版/便携版）。
    """
    found: list[Path] = []
    seen: set[str] = set()

    def add(p: Path | None) -> None:
        if p is None:
            return
        try:
            if p.is_file() and p.suffix.lower() == ".exe":
                key = str(p.resolve()).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(p.resolve())
        except OSError:
            pass

    def add_dir_blender(d: Path) -> None:
        """若 d 是目录则尝试 d/blender.exe；若 d 本身是 blender.exe 则直接 add。"""
        try:
            if d.is_dir():
                add(d / "blender.exe")
            elif d.is_file():
                add(d)
        except OSError:
            pass

    _collect_from_env_vars(add_dir_blender)
    _collect_from_path(add)
    _collect_from_standard_installs(add_dir_blender)
    _collect_from_registry(add)
    _collect_from_user_dirs_and_drives(add_dir_blender)

    return sorted(found, key=_blender_priority)


def _blender_priority(p: Path) -> tuple[int, str]:
    s = str(p).lower().replace("/", "\\")
    if "blender 4.2" in s or "\\4.2\\" in s or "blender-4.2" in s or "-4.2." in s:
        return (0, s)
    if "blender 4." in s or "blender-4." in s or "-4." in s:
        return (1, s)
    if "blender 5" in s or "blender-5" in s or "-5." in s or "blender 6" in s:
        return (3, s)
    return (2, s)


def _collect_from_env_vars(add_dir_blender) -> None:
    for env in ("BLENDER", "BLENDER_PATH", "BLENDER_HOME"):
        val = os.environ.get(env)
        if not val:
            continue
        add_dir_blender(Path(val.strip().strip('"')))


def _collect_from_path(add) -> None:
    which = shutil.which("blender")
    if which:
        add(Path(which))


def _collect_from_standard_installs(add_dir_blender) -> None:
    bases: list[Path] = []
    for env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        v = os.environ.get(env)
        if v:
            bases.append(Path(v))

    parent_dirs: list[Path] = []
    for base in bases:
        parent_dirs.extend([
            base / "Blender Foundation",
            base / "Programs" / "Blender Foundation",
            base / "Programs",
            base / "Steam" / "steamapps" / "common" / "Blender",
        ])

    for parent in parent_dirs:
        try:
            if not parent.is_dir():
                continue
        except OSError:
            continue
        # 顶层就是 blender.exe（如 Steam 路径）
        add_dir_blender(parent)
        for child in _safe_iterdir(parent):
            if "blender" in child.name.lower():
                add_dir_blender(child)


def _collect_from_registry(add) -> None:
    if sys.platform != "win32":
        return
    try:
        import winreg
    except ImportError:
        return

    subkeys = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\blender.exe",
        r"SOFTWARE\Classes\blendfile\shell\open\command",
        r"SOFTWARE\BlenderFoundation\Blender",
    )
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for subkey in subkeys:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    val, _ = winreg.QueryValueEx(key, "")
            except OSError:
                continue
            if not val:
                continue
            # shell\open\command 形如:  "C:\path\blender.exe" "%1"
            text = str(val).strip().strip('"')
            if text.lower().endswith('" "%1'):
                text = text[: -len('" "%1')]
            if '"' in text:
                text = text.split('"', 1)[0]
            add(Path(text))


def _collect_from_user_dirs_and_drives(add_dir_blender) -> None:
    scan_roots: list[Path] = []

    if sys.platform == "win32":
        # 所有存在的盘符根目录
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZAB":
            d = Path(f"{letter}:\\")
            try:
                if d.exists():
                    scan_roots.append(d)
            except OSError:
                continue

    # 用户常用目录
    for env in ("USERPROFILE", "PUBLIC"):
        v = os.environ.get(env)
        if not v:
            continue
        home = Path(v)
        scan_roots.extend([home, home / "Desktop", home / "Downloads", home / "Documents"])

    for root in scan_roots:
        for child in _safe_iterdir(root):
            try:
                if "blender" not in child.name.lower() or not child.is_dir():
                    continue
            except OSError:
                continue
            # 第 1 层：child/blender.exe（绿色版常见结构）
            add_dir_blender(child)
            # 第 2 层：child/<sub>/blender.exe（含版本号子目录的结构）
            for sub in _safe_iterdir(child):
                try:
                    if sub.is_dir():
                        add_dir_blender(sub)
                except OSError:
                    continue


def _safe_iterdir(p: Path):
    try:
        yield from p.iterdir()
    except (PermissionError, OSError):
        return


def find_blender_exe() -> Path | None:
    cands = find_all_blenders()
    return cands[0] if cands else None


def resolve_hdr(tool_dir: Path) -> Path | None:
    """返回可用的环境 HDR 文件；未找到时返回 None。

    查找顺序：工具目录 assets/hdri/ → 工具目录根 → frozen 模式的内置副本。
    前两者允许用户在 exe 旁放置自定义 HDR 覆盖内置。
    """
    candidates = [
        tool_dir / "assets" / "hdri" / HDR_NAME,
        tool_dir / HDR_NAME,
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / HDR_NAME)
    for p in candidates:
        if p.is_file():
            return p
    return None
