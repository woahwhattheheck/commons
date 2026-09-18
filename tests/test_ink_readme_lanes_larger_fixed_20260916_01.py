from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "ink-readme-lanes-larger-fixed-20260916-01"
FILES = {
    "README.md": "./",
    "android/README.md": "../",
    "host/titan_hands/README.md": "../../",
    "ground/PLAY.md": "../",
    "ground/PICK.md": "../",
}


class T(unittest.TestCase):
    def test_readme_lanes_larger_fixed(self):
        for rel, prefix in FILES.items():
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn("Live cash", text)
                self.assertIn("Larger fixed engagements", text)
                self.assertIn(f"{prefix}diagnostic.html", text)
                self.assertIn(f"{prefix}commercial.html", text)
                self.assertIn("$12,000", text)
                self.assertIn("$30,000", text)
                self.assertNotIn("buy.stripe.com", text)
                self.assertNotIn("https://buy.stripe.com/", text)

    def test_receipt(self):
        text = (ROOT / "p" / f"{CLAIM}.md").read_text(encoding="utf-8")
        self.assertIn(CLAIM, text)
        self.assertIn("Tip KEEP", text)
        self.assertIn("#8802", text)
        for rel in FILES:
            self.assertIn(rel, text)


if __name__ == "__main__":
    unittest.main()
