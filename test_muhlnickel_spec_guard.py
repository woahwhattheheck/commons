import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import muhlnickel_spec_guard as guard


def blob_sha(data: bytes) -> str:
    head = ("blob %d\0" % len(data)).encode("ascii")
    return hashlib.sha1(head + data).hexdigest()


class MuhlnickelSpecGuardTests(unittest.TestCase):
    def init_repo(self, files=None, approvals=()):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "guard@test"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "guard"], cwd=root, check=True)
        policy = root / "ground" / "muhlnickel-observe-tools.json"
        policy.parent.mkdir(parents=True)
        policy.write_text(
            json.dumps({"owner_observation_tool_blobs": list(approvals)}, indent=2) + "\n",
            encoding="utf-8",
        )
        for name, body in (files or {"seed.txt": "seed\n"}).items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "trusted base"], cwd=root, check=True)
        return td, root

    def errors(self, root):
        with mock.patch.object(guard, "ROOT", root):
            return guard.violations("HEAD")

    def test_unrelated_commons_numpy_and_submit_are_outside_scope(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "commons_stats.py").write_text(
            "import numpy as np\n\ndef submit(form):\n    return np.mean(form)\n",
            encoding="utf-8",
        )
        self.assertEqual(self.errors(root), [])

    def test_offline_whitebox_tensor_scraper_and_requirements_are_allowed(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "requirements.txt").write_text("numpy>=1.24\ntorch>=2.1\n", encoding="utf-8")
        (root / "tensor_scraper.py").write_text(
            "import numpy as np\nfrom pathlib import Path\n"
            "data = np.memmap(Path('ordinary.gguf'), mode='r', dtype='uint8')\n"
            "print(float(data.mean()))\n",
            encoding="utf-8",
        )
        self.assertEqual(self.errors(root), [])

    def test_renamed_runtime_numpy_is_rejected_by_behavior(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "totally_ordinary.py").write_text(
            "import numpy as np\nfrom pfc_fire import submit\n"
            "def go(x):\n    submit(np.asarray(x))\n",
            encoding="utf-8",
        )
        errors = self.errors(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("host tensor/model/gate computation", errors[0])

    def test_renaming_python_extension_does_not_bypass_behavior(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "ordinary.data").write_text(
            "import numpy as np\nfrom pfc_fire import submit\n"
            "def go(x):\n    submit(np.asarray(x))\n",
            encoding="utf-8",
        )
        self.assertTrue(self.errors(root))

    def test_runtime_torch_forward_is_rejected(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "worker.py").write_text(
            "import torch\nfrom pfc_fire import submit\n"
            "def forward(x):\n    return torch.matmul(x, x)\n"
            "submit(forward(torch.ones(2)))\n",
            encoding="utf-8",
        )
        self.assertTrue(self.errors(root))

    def test_import_indirection_cannot_hide_runtime_compute(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "math_helper.py").write_text(
            "import numpy as np\ndef compute(x):\n    return np.dot(x, x)\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "math_helper.py"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "existing helper"], cwd=root, check=True)
        (root / "new_driver.py").write_text(
            "from pfc_fire import submit\nfrom math_helper import compute\nsubmit(compute([1]))\n",
            encoding="utf-8",
        )
        self.assertTrue(self.errors(root))

    def test_dynamic_launch_from_runtime_is_rejected(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "launcher.py").write_text(
            "import subprocess\nfrom pfc_fire import submit\n"
            "submit(1)\nsubprocess.run(['python3', 'worker.py'])\n",
            encoding="utf-8",
        )
        self.assertIn("dynamic host code", self.errors(root)[0])

    def test_structural_gate_walk_is_rejected_after_rename(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "holiday_calendar.py").write_text(
            "SOURCE = 'runtime.mno'\n"
            "def update(gate_records, state):\n"
            "    for gate in gate_records:\n"
            "        state[gate[2]] = state[gate[0]] ^ state[gate[1]]\n",
            encoding="utf-8",
        )
        self.assertIn("structurally walks gates", self.errors(root)[0])

    def test_exact_approved_tool_blob_may_move_but_modified_copy_may_not(self):
        tool = b"from pfc_fire import submit\nimport numpy as np\nsubmit(np.ones(1))\n"
        approved = blob_sha(tool)
        td, root = self.init_repo(
            {"host/owner_scope.py": tool.decode("utf-8")},
            approvals=(approved,),
        )
        self.addCleanup(td.cleanup)
        (root / "renamed").mkdir()
        subprocess.run(
            ["git", "mv", "host/owner_scope.py", "renamed/anything.py"],
            cwd=root,
            check=True,
        )
        self.assertEqual(self.errors(root), [])
        (root / "renamed/anything.py").write_text(tool.decode("utf-8") + "# changed\n", encoding="utf-8")
        errors = self.errors(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("blob identity no longer matches", errors[0])

    def test_same_change_cannot_self_grant_a_new_tool(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        body = b"from pfc_fire import submit\nimport numpy as np\nsubmit(np.ones(1))\n"
        (root / "new_scope.py").write_bytes(body)
        policy = root / "ground" / "muhlnickel-observe-tools.json"
        policy.write_text(
            json.dumps({"owner_observation_tool_blobs": [blob_sha(body)]}) + "\n",
            encoding="utf-8",
        )
        self.assertTrue(self.errors(root))

    def test_unchanged_legacy_violation_does_not_block_unrelated_fix(self):
        bad = (
            "import numpy as np\nfrom pfc_fire import submit\n"
            "submit(np.ones(1))\n"
        )
        td, root = self.init_repo({"legacy.py": bad, "commons.py": "VALUE = 1\n"})
        self.addCleanup(td.cleanup)
        (root / "commons.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.assertEqual(self.errors(root), [])

    def test_new_violation_in_legacy_file_is_rejected(self):
        td, root = self.init_repo({"legacy.py": "VALUE = 1\n"})
        self.addCleanup(td.cleanup)
        (root / "legacy.py").write_text(
            "import numpy as np\nfrom pfc_fire import submit\nsubmit(np.ones(1))\n",
            encoding="utf-8",
        )
        self.assertTrue(self.errors(root))

    def test_existing_bad_runtime_is_refused_when_selected_for_direct_execution(self):
        body = "import numpy as np\nfrom pfc_fire import submit\nsubmit(np.ones(1))\n"
        td, root = self.init_repo({"already_here.py": body})
        self.addCleanup(td.cleanup)
        with mock.patch.object(guard, "ROOT", root):
            self.assertTrue(guard.executable_violations("already_here.py", "HEAD"))

    def test_existing_offline_tensor_script_may_be_selected_for_direct_execution(self):
        body = "import numpy as np\nprint(np.asarray([1]).mean())\n"
        td, root = self.init_repo({"offline.py": body})
        self.addCleanup(td.cleanup)
        with mock.patch.object(guard, "ROOT", root):
            self.assertEqual(guard.executable_violations("offline.py", "HEAD"), [])

    def test_host_pfc_import_of_activated_titan_circuit_is_rejected(self):
        """Coil-batch regression: a host pfc_* twin that closes over titan_circuit compute fails."""
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "titan_circuit.py").write_text(
            "import numpy as np\n"
            "from pfc_fire import submit\n"
            "def ripple(cir, bits):\n"
            "    return np.dot(bits, bits)\n"
            "submit(ripple(None, [1]))\n",
            encoding="utf-8",
        )
        (root / "host").mkdir()
        (root / "host/pfc_miner.py").write_text(
            "import titan_circuit as TC\n"
            "print('pfc runtime')\n"
            "TC.ripple({'n_in': 1}, [1])\n",
            encoding="utf-8",
        )
        errors = self.errors(root)
        coil = [e for e in errors if "host/pfc_miner.py" in e]
        self.assertEqual(len(coil), 1)
        self.assertIn("host tensor/model/gate computation", coil[0])

    def test_host_pfc_routing_without_compute_closure_is_allowed(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "titan_circuit.py").write_text(
            "import numpy as np\nfrom pfc_fire import submit\n"
            "def ripple(cir, bits):\n    return np.dot(bits, bits)\n",
            encoding="utf-8",
        )
        (root / "pfc_forward.py").write_text(
            "import numpy as np\nfrom pfc_fire import submit\n"
            "def forward(x):\n    return np.matmul(x, x)\n",
            encoding="utf-8",
        )
        (root / "host").mkdir()
        (root / "host/pfc_miner.py").write_text(
            "import json, os\n"
            "REG = 'titan_circuits.json'\n"
            "def main():\n"
            "    print('pfc runtime address-only')\n"
            "    if os.path.exists(REG):\n"
            "        print(json.load(open(REG)).get('pfc_mine'))\n"
            "if __name__ == '__main__':\n"
            "    main()\n",
            encoding="utf-8",
        )
        self.assertEqual(self.errors(root), [])

    def test_live_coil_host_files_do_not_close_over_activated_compute(self):
        """The five coil host twins must stay routing-only even if poisoned compute modules sit nearby."""
        here = Path(__file__).resolve().parent
        names = [
            "pfc_miner.py",
            "pfc_miter.py",
            "pfc_mmu.py",
            "pfc_model.py",
            "pfc_modelbuild.py",
        ]
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "titan_circuit.py").write_text(
            "import numpy as np\nfrom pfc_fire import submit\n"
            "def ripple(c, b):\n    return np.dot(b, b)\n",
            encoding="utf-8",
        )
        (root / "pfc_forward.py").write_text(
            "import numpy as np\nfrom pfc_fire import submit\n"
            "def forward(x):\n    return np.matmul(x, x)\n",
            encoding="utf-8",
        )
        (root / "pfc_llama_harness.py").write_text(
            "import numpy as np\nfrom pfc_fire import submit\n"
            "def ripple(c, b):\n    return np.dot(b, b)\n",
            encoding="utf-8",
        )
        (root / "host").mkdir()
        for name in names:
            src = here / "host" / name
            self.assertTrue(src.is_file(), name)
            (root / "host" / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        errors = self.errors(root)
        coil = [e for e in errors if any(name in e for name in names)]
        self.assertEqual(coil, [])

    def test_null_byte_corpus_is_not_python_and_does_not_crash_the_scan(self):
        """Packed .mno bytes decode as UTF-8 but ast.parse raises ValueError on NUL."""
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "payload.mno").write_bytes(
            b"MUHLRD01\x08\x00\x00\x00H\x00\x00\x00import numpy\nfrom pfc_fire import submit\n"
        )
        self.assertFalse(
            guard.is_python(Path("payload.mno"), (root / "payload.mno").read_bytes())
        )
        self.assertEqual(self.errors(root), [])

    def test_renamed_runtime_without_nulls_is_still_rejected(self):
        td, root = self.init_repo()
        self.addCleanup(td.cleanup)
        (root / "ordinary.mno").write_text(
            "import numpy as np\nfrom pfc_fire import submit\n"
            "def go(x):\n    submit(np.asarray(x))\n",
            encoding="utf-8",
        )
        errors = self.errors(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("host tensor/model/gate computation", errors[0])


if __name__ == "__main__":
    unittest.main()
