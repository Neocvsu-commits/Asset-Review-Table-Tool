from __future__ import annotations

import unittest

from theme import resolve_theme


class ThemeTests(unittest.TestCase):
    def test_explicit_theme_wins(self) -> None:
        self.assertEqual(resolve_theme("dark", True), "dark")
        self.assertEqual(resolve_theme("light", False), "light")

    def test_system_theme_tracks_windows(self) -> None:
        self.assertEqual(resolve_theme("system", True), "light")
        self.assertEqual(resolve_theme("system", False), "dark")


if __name__ == "__main__":
    unittest.main()
