import argparse,json,sys
from pathlib import Path
from .gate import EvidenceError,evaluate,markdown,verify
def read(p):return json.loads(Path(p).read_text())
def main(argv=None):
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True);c=sp.add_parser("compile");c.add_argument("--packet",required=True);c.add_argument("--evaluated-at",required=True);c.add_argument("--json-out");c.add_argument("--markdown-out");v=sp.add_parser("verify");v.add_argument("--packet",required=True);v.add_argument("--evaluated-at",required=True);v.add_argument("--receipt",required=True);a=ap.parse_args(argv)
 try:
  p=read(a.packet)
  if set(p)!={"policy","events"}:raise EvidenceError("packet keys")
  if a.cmd=="compile":
   r=evaluate(p["events"],p["policy"],evaluated_at=a.evaluated_at);s=json.dumps(r,sort_keys=True,separators=(",",":"))+"\n";(Path(a.json_out).write_text(s) if a.json_out else sys.stdout.write(s));a.markdown_out and Path(a.markdown_out).write_text(markdown(r));return 0 if r["status"]=="PASS" else 2
  ok=verify(p["events"],p["policy"],evaluated_at=a.evaluated_at,receipt=read(a.receipt));print("VALID" if ok else "INVALID",file=sys.stdout if ok else sys.stderr);return 0 if ok else 2
 except (OSError,ValueError,EvidenceError) as e:print(f"ERROR: {e}",file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
