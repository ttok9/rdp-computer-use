import re
import unittest
from pathlib import Path


class DistributionHygieneTests(unittest.TestCase):
    def test_no_internal_markers_or_token_shapes(self) -> None:
        root = Path(__file__).parents[1]
        internal_markers = ["auto" + "ever", "10." + "208.", "10." + "204."]
        token_pattern = re.compile(r"eyJ[A-Za-z0-9_-]{40,}\.[A-Za-z0-9_-]{20,}")
        local_path_patterns = [
            re.compile(r"/Use" + r"rs/" + r"[^/]+/"),
            re.compile(r"[A-Za-z]:\\" + r"Use" + r"rs\\[^\\]+\\"),
        ]
        for path in root.rglob("*"):
            if not path.is_file() or any(part in {".git", ".venv", "__pycache__", "dist", "build"} or part.endswith(".egg-info") for part in path.parts):
                continue
            if path.suffix.lower() not in {".py", ".md", ".toml", ".json", ".yml", ".yaml", ".example", ".html", ".svg", ""}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for marker in internal_markers:
                self.assertNotIn(marker, text.lower(), f"internal marker found in {path}")
            self.assertIsNone(token_pattern.search(text), f"token-like value found in {path}")
            for pattern in local_path_patterns:
                self.assertIsNone(pattern.search(text), f"local user path found in {path}")


if __name__ == "__main__":
    unittest.main()
