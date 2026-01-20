import os
import subprocess
from datetime import date
from pathlib import Path
from ..services.drives_windows import get_drive_space

# --- helpers (self-contained) ---


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _fmt_gb(n: int) -> str:
    return f"{n / (1024**3):.1f} GB"


def _required_with_margin(used_bytes: int) -> int:
    # max(2GB, 5%) buffer
    return used_bytes + max(int(used_bytes * 0.05), 2 * 1024**3)


# def _drive_space_bytes(root: str) -> tuple[int, int]:
#     """
#     Returns (total_bytes, free_bytes) for a drive root like 'E:\\'
#     Uses Python's disk_usage (works great for drive roots).
#     """
#     # Windows fallback
#     import shutil
#     usage = shutil.disk_usage(root)
#     return usage.total, usage.free


def _robocopy_cmd(src_root: str, dst_root: str, log_path: str, mt: int = 4) -> list[str]:
    # NOTE: robocopy wants paths without trailing quotes; we pass them as separate args.
    # /MT:4 is a safer default when running TWO robocopies in parallel.
    return [
        "robocopy",
        src_root,
        dst_root,
        "/E",
        "/COPY:DAT",
        "/DCOPY:T",
        "/R:2", "/W:2",
        f"/MT:{mt}",
        "/XJ",
        "/NP",
        f"/LOG+:{log_path}",
    ]


def _robocopy_ok(exit_code: int) -> bool:
    # Robocopy convention: <8 = success (0..7), >=8 = failure
    return exit_code < 8

# Test function for error handling
#
# def ingest_one_card_parallel(
#     *,
#     sd_root: str,          # e.g. "G:\\"
#     archive_root: str,     # e.g. "E:\\"
#     ssd_root: str,         # e.g. "F:\\"
#     base_folder_name: str, # e.g. "Cactus"
#     client_project: str,   # e.g. "Iriya_-_Yom_HaAtsmaut"
#     ingest_date: str,      # e.g. "2026-01-15" (or date.today().isoformat())
#     sd_index: int,         # 1 for SD1, 2 for SD2...
# ) -> dict:
#
#     code_a = 9
#     code_s = 10
#     return {
#         "ok": False,
#         "reason": "ROBOCOPY_FAILED",
#         "archive_exit": code_a,
#         "ssd_exit": code_s,
#         "archive_log": "",
#         "ssd_log": "",
#         "sd_used": "",
#         "required": "",
#         "message": f"Copy failed. Archive exit={code_a}, SSD exit={code_s}. See logs.",
#     }

def ingest_one_card_parallel(
    *,
    sd_root: str,          # e.g. "G:\\"
    archive_root: str,     # e.g. "E:\\"
    ssd_root: str,         # e.g. "F:\\"
    base_folder_name: str, # e.g. "Cactus"
    client_project: str,   # e.g. "Iriya_-_Yom_HaAtsmaut"
    ingest_date: str,      # e.g. "2026-01-15" (or date.today().isoformat())
    sd_index: int,         # 1 for SD1, 2 for SD2...
) -> dict:
    """
    Copies SD card -> Archive and SD card -> SSD in parallel using robocopy.
    Performs a per-card free-space check for BOTH destinations before copying.
    Halts/returns failure if either robocopy fails. (We still let both finish.)
    """

    # Normalize roots
    sd_root = str(Path(sd_root))
    archive_root = str(Path(archive_root))
    ssd_root = str(Path(ssd_root))

    # Destination folder structure:
    # Raw:   X:\Cactus\<Client_Project>\Footage\<Date>\SD1
    # Proxy: X:\Cactus\<Client_Project>\Proxy\<Date>\SD1   (for now: duplicate raw)
    sd_name = f"SD{sd_index}"

    archive_dest = Path(archive_root) / base_folder_name / client_project / "Footage" / ingest_date / sd_name
    ssd_dest     = Path(ssd_root)     / base_folder_name / client_project / "Proxy"   / ingest_date / sd_name

    logs_dir_archive = Path(archive_root) / base_folder_name / client_project / "Footage" / ingest_date / "_logs"
    logs_dir_ssd     = Path(ssd_root)     / base_folder_name / client_project / "Proxy"   / ingest_date / "_logs"

    _ensure_dir(archive_dest)
    _ensure_dir(ssd_dest)
    _ensure_dir(logs_dir_archive)
    _ensure_dir(logs_dir_ssd)

    log_archive = str(logs_dir_archive / f"{sd_name}_archive_robocopy.log")
    log_ssd     = str(logs_dir_ssd     / f"{sd_name}_ssd_robocopy.log")

    # --- Space check (per-card, fast) ---
    sd_total, sd_free = get_drive_space(sd_root)
    sd_used = max(0, sd_total - sd_free)
    required = _required_with_margin(sd_used)

    _, a_free = get_drive_space(archive_root)
    _, s_free = get_drive_space(ssd_root)

    if a_free < required or s_free < required:
        return {
            "ok": False,
            "reason": "NOT_ENOUGH_SPACE",
            "sd_used": sd_used,
            "required": required,
            "archive_free": a_free,
            "ssd_free": s_free,
            "message": (
                f"Need ~{_fmt_gb(required)} for this card. "
                f"Archive free: {_fmt_gb(a_free)}; SSD free: {_fmt_gb(s_free)}."
            ),
        }

    # --- Start both robocopy processes in parallel ---
    cmd_a = _robocopy_cmd(sd_root, str(archive_dest), log_archive, mt=4)
    cmd_s = _robocopy_cmd(sd_root, str(ssd_dest),     log_ssd,     mt=4)

    # Use CREATE_NO_WINDOW to avoid flashing consoles (optional)
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    proc_a = subprocess.Popen(cmd_a, creationflags=creationflags)
    proc_s = subprocess.Popen(cmd_s, creationflags=creationflags)

    # Wait for both to finish (simple gist; GUI version will be non-blocking)
    code_a = proc_a.wait()
    code_s = proc_s.wait()

    ok_a = _robocopy_ok(code_a)
    ok_s = _robocopy_ok(code_s)

    if not (ok_a and ok_s):
        return {
            "ok": False,
            "reason": "ROBOCOPY_FAILED",
            "archive_exit": code_a,
            "ssd_exit": code_s,
            "archive_log": log_archive,
            "ssd_log": log_ssd,
            "message": f"Copy failed. Archive exit={code_a}, SSD exit={code_s}. See logs.",
        }

    return {
        "ok": True,
        "reason": "OK",
        "archive_exit": code_a,
        "ssd_exit": code_s,
        "archive_log": log_archive,
        "ssd_log": log_ssd,
        "sd_used": sd_used,
        "required": required,
        "message": "Copy OK to both destinations.",
    }


# Example call (for testing gist):
# result = ingest_one_card_parallel(
#     sd_root="G:\\",
#     archive_root="E:\\",
#     ssd_root="F:\\",
#     base_folder_name="Cactus",
#     client_project="Iriya_-_Yom_HaAtsmaut",
#     ingest_date=date.today().isoformat(),
#     sd_index=1,
# )
# print(result)
