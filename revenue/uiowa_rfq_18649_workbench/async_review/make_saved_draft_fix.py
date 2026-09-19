"""Derive a saved-draft-only fix from the verified composed app; no remote writes."""
from pathlib import Path
import hashlib,difflib
root=Path(__file__).resolve().parent
p=root/'composed_app.js'; before=p.read_text(); b=p.read_bytes()
sha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
if sha!='808a89401a7978c4897feb351aee231adcba8dd6': raise ValueError('Wrong patch base')
a='    const contents = await file.text();\n'
if before.count(a)!=1: raise ValueError('Missing or ambiguous saved-file read seam')
patched=before.replace(a,'    const bytes = await file.arrayBuffer();\n')
a='    const restored = HandoffImport.parseDraft(contents, report);'
b='''    // File.text() substitutes malformed UTF-8. Decode bytes strictly before
    // replacing any notes so corrupt input cannot become a successful restore.
    let contents;
    try { contents = new TextDecoder("utf-8", { fatal: true }).decode(bytes); }
    catch { throw new Error("Saved draft is not valid UTF-8. Existing notes were not changed."); }
    const restored = HandoffImport.parseDraft(contents, report);'''
if patched.count(a)!=1: raise ValueError('Missing or ambiguous restore validation seam')
patched=patched.replace(a,b)
(root/'fixed_app.js').write_text(patched)
patch=''.join(difflib.unified_diff(before.splitlines(keepends=True),patched.splitlines(keepends=True),
 fromfile='a/revenue/uiowa_rfq_18649_workbench/app.js',tofile='b/revenue/uiowa_rfq_18649_workbench/app.js'))
(root/'saved_draft_utf8.patch').write_text(patch)
print(patch)
