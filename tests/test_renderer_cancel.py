from __future__ import annotations

import subprocess
import unittest
from unittest.mock import Mock, patch

import renderer


class RendererCancellationTests(unittest.TestCase):
    def test_cancel_terminates_running_process(self) -> None:
        process = Mock()
        process.communicate.side_effect = [
            subprocess.TimeoutExpired(["blender"], 0.25),
            ("out", "err"),
        ]
        process.returncode = -15

        with patch.object(renderer.subprocess, "Popen", return_value=process):
            result = renderer._run_process(
                ["blender"], is_cancelled=lambda: True, timeout_seconds=30
            )

        process.terminate.assert_called_once()
        self.assertEqual(result, (-15, "out", "err", "用户取消了渲染"))


if __name__ == "__main__":
    unittest.main()
