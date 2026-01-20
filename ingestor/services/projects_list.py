from __future__ import annotations

import json
from pathlib import Path
from typing import List

from ..models import ProjectSummary


def load_recent_projects(registry_path: Path) -> List[ProjectSummary]:
    """
    UI-only for now.

    Reads a local JSON file containing recent/active projects.
    If missing or invalid, returns an empty list.

    Expected shape:
    [
      {"client": "Iriya", "project": "Yom_HaAtsmaut", "last_updated": "2026-01-10"},
      ...
    ]
    """
    if not registry_path.exists():
        return []

    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
        results: List[ProjectSummary] = []
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                client = str(item.get("client", "")).strip()
                project = str(item.get("project", "")).strip()
                if not client or not project:
                    continue
                last_updated = str(item.get("last_updated", "")).strip()
                results.append(ProjectSummary(client=client, project=project, last_updated=last_updated))
        return results
    except Exception:
        return []
