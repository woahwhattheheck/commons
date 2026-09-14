from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .core import canonical_json, compile_manifest, sha256_bytes, verify_local_evidence


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def build_demo_html(packet: dict[str, Any], *, base_dir: Path | None = None) -> str:
    """Build a deterministic, dependency-free proof storyboard.

    This surface is intentionally presentation-only: it never generates media and
    never promotes generated slots to factual evidence. Local evidence is verified
    first when ``base_dir`` is supplied.
    """
    if base_dir is not None:
        verify_local_evidence(packet, base_dir)
    manifest = compile_manifest(packet)
    project = manifest["project"]
    fact_count = sum(1 for shot in manifest["shots"] if shot["type"] == "factual")
    gen_count = sum(1 for shot in manifest["shots"] if shot["type"] == "generated")

    cards: list[str] = []
    for shot in manifest["shots"]:
        if shot["type"] == "factual":
            evidence_rows = []
            for ev in shot["evidence"]:
                locator = ev.get("url") or ev.get("path") or "descriptor-only"
                evidence_rows.append(
                    '<li><span class="ev-id">{}</span><span>{}</span><code>{}</code></li>'.format(
                        _esc(ev["id"]), _esc(locator), _esc(ev["sha256"][:16] + "…")
                    )
                )
            cards.append(
                '<article class="shot factual" data-shot="{}">'
                '<div class="badge">EVIDENCE-BOUND FACT</div>'
                '<h2>{}</h2>'
                '<p class="caption">{}</p>'
                '<ul class="evidence">{}</ul>'
                '</article>'.format(
                    _esc(shot["id"]), _esc(shot["claim_id"]), _esc(shot["caption"]), "".join(evidence_rows)
                )
            )
        else:
            cards.append(
                '<article class="shot generated" data-shot="{}">'
                '<div class="badge">GENERATIVE CONNECTIVE · HOLD_PROVIDER</div>'
                '<h2>{}</h2>'
                '<p class="caption">{}</p>'
                '<p class="prompt"><strong>Prompt:</strong> {}</p>'
                '<p class="boundary">Cannot satisfy factual claims.</p>'
                '</article>'.format(
                    _esc(shot["id"]), _esc(shot["id"]), _esc(shot["purpose"]), _esc(shot["prompt"])
                )
            )

    manifest_json = json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False)
    receipt = sha256_bytes(canonical_json(manifest))
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProofCut · {_esc(project['name'])}</title>
<style>
:root{{--bg:#090b10;--panel:#111722;--ink:#eef4ff;--muted:#9faec2;--line:#273246;--fact:#8be9c1;--gen:#d7b4ff;--hold:#ffd479}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}}
main{{max-width:980px;margin:auto;padding:44px 20px 72px}} header{{padding:28px;border:1px solid var(--line);background:linear-gradient(135deg,#111722,#0d1119);border-radius:20px}}
h1{{font-size:clamp(32px,6vw,70px);line-height:.95;margin:8px 0 18px;letter-spacing:-.055em}} .kicker{{color:var(--fact);font-weight:800;letter-spacing:.12em;font-size:12px}}
.lede{{max-width:760px;color:var(--muted);font-size:18px}} .stats{{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}} .stat{{border:1px solid var(--line);padding:8px 11px;border-radius:999px}}
.grid{{display:grid;gap:14px;margin-top:18px}} .shot{{border:1px solid var(--line);background:var(--panel);padding:20px;border-radius:16px}} .shot h2{{margin:8px 0;font-size:20px}}
.badge{{font-size:11px;font-weight:900;letter-spacing:.08em}} .factual .badge{{color:var(--fact)}} .generated .badge{{color:var(--gen)}} .caption,.prompt{{color:var(--muted)}}
.evidence{{list-style:none;padding:0;margin:16px 0 0;display:grid;gap:8px}} .evidence li{{display:grid;grid-template-columns:minmax(120px,.5fr) 1fr auto;gap:12px;padding:10px;border-top:1px solid var(--line);align-items:center}}
.ev-id{{color:var(--fact)}} code{{color:#cdd8e8;font-size:12px}} .boundary{{color:var(--hold);font-weight:800}} details{{margin-top:18px;border:1px solid var(--line);border-radius:14px;padding:14px}} pre{{white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);font-size:12px}}
footer{{color:var(--muted);margin-top:24px;font-size:12px}} a{{color:inherit}} @media(max-width:700px){{.evidence li{{grid-template-columns:1fr}}}}
</style>
</head>
<body><main>
<header>
<div class="kicker">PROOFCUT · EVIDENCE BEFORE CINEMA</div>
<h1>{_esc(project['name'])}</h1>
<p class="lede">A product-demo storyboard where factual frames are content-addressed and generative media is visibly constrained to connective shots.</p>
<div class="stats"><span class="stat">{fact_count} factual</span><span class="stat">{gen_count} generative</span><span class="stat">manifest {_esc(manifest['manifest_sha256'][:12])}…</span></div>
</header>
<section class="grid">{''.join(cards)}</section>
<details><summary>Canonical manifest</summary><pre>{_esc(manifest_json)}</pre></details>
<footer>Manifest receipt: <code>{_esc(receipt)}</code> · Source packet: <code>{_esc(manifest['source_packet_sha256'])}</code></footer>
</main></body></html>'''
