from .render import outputs,verify_outputs
NAMES=('packet.json','observations.csv','findings.csv','report.html','manifest.json')
def compile_dir(source,policy,out):
    files=outputs(source.read_bytes(),policy.read_bytes());out.mkdir(parents=True,exist_ok=True)
    for k,v in files.items():(out/k).write_bytes(v)
def verify_dir(source,policy,out):
    verify_outputs(source.read_bytes(),policy.read_bytes(),{k:(out/k).read_bytes() for k in NAMES})
