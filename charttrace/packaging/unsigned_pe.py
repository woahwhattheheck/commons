"""Deterministic unsigned PE32 stub for ChartTrace packaging receipts.

This is not a production binary, not code-signed, and not a clean-VM proof
by itself. It exists so a Linux host can still emit a real unsigned Windows
image plus a hash without inventing a signed installer.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict

ARTIFACT_LABEL = "UNSIGNED_SYNTHETIC"
SIGNING_STATE = "unsigned"
NOTICE = b"ChartTrace v1.1 UNSIGNED_SYNTHETIC signing_state=unsigned not-production\0"
MACHINE_I386 = 0x014C
IMAGE_BASE = 0x00400000
FILE_ALIGN = 0x200
SECTION_ALIGN = 0x1000


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "little")


def _u32(value: int) -> bytes:
    return value.to_bytes(4, "little")


def build_unsigned_pe_bytes() -> bytes:
    """Return a deterministic PE32 that calls ExitProcess(0)."""
    # .text at RVA 0x1000 / file 0x200: push 0; call [IAT]; padding
    # IAT lives at RVA 0x1040 so the call is a simple absolute address.
    text_rva = SECTION_ALIGN
    iat_rva = text_rva + 0x40
    # FF 15 xx xx xx xx = call dword ptr [imm32]
    call_iat = bytes((0x6A, 0x00, 0xFF, 0x15)) + _u32(IMAGE_BASE + iat_rva)
    text_body = call_iat + NOTICE
    text_raw_size = _align(max(len(text_body), 1), FILE_ALIGN)
    text_raw = text_body.ljust(text_raw_size, b"\x00")

    # .idata at RVA 0x2000 / file 0x400
    idata_rva = 2 * SECTION_ALIGN
    kernel32 = b"kernel32.dll\x00"
    hint_name = b"\x00\x00ExitProcess\x00"
    # Layout inside .idata:
    # 0x00 IMAGE_IMPORT_DESCRIPTOR (20) + terminator (20)
    # 0x28 ILT (4 + 4)
    # 0x30 IAT copy source (we also put the live IAT in .text; descriptor IAT RVA)
    # 0x38 hint/name
    # ... kernel32.dll
    hint_rva = idata_rva + 0x38
    ilt_rva = idata_rva + 0x28
    name_rva = idata_rva + 0x38 + len(hint_name)
    descriptor = (
        _u32(ilt_rva)  # OriginalFirstThunk
        + _u32(0)
        + _u32(0)
        + _u32(name_rva)
        + _u32(iat_rva)  # FirstThunk -> IAT in .text
    )
    terminator = b"\x00" * 20
    thunk = _u32(hint_rva) + _u32(0)
    idata_body = descriptor + terminator + thunk + thunk + hint_name + kernel32
    # Place a writable IAT slot inside .text so the loader can patch it.
    text_list = bytearray(text_raw)
    # IAT file offset inside .text: iat_rva - text_rva = 0x40
    text_list[0x40:0x48] = thunk
    text_raw = bytes(text_list)

    idata_raw_size = _align(len(idata_body), FILE_ALIGN)
    idata_raw = idata_body.ljust(idata_raw_size, b"\x00")

    size_of_headers = FILE_ALIGN
    text_raw_ptr = size_of_headers
    idata_raw_ptr = text_raw_ptr + text_raw_size
    size_of_image = _align(idata_rva + _align(len(idata_body), SECTION_ALIGN), SECTION_ALIGN)

    optional = bytearray()
    optional += _u16(0x010B)  # PE32
    optional += bytes((0x0E, 0x00))  # linker
    optional += _u32(text_raw_size)
    optional += _u32(idata_raw_size)
    optional += _u32(0)  # uninitialized
    optional += _u32(text_rva)  # entry
    optional += _u32(text_rva)  # base of code
    optional += _u32(idata_rva)  # base of data
    optional += _u32(IMAGE_BASE)
    optional += _u32(SECTION_ALIGN)
    optional += _u32(FILE_ALIGN)
    optional += _u16(4) + _u16(0)  # OS
    optional += _u16(0) + _u16(0)  # image
    optional += _u16(4) + _u16(0)  # subsystem
    optional += _u32(0)
    optional += _u32(size_of_image)
    optional += _u32(size_of_headers)
    optional += _u32(0)  # checksum
    optional += _u16(3)  # console
    optional += _u16(0)
    optional += _u32(0x00100000) + _u32(0x1000)
    optional += _u32(0x00100000) + _u32(0x1000)
    optional += _u32(0)
    optional += _u32(16)
    directories = [b"\x00" * 8 for _ in range(16)]
    directories[1] = _u32(idata_rva) + _u32(40)  # import
    directories[12] = _u32(iat_rva) + _u32(8)  # IAT
    optional += b"".join(directories)
    if len(optional) != 0xE0:
        raise RuntimeError(f"PE optional header must be 224 bytes, got {len(optional)}.")

    coff = (
        _u16(MACHINE_I386)
        + _u16(2)
        + _u32(0)
        + _u32(0)
        + _u32(0)
        + _u16(len(optional))
        + _u16(0x0102)
    )
    text_header = (
        b".text\x00\x00\x00"
        + _u32(len(text_body))
        + _u32(text_rva)
        + _u32(text_raw_size)
        + _u32(text_raw_ptr)
        + _u32(0)
        + _u32(0)
        + _u16(0)
        + _u16(0)
        + _u32(0x60000020)
    )
    idata_header = (
        b".idata\x00\x00"
        + _u32(len(idata_body))
        + _u32(idata_rva)
        + _u32(idata_raw_size)
        + _u32(idata_raw_ptr)
        + _u32(0)
        + _u32(0)
        + _u16(0)
        + _u16(0)
        + _u32(0xC0000040)
    )

    e_lfanew = 0x80
    dos = bytearray(e_lfanew)
    dos[0:2] = b"MZ"
    dos[0x3C:0x40] = _u32(e_lfanew)
    headers = bytes(dos) + b"PE\x00\x00" + coff + bytes(optional) + text_header + idata_header
    headers = headers.ljust(size_of_headers, b"\x00")
    return headers + text_raw + idata_raw


def write_unsigned_pe(dest: Path) -> Dict[str, object]:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob = build_unsigned_pe_bytes()
    dest.write_bytes(blob)
    return {
        "path": str(dest),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "size_bytes": len(blob),
        "artifact_label": ARTIFACT_LABEL,
        "signing_state": SIGNING_STATE,
        "production": False,
        "machine": "i386",
        "pe_magic": "MZ",
        "synthetic_released": False,
    }
