# HARNESS_TEST

**When:** 2026-08-15. cwd `LocalDeviceAgent`. CLI `host/muhl_cli.py`. Spec `SUPER_HARNESS.md`.
**Buttons:** slots · surface · copy · die. No wipe. No train. No inject.

Output := **ran y / slot_0_size 8192 / ok**

---

## slots

```
python host/muhl_cli.py slots
```

exit 0

```
MUHL CLI  slots
  dir    C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS
  n      1
  C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_0.mno  8192 B
  training_started  NO
  (button dies)
```

---

## surface slot_0 (ans region, documented mouth ans@5378+1283)

```
python host/muhl_cli.py surface slot_0
```

exit 0

```
MUHL CLI  surface
  slot   C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_0.mno
  addr   6661  n=1
  hex    08
  byte   8
  training_started  NO
  (button dies)
```

---

## copy slot_1 (new slot)

```
python host/muhl_cli.py copy slot_1
```

exit 0

```
MUHL CLI  copy
  germ   C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\SEED0.mno
  slot   C:\Users\lucys\Desktop\MUHLNICKEL_DISTRO\CONTAINERS\slot_1.mno
  bytes  8192
  training_started  NO
  (button dies)
```

---

## die

```
python host/muhl_cli.py die
```

exit 0

```
MUHL CLI  die
  training_started  NO
  (button dies)
```

---

## Σ

| verb | ran | exit | note |
|---|---|---|---|
| slots | y | 0 | slot_0.mno 8192 B |
| surface | y | 0 | addr 6661 hex 08 byte 8 |
| copy | y | 0 | slot_1.mno 8192 B |
| die | y | 0 | dies |

training_started NO on every button.
