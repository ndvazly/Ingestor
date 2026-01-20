from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ingestor.main_window import MainWindow
from ingestor.theme import apply_dark_theme


def main() -> int:
    app = QApplication(sys.argv)
    apply_dark_theme(app)

    # UI-only registry file for the Existing Project dropdown.
    # For now it lives next to app.pyw (ingest PC local only).
    projects_registry_path = Path(__file__).resolve().parent / "projects_index.json"
    ledger_path = Path(__file__).resolve().parent / "ingest_ledger.csv"
    settings_path = Path(__file__).resolve().parent / "settings.json"

    print("LEDGER PATH:", ledger_path.resolve())

    # w = MainWindow(projects_registry_path=projects_registry_path, ledger_path=ledger_path)
    w = MainWindow(
        projects_registry_path=projects_registry_path,
        ledger_path=ledger_path,
        settings_path=settings_path,
    )
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
