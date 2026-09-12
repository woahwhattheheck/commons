import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "extract_episode.py"

def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

class ReplayLossAutopsyTests(unittest.TestCase):
    def fixture(self, root: Path, *, ambiguous=False):
        actions = root / "farmer_actions.csv"
        markets = root / "market_orders.csv"
        meta = root / "matches_meta.csv"
        if ambiguous:
            write(actions, "episode_id,match_id,player,step,action_verb,target,qty\nE1,E1,0,718,DROP,,\n")
        else:
            write(actions,
                  "episode_id,player,step,action_verb,target,qty\n"
                  "E1,0,700,HARVEST,WHEAT,2\n"
                  "E1,1,701,CARE,GOOSE,\n"
                  "E1,0,718,DROP,,\n"
                  "E2,0,718,PASS,,\n")
        write(markets,
              "episode_id,player,step,order_verb,item,qty\n"
              "E1,0,700,SELL,WHEAT,2\n"
              "E1,1,702,BUY_ANIMAL,GOOSE,1\n"
              "E1,1,718,SELL,EGG,bad\n"
              "E2,0,718,SELL,WHEAT,1\n")
        write(meta,
              "episode_id,team0,team1,score0,score1,winner\n"
              "E1,Titan,Rival,61766,62770,1\n"
              "E2,Titan,Other,1,0,0\n")
        return actions, markets, meta

    def run_tool(self, root: Path, *extra):
        actions, markets, meta = self.fixture(root)
        cmd = [
            sys.executable, str(TOOL),
            "--farmer-actions", str(actions),
            "--market-orders", str(markets),
            "--matches-meta", str(meta),
            "--episode", "E1",
            *extra,
        ]
        return subprocess.run(cmd, text=True, capture_output=True, check=False)

    def test_deterministic_episode_summary_and_tail(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = self.run_tool(root, "--tail-callbacks", "24")
            second = self.run_tool(root, "--tail-callbacks", "24")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            data = json.loads(first.stdout)
            self.assertEqual(data["episode"], "E1")
            self.assertEqual(data["coverage"]["farmer_action_rows"], 3)
            self.assertEqual(data["coverage"]["market_order_rows"], 3)
            self.assertEqual(data["coverage"]["meta_rows"], 1)
            self.assertEqual(data["coverage"]["bad_qty_rows"]["market_orders"], 1)
            self.assertEqual(data["tail"]["start_step"], 695)
            self.assertTrue(all(e["step"] >= 695 for e in data["tail"]["events"]))
            sells = [r for r in data["market_summary"] if r["verb"] == "SELL" and r["item"] == "WHEAT"]
            self.assertEqual(sells[0]["explicit_qty_sum"], 2)
            self.assertEqual(data["meta_rows_exact"][0]["score0"], "61766")

    def test_output_file_exactly_matches_stdout_shape(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out.json"
            result = self.run_tool(root, "--output", str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            payload = json.loads(out.read_text())
            self.assertEqual(payload["schema"], "titan.v4.replay-loss-autopsy.v1")

    def test_absent_episode_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            actions, markets, meta = self.fixture(root)
            result = subprocess.run([
                sys.executable, str(TOOL),
                "--farmer-actions", str(actions),
                "--market-orders", str(markets),
                "--matches-meta", str(meta),
                "--episode", "MISSING",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("not found", result.stderr)

    def test_ambiguous_aliases_fail_without_explicit_map(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            actions, markets, meta = self.fixture(root, ambiguous=True)
            result = subprocess.run([
                sys.executable, str(TOOL),
                "--farmer-actions", str(actions),
                "--market-orders", str(markets),
                "--matches-meta", str(meta),
                "--episode", "E1",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("ambiguous episode", result.stderr)

    def test_explicit_schema_map_resolves_ambiguity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            actions, markets, meta = self.fixture(root, ambiguous=True)
            schema = root / "schema.json"
            schema.write_text(json.dumps({
                "farmer_actions": {"episode": "episode_id"},
                "market_orders": {"episode": "episode_id"},
                "matches_meta": {"episode": "episode_id"},
            }), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(TOOL),
                "--farmer-actions", str(actions),
                "--market-orders", str(markets),
                "--matches-meta", str(meta),
                "--episode", "E1",
                "--schema-json", str(schema),
            ], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["coverage"]["farmer_action_rows"], 1)

    def test_malformed_csv_row_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            actions, markets, meta = self.fixture(root)
            actions.write_text(
                "episode_id,player,step,action_verb,target,qty\n"
                "E1,0,700,HARVEST,WHEAT\n",
                encoding="utf-8",
            )
            result = subprocess.run([
                sys.executable, str(TOOL),
                "--farmer-actions", str(actions),
                "--market-orders", str(markets),
                "--matches-meta", str(meta),
                "--episode", "E1",
            ], text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertIn("malformed CSV row", result.stderr)

    def test_invalid_tail_and_turns_per_day_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bad_tail = self.run_tool(root, "--tail-callbacks", "-1")
            self.assertEqual(bad_tail.returncode, 2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bad_day = self.run_tool(root, "--turns-per-day", "0")
            self.assertEqual(bad_day.returncode, 2)

if __name__ == "__main__":
    unittest.main()
