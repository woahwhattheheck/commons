import csv,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bias_discovery import analyze,load_scores
class BiasDiscoveryTests(unittest.TestCase):
    def test_ranks_nonfixed_numeric_candidate_and_excludes_svi(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); scores_path=root/"scores.csv"; strata_path=root/"strata.csv"
            with scores_path.open("w",newline="",encoding="utf-8") as h:
                w=csv.DictWriter(h,fieldnames=["GEOID","coverage_gap_score"]); w.writeheader(); [w.writerow({"GEOID":f"0401301{i:04d}","coverage_gap_score":i/11}) for i in range(12)]
            with strata_path.open("w",newline="",encoding="utf-8") as h:
                w=csv.DictWriter(h,fieldnames=["GEOID","broadband_metric","svi_score"]); w.writeheader(); [w.writerow({"GEOID":f"0401301{i:04d}","broadband_metric":i,"svi_score":i}) for i in range(12)]
            results=analyze(load_scores(scores_path),strata_path,min_rows=8,prefixes=("svi_",))
        self.assertEqual(results[0]["field"],"broadband_metric"); self.assertGreater(results[0]["signed_delta"],0); self.assertNotIn("svi_score",{x["field"] for x in results})
if __name__=="__main__": unittest.main()
