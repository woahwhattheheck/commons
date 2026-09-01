"""Fail-closed same-device path validation.

ChartTrace does not treat UNC paths, mapped remote drives, known network
filesystems, URI-like paths, or symbolic-link traversal as local storage.
"""

import os
from pathlib import Path, PureWindowsPath
from typing import Union


PathLike = Union[str, os.PathLike]

_REMOTE_FILESYSTEMS = {
    "9p",
    "afs",
    "ceph",
    "cifs",
    "davfs",
    "fuse.sshfs",
    "gcsfuse",
    "glusterfs",
    "lustre",
    "nfs",
    "nfs4",
    "smb3",
    "smbfs",
}


class PathBoundaryError(ValueError):
    """Raised when a path cannot be proven to be same-device local."""


def _reject_lexical_remote(path: PathLike) -> str:
    raw = os.fspath(path)
    if isinstance(raw, bytes):
        raw = os.fsdecode(raw)
    if not raw or "\x00" in raw:
        raise PathBoundaryError("A non-empty local path is required.")
    windows_path = PureWindowsPath(raw)
    if (
        raw.startswith(("\\\\", "//"))
        or windows_path.drive.startswith("\\\\")
        or "://" in raw
    ):
        raise PathBoundaryError("UNC, URI, and network-share paths are prohibited.")
    return raw


def _reject_symlink_traversal(path: Path) -> None:
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise PathBoundaryError("Symbolic-link traversal is prohibited.")


def _unescape_mount_path(value: str) -> str:
    return (
        value.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def _reject_posix_network_mount(path: Path) -> None:
    mount_info = Path("/proc/self/mountinfo")
    if os.name == "nt" or not mount_info.is_file():
        return
    resolved = path.resolve(strict=False)
    best_mount = Path("/")
    best_filesystem = ""
    try:
        lines = mount_info.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise PathBoundaryError("Unable to verify local filesystem boundary.") from error
    for line in lines:
        fields = line.split()
        if " - " not in line or len(fields) < 5:
            continue
        separator = fields.index("-")
        if separator + 1 >= len(fields):
            continue
        mount_path = Path(_unescape_mount_path(fields[4]))
        try:
            resolved.relative_to(mount_path)
        except ValueError:
            continue
        if len(mount_path.parts) >= len(best_mount.parts):
            best_mount = mount_path
            best_filesystem = fields[separator + 1].lower()
    if best_filesystem in _REMOTE_FILESYSTEMS:
        raise PathBoundaryError(
            f"Network filesystem {best_filesystem!r} is prohibited."
        )


def _reject_windows_remote_drive(path: Path) -> None:
    if os.name != "nt":
        return
    import ctypes

    resolved = path.resolve(strict=False)
    anchor = resolved.anchor
    if not anchor:
        raise PathBoundaryError("Unable to determine the local drive.")
    drive_type = ctypes.windll.kernel32.GetDriveTypeW(str(anchor))  # type: ignore[attr-defined]
    # DRIVE_REMOVABLE, DRIVE_FIXED, DRIVE_CDROM, and DRIVE_RAMDISK are local.
    if drive_type not in {2, 3, 5, 6}:
        raise PathBoundaryError("Mapped or unverifiable drives are prohibited.")


def _validate_boundary(path: PathLike) -> Path:
    raw = _reject_lexical_remote(path)
    candidate = Path(raw).expanduser()
    _reject_symlink_traversal(candidate)
    _reject_windows_remote_drive(candidate)
    _reject_posix_network_mount(candidate)
    return candidate


def validate_local_file(path: PathLike) -> Path:
    candidate = _validate_boundary(path)
    if not candidate.exists() or not candidate.is_file():
        raise PathBoundaryError("Expected an existing same-device local file.")
    return candidate


def validate_local_directory(path: PathLike, must_exist: bool = False) -> Path:
    candidate = _validate_boundary(path)
    if must_exist and (not candidate.exists() or not candidate.is_dir()):
        raise PathBoundaryError("Expected an existing same-device local directory.")
    if candidate.exists() and not candidate.is_dir():
        raise PathBoundaryError("Local data path must be a directory.")
    return candidate


def validate_local_output_path(path: PathLike) -> Path:
    candidate = _validate_boundary(path)
    if candidate.exists() and not candidate.is_file():
        raise PathBoundaryError("Output path must be a local file.")
    return candidate
