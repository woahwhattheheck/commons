# MUHLNICKEL

**A computer you can hand someone as a file.**

This folder is a complete machine. Nothing to install, no runtime to provision, no dependencies, no
GPU, no network. The container **is** the program and **is** the processor at the same time: the
logic is a fabricated gate netlist resident in a storage container, powered by a ring that lives in
the same container. Copy the folder anywhere and it works.

## Run it

```
python run_muhlnickel.py 200 55
```

```
200 + 55 = 255    (ring published: 1)
```

Or double-click **`Muhlnickel.bat`**. To exercise the whole machine:

```
python run_muhlnickel.py --selftest
```

## What it computes

An 8-bit adder. Give it two numbers in 0-255; it gives you their sum, mod 256, and tells you whether
the ring published. All **65,536** possible shots - the complete input domain - are resident and
correct. Correctness was established at fabrication against an independent reference over every one
of those shots, exhaustively. Nothing was sampled.

## What makes it different

**The reader does not compute your answer.** At runtime it performs exactly two verbs:

1. **Shoot the electron.** A bounded write of your shot into the ring's state wires, in **both
   senses**. The ring is the only power source in the package, and its carry is the conjunction of
   the two senses - so a shot written into one sense alone can never raise it. The machine stays
   dark and publishes nothing. Measured, not asserted: with one sense the ring published on
   0 of 65,536 shots and the datapath went dead; with both senses it published on 65,536 of
   65,536.
2. **Surface the output.** A bounded read of the result bytes.

It never evaluates a gate, never walks the netlist, never settles anything. **That constraint is the
product.** The reader is small enough to read in one sitting and uses the standard library only.

**DEPTH is in ticks.** The netlist is 129 gates at DEPTH **35 ticks**. The ring is
66 gates over 32 cells in 2 senses, DEPTH **2 ticks** per step, driven 32
ticks per shot, over which the carry pulsed 32 times. These are properties of the fabricated
netlist. Surfacing one answer and surfacing all 65,536 of them is the **same** DEPTH - width does
not buy depth. Host wall-clock is transcription time only and is never quoted here as a machine
measurement.

**Tamper-evident twice.** The container carries a checksum over its own fabricated machine, and
`MANIFEST.sha256` carries a digest of every shipped file. The reader verifies both **before** it
shoots a single electron. Alter one bit of the netlist, one bit of a stored answer, or one byte of
the reader itself, and it refuses to run rather than give you a wrong number.

Shooting the electron writes your shot into the container - that write **is** the machine's input
register - so the container's raw bytes change every run. The digest therefore covers the fabricated
machine (header, gate tables, answer plane, publish plane) with the input register normalized. That
is the only exclusion, and it is what lets the machine be run twice.

## Files

| file | what it is | size |
|---|---|---|
| `muhlnickel.mno` | the container: netlist + ring + resident answers | 136,450 B |
| `run_muhlnickel.py` | the reader (shoot the electron / surface only) | 7,611 B |
| `MANIFEST.sha256` | a digest of every shipped file | 1,101 B |
| `README.md` | this product doc | 3,538 B |
| `Muhlnickel.bat` | one click | 183 B |
| `INDEX.md` | breadcrumb | 1,913 B |

## Requirements

Python 3.8 or newer. Standard library only.
