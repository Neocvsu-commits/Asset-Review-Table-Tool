#!/usr/bin/env python3
"""资产 Review 表格工具 — 统一入口。

无参数：启动 GUI；
--cli：命令行模式，按 --assets-root 与 --out-dir 生成表格。

示例：
    python main.py
    python main.py --cli --assets-root D:/AssetsA --assets-root D:/AssetsB \\
                   --out-dir D:/Review --blender "C:/.../blender.exe"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


__version__ = "1.1.0"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="资产 Review 表格工具")
    p.add_argument("--cli", action="store_true", help="命令行模式（不打开 GUI）")
    p.add_argument(
        "--assets-root", action="append", type=Path, dest="roots", metavar="DIR",
        help="资产根目录，可多次指定以合并多个根",
    )
    p.add_argument("--out-dir", type=Path, help="输出目录")
    p.add_argument("--blender", type=Path, help="blender.exe 路径（缺省时自动探测）")
    p.add_argument("--hdr", type=Path, help="可选 HDR 环境贴图（缺省时使用 assets/hdri/ 内置文件）")
    p.add_argument("--count", type=int, default=0, help="抽样 N 个资产（0 = 全部）")
    p.add_argument("--seed", type=int, default=20260512, help="抽样种子（仅在 --count > 0 时生效）")
    return p.parse_args()


def _run_cli(args: argparse.Namespace) -> int:
    from builder import build_report
    from utils import find_blender_exe, resolve_hdr, tool_dir

    if not args.roots or not args.out_dir:
        print("ERROR: --assets-root 与 --out-dir 为必填项。", file=sys.stderr)
        return 2

    blender = args.blender or find_blender_exe()
    if not blender:
        print("ERROR: 未在系统中找到 blender.exe，请用 --blender 指定路径。", file=sys.stderr)
        return 2
    if not blender.is_file():
        print(f"ERROR: --blender 指向的文件不存在: {blender}", file=sys.stderr)
        return 2

    hdr = args.hdr or resolve_hdr(tool_dir())
    try:
        build_report(
            roots=args.roots,
            out_dir=args.out_dir,
            blender=blender,
            hdr=hdr,
            limit=args.count or None,
            seed=args.seed,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    args = _parse_args()
    if args.cli:
        return _run_cli(args)
    from gui import launch
    launch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
