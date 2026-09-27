# Kaggriculture final challenger — September 27, 2026

Archive: `titan-v5-runtime-p05-weed-catchup.tar.gz`  
SHA-256: `e58785ab13d3e7d2d8ca0a03bc77f04ee54155ebd1f687ba1a1388dac31aece5`  
Size: 421,498 bytes; 94 regular members; root `main.py::agent`.

This is a candidate for one judged Kaggle upload before September 30, 23:59 UTC. It is the exact held WF1+C02 policy with two bounded changes: module-import startup prewarm in `main.py`, and P05 weed-queue catch-up that skips appending an authored PASS while same-day queue debt exists. The latter leaves non-PASS authored actions and empty-queue behavior unchanged. The archive and the receipt freeze these bytes; do not rebuild or substitute `exports/titan-current.tar.gz`.

A worker-thread official-engine first callback on the unmodified held package took 1.0193 seconds and returned fallback PASS with zero market orders. The prewarmed member took 0.3969 seconds and returned a real three-order action on the same observation. No broad paired panel or superiority claim is made for this archive; the submission is the judged evaluation requested by Bryce.

Existing V5 D2 submission `56220277` is the anchor. Historical second active submission was V3.1 `56220248`. Read back the current Kaggle submission list immediately before uploading; only the latest two count. If this order still holds, one upload of this candidate rotates out V3.1 and keeps D2. Upload the exact archive once, record the returned ID and validation status, and read back the final active pair. Do not upload the runtime-only parent.

Official CLI form:
```bash
kaggle competitions submit kaggriculture -f titan-v5-runtime-p05-weed-catchup.tar.gz -m "TITAN V5 runtime and weed-queue catch-up"
kaggle competitions submissions kaggriculture
```

The corresponding source is `runtime_main.py`; the router transform is already in `../p05_weed_queue_completion.py`. The receipt records both member hashes and the exact held parent.
