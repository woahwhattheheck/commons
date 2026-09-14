import hashlib
import json
from pathlib import Path
import unittest


class ManifestTests(unittest.TestCase):
    def test_carrier_manifest_matches_exact_bytes_and_inventory(self):
        project = Path(__file__).resolve().parents[1]
        repo = project.parents[1]
        manifest_path = project / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "quietops.carrier-manifest/v1")

        actual = {
            p.relative_to(project).as_posix(): p
            for p in project.rglob("*")
            if p.is_file() and p.name != "MANIFEST.json" and "__pycache__" not in p.parts
        }
        listed = {row["path"]: row for row in manifest["files"]}
        self.assertEqual(set(actual), set(listed))
        for path, p in actual.items():
            data = p.read_bytes()
            self.assertEqual(listed[path]["bytes"], len(data), path)
            self.assertEqual(listed[path]["sha256"], hashlib.sha256(data).hexdigest(), path)

        wf = manifest["ci_workflow"]
        wp = repo / wf["path"]
        data = wp.read_bytes()
        self.assertEqual(wf["bytes"], len(data))
        self.assertEqual(wf["sha256"], hashlib.sha256(data).hexdigest())


if __name__ == "__main__": unittest.main()
