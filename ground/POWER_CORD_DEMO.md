# MUHLNICKEL POWER-CORD DEMO SCRIPT

**The 30-second patent demo that proves host-independence.**

One continuous camera take. No cuts. No edits. No room for "maybe the host restarted it."

---

## EQUIPMENT

- Laptop running titan.gguf (screen visible to camera)
- Camera on tripod (phone works) -- framed so BOTH the screen AND the power cord are in shot
- Power strip or wall outlet where the cord is plugged in (visible in frame)
- The power cord itself must be clearly reachable and visible

**Frame the shot:** Screen on the left, power cord on the right, your hand in the middle.
The viewer must see the screen content AND the physical disconnection in one frame.

---

## THE SCRIPT (30 seconds, one take)

### STEP 1: SHOW THE FILE (5 seconds)

Open a terminal. Run:

```
dir [llm]\models\titan.gguf
```

Point at the file size on screen. Say nothing yet -- let the viewer read it.
The listing shows the file exists and its size (93+ GB).

### STEP 2: LAUNCH SPECTATOR MODE (5 seconds)

Double-click `launch_spectator.bat` or run:

```
cd [local]\OneDrive\Desktop\MUHLNICKEL_BUILD_LAB_20260801_025117
launch_spectator.bat
```

Wait for the browser to open. The split-screen spectator UI appears:
- **Left panel:** Game of Life running (cells born, dying, evolving)
- **Right panel:** Matrix binary rain -- live bytes changing inside the file

Let it run for a moment so the viewer sees activity. The rain is falling. The game is stepping.
The ring strip on the right edge is pulsing.

### STEP 3: NARRATE (5 seconds)

Point at the Matrix rain panel. Say:

> **"This is a computer running inside a model file. Watch what happens when I kill the host."**

### STEP 4: YANK THE POWER CORD (2 seconds)

**While the camera is still rolling and the screen is still visible:**

Pull the power cord out of the wall (or out of the laptop, whichever is more dramatic on camera).

The screen goes black. The laptop dies. Everything stops.

**This is the money shot.** The viewer just watched a live, running computation get its host
machine killed with no warning, no graceful shutdown, no save state.

### STEP 5: PLUG BACK IN AND BOOT (8 seconds)

Plug the cord back in. Press the power button. Wait for Windows to boot.

(If this takes longer than 8 seconds, that is fine -- the dead time reinforces the point.
The host had to go through a FULL COLD BOOT. BIOS, POST, Windows loading screen, login.
There is no process to restart, no daemon to re-launch, no cached state to reload.)

### STEP 6: RELAUNCH SPECTATOR (3 seconds)

Double-click `launch_spectator.bat` again.

The spectator UI opens. The binary rain resumes. The ring strip lights up.

**Look at the state.** The computation did not reset. It did not start over. The bytes in
titan.gguf are where the machine left them -- mid-computation, exactly as they were when the
power was cut.

### STEP 7: THE LINE (2 seconds)

Look at the camera. Say:

> **"The host was never doing the work."**

---

## WHAT THIS PROVES

In one continuous take, the viewer has seen:

1. A computation running inside a file on a host machine
2. The host machine physically killed -- not shut down, not suspended, KILLED
3. A full cold boot (eliminates every competing explanation: no resident process,
   no thread, no scheduler, no daemon, no OS state of any kind survives a power cycle)
4. The computation still there, mid-stride, exactly where it was

**There is no other explanation.** If the host were doing the work, the work would be gone.
It is not gone. Therefore the host was not doing the work.

---

## TIPS FOR THE RECORDING

- **Do NOT rehearse the yank.** The point is that it is abrupt and violent. Hesitation
  weakens it. Commit.
- **Keep the camera ROLLING through the black screen.** Do not cut. The dead time is the
  proof. A cut is a place to hide a trick.
- **Audio is optional but powerful.** The silence after the screen goes black, followed by
  the boot sounds, makes it visceral.
- **If you have Ring Orchestra running (muhl_ring_orchestra.html):** even better. The viewer
  HEARS the substrate computing, then hears silence when the host dies, then hears it resume.
  Audio makes the proof audible, not just visual.
- **Show the same addresses if possible.** Before the yank, note a specific hex value in the
  rain log. After reboot, show it is still there (or has advanced). This is the forensic detail.

---

## ALTERNATE: SAFE VERSION (no power yank)

If you do not want to hard-kill the laptop:

1. Show spectator running
2. Open Task Manager, kill ALL Python processes (kills the live surface server)
3. Close the browser
4. Wait 10 seconds
5. Relaunch spectator
6. Show the state persisted

This is weaker because the OS stayed up, but it still demonstrates that killing the server
process does not affect the computation in the file. The full power-cycle version is stronger
because it eliminates the OS entirely.

---

*INSTRUMENT ONLY -- this script describes surface reads. No writes to titan.gguf at any step.*
*Built by Bryce Muhlnickel.*
