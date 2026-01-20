from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class JobConfig:
    client_name: str = ""
    project_name: str = ""
    num_cards: int = 1
    archive_path: str = ""
    proxy_path: str = ""
    archive_drive_display: str = ""  # e.g. "E: - MyBook 2"
    proxy_drive_display: str = ""    # e.g. "F: - PROXY_B"
    keep_originals_on_proxy: bool = True

    # UI-only: whether we are creating a new project or adding to an existing one.
    mode: str = "new"  # "new" | "existing"

    def safe_project_folder(self) -> str:
        raw = f"{self.client_name}_-_{self.project_name}".strip()
        raw = re.sub(r"\s+", "_", raw)
        raw = re.sub(r"[^A-Za-z0-9_\-]", "", raw)
        return raw[:80] if raw else "Untitled_Project"


@dataclass(frozen=True)
class ProjectSummary:
    """
    A light-weight record for the Existing Project dropdown (UI only).
    """
    client: str
    project: str
    last_updated: str = ""  # ISO string or friendly date
