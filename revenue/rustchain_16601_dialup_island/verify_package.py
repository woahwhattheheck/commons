from pathlib import Path
from PIL import Image
import subprocess,re,sys
r=Path(__file__).resolve().parent; e=[]
for p in ['script.md','assembly.md','metadata.md','SOURCES.md','RIGHTS.md','thumbnail.png','thumbnail-alt-1.png','thumbnail-alt-2.png']:
 if not (r/p).is_file():e.append('missing '+p)
for p in ['thumbnail.png','thumbnail-alt-1.png','thumbnail-alt-2.png']:
 if (r/p).is_file() and Image.open(r/p).size!=(1280,720):e.append(p+' dimensions')
vs=list((r/'visuals').glob('*.png'));ms=list((r/'voiceover').glob('*.mp3'));dur=0
for p in vs:
 if Image.open(p).size!=(1920,1080):e.append(p.name+' dimensions')
for p in ms:dur+=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(p)],text=True))
w=len(re.findall(r"\b[\w’'-]+\b",(r/'script.md').read_text()))
if len(vs)!=9:e.append(f'visuals={len(vs)}')
if len(ms)!=7:e.append(f'mp3s={len(ms)}')
if not 180<=dur<=480:e.append(f'duration={dur}')
if w<450:e.append(f'words={w}')
print(f'visuals={len(vs)} thumbnails=3 mp3s={len(ms)} duration_s={dur:.2f} script_words={w}')
if e:print('FAIL',*e,sep='\n- ');sys.exit(1)
print('PASS')
