"""The pages are on the site theme: template.html loads /theme.css and /theme.js (served by the site repo),
carries the shared header and skip link, and uses none of the colors and fonts from before the theme.
The same rule is checked in the site repo by tools/check_theme.py."""
import re
import unittest
from pathlib import Path

TEMPLATE = (Path(__file__).resolve().parent.parent / "template.html").read_text(encoding="utf-8")
RETIRED = ["#161a1f", "#1b2026", "#303741", "#262c34", "#ebe8e1", "#aeb3b9", "#8f969f", "#9cc0dc", "156,192,220",
           "Source Serif"]


class Theme(unittest.TestCase):
    def test_loads_theme(self):
        self.assertRegex(TEMPLATE, r'<link rel="stylesheet" href="/theme\.css">')
        self.assertRegex(TEMPLATE, r'<script src="/theme\.js" defer></script>')
        # the theme comes before the page's own styles, so the page can only adjust layout
        self.assertLess(TEMPLATE.index('href="/theme.css"'), TEMPLATE.index("<style>"))

    def test_header_and_skip_link(self):
        self.assertRegex(TEMPLATE, r'<header class="dw-site">')
        self.assertIn('class="dw-skip"', TEMPLATE)

    def test_no_retired_values(self):
        low = TEMPLATE.lower().replace(" ", "")
        for v in RETIRED:
            self.assertNotIn(v.lower().replace(" ", ""), low, v)

    def test_colors_read_theme_tokens(self):
        root = re.search(r":root \{(.*?)\n\}", TEMPLATE, re.S).group(1)
        for name in ("--bg", "--surface", "--border", "--text", "--accent", "--good", "--warn", "--crit", "--font", "--head"):
            self.assertRegex(root, rf"{name}: var\(--[a-z0-9-]+, ", name)


if __name__ == "__main__":
    unittest.main()
