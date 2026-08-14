from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import builder


class BuildProgressTests(unittest.TestCase):
    def test_cancel_before_first_asset_does_not_render_or_write(self) -> None:
        root = Path("C:/fixture/root")
        folder = root / "AssetA"
        output = Path("C:/fixture/output")
        with (
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.exists", return_value=False),
            patch.object(builder, "_gather_candidates", return_value=[folder]),
            patch.object(builder, "_deduplicate", return_value=[folder]),
            patch.object(builder, "_row_from_folder") as row_from_folder,
            patch.object(builder, "_write_workbook") as write_workbook,
        ):
            with self.assertRaises(builder.BuildCancelled):
                builder.build_report(
                    [root],
                    output,
                    output.parent / "blender.exe",
                    is_cancelled=lambda: True,
                    log=lambda _message: None,
                )
        write_workbook.assert_not_called()
        row_from_folder.assert_not_called()

    def test_progress_reports_asset_then_excel(self) -> None:
        root = Path("C:/fixture/root")
        folder = root / "AssetA"
        output = Path("C:/fixture/output")
        events: list[tuple[int, int, str]] = []
        row = builder._Row("AssetA", "", "", "", "", "", "", "", "", "", "", "", None)
        with (
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.exists", return_value=False),
            patch.object(builder, "_gather_candidates", return_value=[folder]),
            patch.object(builder, "_deduplicate", return_value=[folder]),
            patch.object(builder, "_row_from_folder", return_value=row),
            patch.object(builder, "_write_workbook"),
        ):
            builder.build_report(
                [root],
                output,
                output.parent / "blender.exe",
                progress=lambda done, total, label: events.append((done, total, label)),
                log=lambda _message: None,
            )
        self.assertEqual(events[0], (0, 1, "AssetA"))
        self.assertEqual(events[-1], (1, 1, "正在写入 Excel · 暂不可取消"))


if __name__ == "__main__":
    unittest.main()
