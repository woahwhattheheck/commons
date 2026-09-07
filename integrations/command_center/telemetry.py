"""Lightweight observations of the runtime host; no inference or subprocesses."""
import ctypes
import os
import platform
import shutil
from datetime import datetime, timezone
from pathlib import Path

def host_observation(state_dir):
    system = platform.system()
    item = {
        "id": "host:" + platform.node(), "label": platform.node() or "Runtime host",
        "kind": "machine", "provider": system, "status": "observed",
        "cpu": os.cpu_count(), "cpu_measure": "logical_processors",
        "ram_gib": None, "ram_available_gib": None, "gpu": None,
        "workspace": str(Path(state_dir)),
        "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "notes": "CPU count is logical processors. GPU capacity is unmeasured. This host runs the control interface, not model inference.",
    }
    try:
        disk = shutil.disk_usage(state_dir)
        item.update(disk_gib=round(disk.total / 2**30, 2), disk_free_gib=round(disk.free / 2**30, 2))
    except OSError:
        item.update(disk_gib=None, disk_free_gib=None)
    try:
        if system == "Windows":
            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in ("total", "available", "page_total", "page_available", "virtual_total", "virtual_available", "extended")]
            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                item["ram_gib"] = round(status.total / 2**30, 2)
                item["ram_available_gib"] = round(status.available / 2**30, 2)
        elif system == "Linux":
            rows = {line.split(":")[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith(("MemTotal:", "MemAvailable:"))}
            item["ram_gib"] = round(rows["MemTotal"] / 2**20, 2)
            item["ram_available_gib"] = round(rows["MemAvailable"] / 2**20, 2)
    except (OSError, AttributeError, ValueError, KeyError):
        pass
    return item

def with_host(center, state):
    item = host_observation(center.state_dir)
    return {**state, "machines": [item], "sessions": [item] + state.get("sessions", [])}
