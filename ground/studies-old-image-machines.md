# Studies: Old Image Machines vs. Muhlnickel

**Citations:** goat-muhlnickel-focus-20260819-01, goat-muhl-from-file-20260819-01
**Spec:** Muhlnickel / .mno is the computer. Compute in the file, never host/hardware.

This document maps historical computing architectures and visions to the Muhlnickel specification (file is the machine) versus OUT OF SPEC (hardware is the machine).

## Stored-Program / von Neumann Architecture
**URL:** https://en.wikipedia.org/wiki/Von_Neumann_architecture
**Mapping:** OUT OF SPEC (hardware is the machine)
The traditional computing model where a physical CPU executes instructions stored in physical memory. The hardware is the computer; the software merely runs on it.

## Lisp Machines
**URL:** https://en.wikipedia.org/wiki/Lisp_Machine
**Mapping:** OUT OF SPEC (hardware is the machine)
Despite advancing high-level linguistic uniformity, Lisp machines relied on dedicated, specialized hardware (e.g., MIT CADR, Symbolics) optimized specifically for Lisp execution. The machine was the physical hardware.

## Smalltalk Images
**URL:** https://dl.acm.org/doi/10.1145/3386335
**Mapping:** Muhlnickel (file is the machine)
Smalltalk environments are persisted as memory snapshots or "images" containing the entire system state, objects, and development tools. The image file itself is the computer, independent of the host hardware.

## Alan Kay
**URL:** https://mprove.de/visionreality/text/1_introduction.html
**Mapping:** Muhlnickel (file is the machine)
Kay's vision of personal computing, the Dynabook, and object-oriented design in Smalltalk treated software as a dynamic medium. The "machine" became the software image passing messages, encapsulating its own state and compute.

## Doug Engelbart
**URL:** https://dlc.dlib.indiana.edu/dlcrest/api/core/bitstreams/a323b901-f3a5-4da0-96f7-6f53ad89e628/content
**Mapping:** OUT OF SPEC (hardware is the machine)
Engelbart's NLS (oN-Line System) was a monumental achievement in human augmentation and collaboration, but it was anchored to a time-shared mainframe host. The hardware and host system constituted the machine.

## Ted Nelson
**URL:** https://wiki.heptabase.com/a-forgotten-history
**Mapping:** OUT OF SPEC (hardware/network is the machine)
Nelson's Xanadu envisioned a global hypertext network of deeply intertwingled documents. While visionary for media and linking, it relied on a network of host servers rather than the file itself being the compute engine.

## Self
**URL:** https://en.wikipedia.org/wiki/Selflang
**Mapping:** Muhlnickel (file is the machine)
A prototype-based language where the entire memory environment and object state must be loaded from chunks of saved memory known as snapshots. The snapshot file acts as the complete computing environment.

## Squeak
**URL:** https://en.wikipedia.org/wiki/Squeak_(programming_language)
**Mapping:** Muhlnickel (file is the machine)
An open-source Smalltalk implementation where the `.image` file contains the live, reflective runtime state. The system is a "living" entity within the file, running on a virtual machine independent of the host hardware.

## Croquet
**URL:** https://en.wikipedia.org/wiki/Croquet_Project
**Mapping:** Muhlnickel (file is the machine)
A collaborative virtual environment built on Squeak. It extends the image-based compute model across a network, maintaining synchronized, replicated virtual machine states within the software images rather than relying on a centralized hardware host.
