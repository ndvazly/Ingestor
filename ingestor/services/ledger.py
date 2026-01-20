from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import JobConfig


LEDGER_HEADERS = [
    "session_started_at",
    "session_finished_at",
    "status",
    "mode",
    "client",
    "project",
    "num_cards",
    "archive_drive",
    "proxy_drive",
    "keep_originals_on_proxy",
]


def append_session_row(
    ledger_path: Path,
    *,
    started_at: datetime,
    finished_at: Optional[datetime],
    status: str,
    job: JobConfig,
) -> None:
    """
    Append one row per ingest session.

    This is the human-friendly studio ledger (ingest PC only).
    """
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not ledger_path.exists()
    print(f'append_session_row {job}')

    row = {
        "session_started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
        "session_finished_at": finished_at.strftime("%Y-%m-%d %H:%M:%S") if finished_at else "",
        "status": status,
        "mode": job.mode,
        "client": job.client_name,
        "project": job.project_name,
        "num_cards": job.num_cards,
        "archive_drive": job.archive_drive_display or job.archive_path,
        "proxy_drive": job.proxy_drive_display or job.proxy_path,
        "keep_originals_on_proxy": "Yes" if job.keep_originals_on_proxy else "No",
    }

    with ledger_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_HEADERS)
        if is_new:
            w.writeheader()
        w.writerow(row)
