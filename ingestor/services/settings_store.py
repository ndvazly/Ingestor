from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppSettings:
    last_archive_root: str = ""
    last_proxy_root: str = ""


def load_settings(path: Path) -> AppSettings:
    if not path.exists():
        return AppSettings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppSettings(
            last_archive_root=str(data.get("last_archive_root", "")).strip(),
            last_proxy_root=str(data.get("last_proxy_root", "")).strip(),
        )
    except Exception:
        return AppSettings()


def save_settings(path: Path, s: AppSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_archive_root": s.last_archive_root,
        "last_proxy_root": s.last_proxy_root,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
