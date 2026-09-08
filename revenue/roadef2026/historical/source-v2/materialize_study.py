#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Materialize exact historical V2 replay, freeze, inputs, timings, and summary."""
from __future__ import annotations
import argparse,base64,hashlib,io,json,tarfile
from pathlib import Path,PurePosixPath

ARCHIVE_SHA256='9057f4ce667108881e8613be7131a1ee08cf06bb60ae437f6203a09183cc69fb'
FILES={
 'replay_three_arms.py':(4487,'62531c78c04655d519f238ed58f895edd20ee9c9f862cdf28147a0b11760d122'),
 'run_three_arms.py':(6000,'96f807aff9435a7fb62ae32f558aa77701128b90a1f1e73f09269dac93520196'),
 'PREDECLARED.json':(766,'5227a8652d236ceb16fa36ef30d66cb5df1211a07df4f3eb17eca54e39b3983b'),
 'PUBLIC-THREE-ARM-FREEZE.json':(2224,'af5b05f2b8568133c2acad52d0cff558bef3c9ed96785627f897be092d596507'),
 'PUBLIC-INPUTS.json':(7459,'242f79aa0fc0967bb761131e8bc44d940702e26f1090ff726f9ef3448852ca92'),
 'RESULTS.md':(3328,'380b2a988572a8e79ec89e4aa99a9a83d7f9f8b9241f22d7a8fe4a4fc215656d'),
 'RESULTS.json':(18048,'5e2a70235d55b9ca448e8ffdddfc601d2386cba15936e448ac456293885c23ee'),
 'public-three.log':(26285,'107db7487f4cd8fa43685188af6713cc9d666775e651f6e621d92bba35062761'),
}
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def main()->int:
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--encoded',type=Path,default=Path(__file__).with_name('study-v2.tar.gz.b64'))
 p.add_argument('--output',type=Path,required=True)
 args=p.parse_args()
 try: archive=base64.b64decode(args.encoded.read_text(encoding='ascii'),validate=False)
 except (OSError,ValueError) as exc:p.error(str(exc))
 if sha(archive)!=ARCHIVE_SHA256:p.error('study archive digest mismatch')
 if args.output.exists():p.error('output directory already exists')
 rows=[]
 try:
  with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tf:
   members=tf.getmembers()
   if len(members)!=len(FILES) or {m.name for m in members}!=set(FILES):p.error('unexpected study member set')
   args.output.mkdir(parents=True)
   for member in members:
    pure=PurePosixPath(member.name)
    if pure.is_absolute() or '..' in pure.parts or not member.isfile():p.error('unsafe study member')
    stream=tf.extractfile(member)
    if stream is None:p.error(f'cannot read {member.name}')
    data=stream.read();size,digest=FILES[member.name]
    if len(data)!=size or sha(data)!=digest:p.error(f'identity mismatch: {member.name}')
    (args.output/member.name).write_bytes(data)
    rows.append({'path':member.name,'bytes':len(data),'sha256':sha(data)})
 except (OSError,tarfile.TarError) as exc:p.error(str(exc))
 print(json.dumps({'schema':'roadef.historical.temporal-v2.study-materialization.v1','status':'PASS',
  'archive_sha256':ARCHIVE_SHA256,'files':sorted(rows,key=lambda x:x['path']),'compiled':False,
  'solver_runs':0,'checker_runs':0,'historical_execution_only':True},indent=2,sort_keys=True))
 return 0
if __name__=='__main__':raise SystemExit(main())
