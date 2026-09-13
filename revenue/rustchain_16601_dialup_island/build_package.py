#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import subprocess,hashlib,re
R=Path(__file__).resolve().parent; V=R/'visuals'; A=R/'voiceover'; V.mkdir(parents=True,exist_ok=True); A.mkdir(exist_ok=True)
PIN='f01243a09810eb9b36013a6336b5b4ff6d444d50'; BASE=f'https://github.com/Scottcjn/rustchain-dialup/blob/{PIN}'
S=[
('00-cold-open','Cold open','Picture a 1997 internet service provider rebuilt on a Raspberry Pi-class Linux box — not as a museum piece, but as a bridge for hardware that modern networks forgot. RustChain Dial-Up is an early-build project that combines a dial-up network-access server, a BBS, and a split mining gateway. The target clients are machines like a 486, a classic Mac, or a Dreamcast-class setup that can speak through a serial or USB modem. The important word is early-build: the repository has working software pieces and a documented live-node gateway test, but the full vintage-machine-over-modem mining loop is still a roadmap milestone.'),
('01-the-island','The dial-up island','The network shape is deliberately old-school. A client modem talks across an analog plant — a line simulator on the bench, or later a phone-style bridge — to a server modem attached to the Linux NAS. mgetty owns the modem, answers the call, and hands a PPP session to pppd. The project plans terminal BBS and PPP service on separate lines first, because automatic one-line PPP detection is brittle if a login banner or terminal-first client speaks before PPP. On the PPP side, the caller gets an isolated IP path rather than joining the lab LAN directly. That is the first architectural idea: recreate a tiny ISP, but keep the vintage guest boxed into its own island.'),
('02-split-miner','Why the miner is split','The second idea is the split miner. The old computer is not asked to become a modern TLS client. Instead, the vintage side is responsible for the trust-sensitive work: gather hardware evidence, construct the challenge response, and sign locally with Ed25519. The Pi-side gateway is transport. It fetches the node challenge, relays the signed attestation over HTTPS, and returns the result. The gateway documentation is explicit that it holds no signing key. That boundary matters because moving the private key or fabricating hardware evidence on the Pi would destroy the proof-of-antiquity story. The gateway can deny service, but by design it should not be able to mint a fake vintage miner.'),
('03-what-is-real','What is actually working today','Here is the line between shipped evidence and ambition. The repository contains rcgateway, its line protocol, and tests. Its README records a June second live-node validation where a modern vintage-client stand-in sent through the gateway to the real RustChain attestation endpoint and received an accepted result. The gateway also implements a miner allowlist, challenge-nonce binding, a per-miner rate limit, and optional local signature preflight. But the same source marks the reference portable C vintage client as not done. The project roadmap also leaves the modem-pair PPP acceptance test, a real vintage target, and a big-endian round trip open. So: the modern transport half has a documented acceptance; the actual antique-hardware dial-up loop is the work still being built.'),
('04-slow-link-security','Making 9600 baud usable — and safe','Dial-up changes the engineering constraints. The architecture document estimates 9600 baud at roughly 960 bytes per second and calls a default 1500-byte PPP frame about a second and a half of serialization time. The proposed fix is a 576-byte MTU and MRU, with tests down to 296, plus a TCP MSS clamp so remote servers do not push oversized segments into the slow link. Security is equally concrete: the PPP subnet is meant to be separate, default-deny toward private lab ranges, block peer-to-peer movement, and allow only the narrow services the caller actually needs — such as DNS, WAN egress, the BBS, and the one local RustChain gateway. Old hardware is interesting; an untrusted dial-in host is still untrusted.'),
('05-not-proven','What this video is not claiming','The repository itself labels the project an early build in its LAN-island phase. It does not prove that a Dreamcast is already mining RTC over a live phone call. It does not prove that a 386 has completed the full signed attestation path over a modem pair. And its VoIP-to-analog bridge is a later phase, with the documentation warning that 56k modem modes do not survive ordinary VoIP and that even V.34 should be treated cautiously. Those gaps are not embarrassing footnotes; they are written as explicit bounties and acceptance tests. D6 asks for the portable C evidence-and-sign client on a real vintage OS. D7 asks for a big-endian signature round trip. D10 asks for a real modem data call through the VoIP bridge.'),
('06-why-it-matters','Why build it','That makes RustChain Dial-Up more interesting than a retro-networking stunt. It is a preservation experiment with a hard systems boundary: keep identity and evidence on the old silicon, move only modern transport chores to the gateway, and prove each physical link instead of pretending a diagram is a demo. The architecture document even publishes example RIP-200 multipliers — G4 at two point five, retro x86 at one point four, POWER8 at one point five, and modern x86 at zero point eight — to explain why antique machines are not merely tolerated in this design. The next milestone is not “believe the pitch.” It is “produce the modem logs, the signed attestation, the node acceptance, and the isolation proof.” If that evidence lands, a machine that belongs in a computer-history exhibit can become a first-class participant in a modern attestation network — over a literal phone-style link.')]
(R/'script.md').write_text('# RustChain Dial-Up: Mining From an Island the Internet Forgot\n\n**Package:** Scottcjn/rustchain-bounties #16601 · Type A full production kit  \n**Author credit:** Bryce / @woahwhattheheck  \n**Source pin:** `Scottcjn/rustchain-dialup@'+PIN+'`  \n**Editorial rule:** shipped evidence and roadmap claims are explicitly separated.\n\n'+'\n\n'.join('## '+t+'\n\n'+x for _,t,x in S)+'\n')
for slug,_,text in S:(A/f'{slug}.txt').write_text(text+'\n')
(R/'README.md').write_text(f'''# RustChain Dial-Up — “Island the Internet Forgot” Type-A kit

Publication-ready Type-A package for [rustchain-bounties#16601](https://github.com/Scottcjn/rustchain-bounties/issues/16601).

**Pitch:** a source-pinned explainer of the modem-era network island and split-miner architecture that distinguishes the live-validated modern gateway from still-open physical modem + vintage-client milestones.

Contents: `script.md`, seven MP3s in `voiceover/`, nine 1920×1080 originals in `visuals/`, three 1280×720 thumbnails, `assembly.md`, `metadata.md`, `SOURCES.md`, `RIGHTS.md`, and `verify_package.py`.

Pinned upstream: `Scottcjn/rustchain-dialup@{PIN}`. The package states exactly one live acceptance result: the gateway README's documented modern-client → `rcgateway` → real-node `/attest/submit` acceptance. It does **not** claim a completed vintage client, physical 9600-baud modem-pair attestation, Dreamcast mining session, or VoIP modem relay.

Narration: eSpeak (`en-us`, 150 wpm), encoded as mono 24 kbps / 16 kHz MP3 with ffmpeg.
''')
(R/'RIGHTS.md').write_text('''# Rights and generation notes

- Script: original for this package, authored for @woahwhattheheck from cited public sources.
- Narration: generated with eSpeak from `voiceover/*.txt`.
- Visuals/thumbnails: generated from scratch with Pillow; no stock images, logos, screenshots, or third-party artwork.
- Elyan Labs may publish under rustchain-bounties#16601 with permanent author attribution.
''')
(R/'SOURCES.md').write_text(f'''# Sources and claim map

All technical claims are pinned to `Scottcjn/rustchain-dialup@{PIN}`.

- **Cold open / status:** {BASE}/README.md — project definition, target clients, `Status: early build — LAN-island phase`, roadmap.
- **Dial-up island / separate lines / isolation:** {BASE}/docs/ARCHITECTURE.md — big picture, component responsibilities, two-mode decision, security & isolation.
- **Split miner / trust boundary:** {BASE}/docs/MINER_GATEWAY.md — split, security invariant, phasing, Phase-4 acceptance test.
- **Gateway live-node acceptance + guards:** {BASE}/gateway/README.md — `Status / TODO` and `What it does / doesn't do`.
- **Slow-link numbers:** {BASE}/docs/ARCHITECTURE.md — 9600 baud ≈ 960 B/s, 1500-byte frame ≈ 1.5 s, MTU/MRU 576, test to 296, MSS clamp.
- **Open D6/D7/D10 proofs:** {BASE}/BOUNTIES.md.
- **VoIP/56k caveat:** {BASE}/README.md and {BASE}/docs/ARCHITECTURE.md.
- **Example RIP-200 multipliers:** {BASE}/docs/ARCHITECTURE.md — G4 2.5×, retro x86 1.4×, POWER8 1.5×, modern x86 0.8×.
- **Package contract / 40 RTC Type-A reward:** https://github.com/Scottcjn/rustchain-bounties/issues/16601
''')
(R/'metadata.md').write_text('''# Publication metadata

## Primary title
**RustChain Dial-Up: Mining From an Island the Internet Forgot**

## Alternate titles
1. **Can a 486 Mine Over Dial-Up? Inside RustChain’s Vintage Network Island**
2. **A Tiny ISP for Old Computers: RustChain’s Split-Miner Experiment**

## Description
RustChain Dial-Up is rebuilding a tiny modem-era ISP around vintage machines, a Linux network-access server, and a split attestation gateway. This evidence-first package separates what the public repository proves from the physical modem/vintage-hardware milestones that remain open.

Source: https://github.com/Scottcjn/rustchain-dialup

## Chapters
00:00 An ISP for forgotten hardware · 00:45 The dial-up island · 01:33 Why the miner is split · 02:23 What works today · 03:17 9600 baud and isolation · 04:16 What is not proven · 05:07 Why it matters

## Tags
RustChain, dial-up, retrocomputing, vintage computing, PPP, BBS, Raspberry Pi, modem, 486, Dreamcast, Ed25519, systems engineering, proof of antiquity
''')
(R/'assembly.md').write_text('''# Assembly map

Use the seven section MP3s sequentially. Visuals are 1920×1080 stills designed for slow pans/push-ins.

| Section | Primary visual | Secondary |
|---|---|---|
| Cold open | `visuals/01-title.png` | `02-topology.png` |
| Dial-up island | `02-topology.png` | `03-two-lines-first.png` |
| Split miner | `04-split-miner.png` | hold on trust labels |
| What is real | `05-evidence-vs-roadmap.png` | reveal accepted then open |
| Slow link + security | `06-slow-link.png` | `07-isolation.png` |
| Not proven | `08-roadmap.png` | D6 → D7 → D10 |
| Why it matters | `09-proof-not-pitch.png` | return to title |

Do not add footage implying a physical modem call or vintage attestation unless the publisher separately captures that proof. Thumbnails are publication options, not evidence.
''')
try:
 B=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',72); M=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',38); N=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',28); T=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',64)
except:B=M=N=T=ImageFont.load_default()
def wrap(d,s,f,w):
 out=[]; cur=''
 for word in s.split():
  q=(cur+' '+word).strip()
  if d.textbbox((0,0),q,font=f)[2]<=w:cur=q
  else:
   if cur:out.append(cur)
   cur=word
 if cur:out.append(cur)
 return out
def frame(name,title,sub,bullets):
 im=Image.new('RGB',(1920,1080),(11,15,22));d=ImageDraw.Draw(im);a=(90,220,170);d.rectangle((80,75,1840,1005),outline=a,width=4);d.text((125,115),title,font=B,fill=(235,240,245));y=240
 for q in wrap(d,sub,M,1600):d.text((130,y),q,font=M,fill=a);y+=50
 y+=35
 for b in bullets:
  ls=wrap(d,b,N,1450);d.ellipse((145,y+9,165,y+29),fill=a)
  for i,q in enumerate(ls):d.text((195,y+i*42),q,font=N,fill=(210,218,225))
  y+=42*len(ls)+28
 d.text((130,945),'source pin: rustchain-dialup@f01243a…',font=N,fill=(120,130,140));im.save(V/name,optimize=True)
F=[('01-title.png','RUSTCHAIN DIAL-UP','Mining from an island the Internet forgot',['A tiny ISP + BBS + split attestation gateway for vintage hardware','Evidence-first: shipped software ≠ completed physical modem milestone']),('02-topology.png','THE DIAL-UP ISLAND','Vintage client → analog plant → Linux NAS',['Client modem: 486 / classic Mac / Dreamcast-class setup','Server: modem + mgetty + pppd on a Pi-class Linux box','PPP guests reach a narrow path, not the whole lab']),('03-two-lines-first.png','SEPARATE LINES FIRST','Prove terminal/BBS and PPP independently before multiplexing',['PPP auto-detection is brittle if plaintext appears before LCP','One-number AutoPPP is Phase 5, after both modes work alone']),('04-split-miner.png','KEEP TRUST ON OLD SILICON','Vintage client signs. Gateway transports.',['Vintage side: hardware evidence + challenge response + Ed25519','Gateway: nonce fetch + TLS/HTTP relay + result return','Gateway holds no signing key']),('05-evidence-vs-roadmap.png','EVIDENCE vs ROADMAP','One line is green; the physical loop is still open',['DOCUMENTED: modern client → rcgateway → real node → accepted','OPEN: portable C client (D6)','OPEN: big-endian round trip (D7)','OPEN: modem-pair Phase-4 acceptance']),('06-slow-link.png','9600 BAUD CHANGES EVERYTHING','Serialization latency becomes architecture',['~960 bytes/sec in the architecture estimate','1500-byte PPP frame: ~1.5 seconds','MTU/MRU 576 + MSS clamp; test down to 296']),('07-isolation.png','DIAL-IN = UNTRUSTED GUEST','Retro does not mean trusted',['Dedicated PPP subnet','Default-deny toward private lab ranges','Block PPP↔PPP lateral movement','Narrow DNS / WAN / BBS / gateway paths']),('08-roadmap.png','THE NEXT PROOFS','The gaps are published as bounties',['D6 — portable C client on a real vintage OS','D7 — big-endian signature round trip','D10 — real modem call through VoIP↔analog']),('09-proof-not-pitch.png','PROOF, NOT PITCH','The finish line is physical evidence',['modem logs','signed attestation','node acceptance','correct antiquity result','firewall isolation proof'])]
for x in F:frame(*x)
def thumb(path,l1,l2,a):
 im=Image.new('RGB',(1280,720),(8,12,18));d=ImageDraw.Draw(im);d.rectangle((35,35,1245,685),outline=a,width=6);d.text((70,80),'RUSTCHAIN DIAL-UP',font=M,fill=a);y=190
 for z in (l1,l2):
  for q in wrap(d,z,T,1120):d.text((70,y),q,font=T,fill=(240,244,247));y+=78
 d.line((120,570,1160,570),fill=a,width=5)
 for x,z in ((150,'MODEM'),(555,'PPP'),(930,'GATEWAY')):d.rectangle((x,525,x+190,620),outline=a,width=4);d.text((x+15,550),z,font=N,fill=(220,228,235))
 im.save(R/path,optimize=True)
thumb('thumbnail.png','CAN A 486 MINE','OVER DIAL-UP?',(90,220,170));thumb('thumbnail-alt-1.png','THE INTERNET','FORGOT THIS ISLAND',(220,180,90));thumb('thumbnail-alt-2.png','OLD SILICON,','MODERN ATTESTATION',(130,160,240))
rows=[];total=0
for txt in sorted(A.glob('*.txt')):
 b=txt.with_suffix('');w=Path(str(b)+'.tmp.wav');m=Path(str(b)+'.mp3');subprocess.run(['espeak','-v','en-us','-s','150','-w',str(w),'-f',str(txt)],check=True);subprocess.run(['ffmpeg','-loglevel','error','-y','-i',str(w),'-codec:a','libmp3lame','-b:a','24k','-ar','16000','-ac','1',str(m)],check=True);w.unlink();d=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(m)],text=True));total+=d;rows.append((m.name,d,m.stat().st_size,hashlib.sha256(m.read_bytes()).hexdigest()))
engine=subprocess.check_output(['espeak','--version'],text=True,stderr=subprocess.STDOUT).splitlines()[0].strip()
(A/'manifest.md').write_text('# Voiceover manifest\n\nEngine: **'+engine+'**, `en-us`, 150 wpm; mono MP3 24 kbps / 16 kHz.\n\n| file | seconds | bytes | sha256 |\n|---|---:|---:|---|\n'+'\n'.join(f'| `{n}` | {d:.2f} | {z} | `{h}` |' for n,d,z,h in rows)+f'\n\n**Total narration:** {total:.2f} seconds ({total/60:.2f} minutes).\n')
verify='''from pathlib import Path\nfrom PIL import Image\nimport subprocess,re,sys\nr=Path(__file__).resolve().parent; e=[]\nfor p in ['script.md','assembly.md','metadata.md','SOURCES.md','RIGHTS.md','thumbnail.png','thumbnail-alt-1.png','thumbnail-alt-2.png']:\n if not (r/p).is_file():e.append('missing '+p)\nfor p in ['thumbnail.png','thumbnail-alt-1.png','thumbnail-alt-2.png']:\n if (r/p).is_file() and Image.open(r/p).size!=(1280,720):e.append(p+' dimensions')\nvs=list((r/'visuals').glob('*.png'));ms=list((r/'voiceover').glob('*.mp3'));dur=0\nfor p in vs:\n if Image.open(p).size!=(1920,1080):e.append(p.name+' dimensions')\nfor p in ms:dur+=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(p)],text=True))\nw=len(re.findall(r"\\b[\\w’'-]+\\b",(r/'script.md').read_text()))\nif len(vs)!=9:e.append(f'visuals={len(vs)}')\nif len(ms)!=7:e.append(f'mp3s={len(ms)}')\nif not 180<=dur<=480:e.append(f'duration={dur}')\nif w<450:e.append(f'words={w}')\nprint(f'visuals={len(vs)} thumbnails=3 mp3s={len(ms)} duration_s={dur:.2f} script_words={w}')\nif e:print('FAIL',*e,sep='\\n- ');sys.exit(1)\nprint('PASS')\n''';(R/'verify_package.py').write_text(verify)
(R/'VERIFY.md').write_text(f'''# Validation receipt

Run `python3 verify_package.py` with Pillow + ffprobe. Build uses eSpeak + ffmpeg.

Builder result: 9 original 1920×1080 PNGs, 3 original 1280×720 thumbnails, 7 MP3 narration files, source map pinned to `{PIN}`, and explicit no-physical-modem-completion claim.
''')
subprocess.run(['python3',str(R/'verify_package.py')],check=True)
print('PACKAGE_BUILD_PASS')
