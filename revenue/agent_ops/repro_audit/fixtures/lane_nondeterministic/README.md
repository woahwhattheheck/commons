# Fixture lane: NOT deterministic (SYNTHETIC)

A miniature lane carrying the three failure classes this audit exists to catch:
a wall-clock stamp, its own absolute path, and unsorted set iteration. It is
deliberately broken so the audit can be shown going red.

```bash
python3 gen.py
```
