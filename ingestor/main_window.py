from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from .models import JobConfig
from .ui.setup_screen import SetupScreen
from .ui.ingest_screen import IngestScreen
from .ui.ledger_screen import LedgerScreen


class MainWindow(QMainWindow):
    def __init__(self, projects_registry_path: Path, ledger_path: Path, settings_path: Path):
    # def __init__(self, projects_registry_path: Path, ledger_path: Path):
        super().__init__()
        self.setWindowTitle("Cactus Ingest Tool")
        self.setMinimumSize(400, 640)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.settings_path = settings_path

        self.setup_screen = SetupScreen(
            on_start=self.start_ingest,
            projects_registry_path=projects_registry_path,
            on_open_ledger=self.open_ledger,
            settings_path=self.settings_path,
        )

        self.ledger_path = ledger_path
        self.ingest_screen = IngestScreen(
            on_done=self.close,
            on_back_to_setup=self.back_to_setup,
            ledger_path=self.ledger_path,
        )

        self._ledger_window = None

        self.stack.addWidget(self.setup_screen)
        self.stack.addWidget(self.ingest_screen)
        # self.stack.addWidget(self.ledger_screen)

        self.stack.setCurrentWidget(self.setup_screen)

    def start_ingest(self, job: JobConfig):
        self.ingest_screen.load_job(job)
        self.stack.setCurrentWidget(self.ingest_screen)

    def open_ledger(self):
        # Refresh ledger screen each time we open it (so it updates after new sessions)
        # try:
        #     self.ledger_screen.refresh()
        # except Exception:
        #     print("can't refresh ledger")
        # If it's already open, just bring it to front
        # if self._ledger_window is not None:
        #     self._ledger_window.raise_()
        #     self._ledger_window.activateWindow()
        #     return

        # w = LedgerScreen(ledger_path=self.ledger_path, parent=None)
        w = LedgerScreen(ledger_path=self.ledger_path)

        self._ledger_window = w

        # When it closes, clear the reference so it can be reopened
        def _on_destroyed():
            self._ledger_window = None

        w.destroyed.connect(_on_destroyed)
        w.setMinimumSize(1000, 800)
        w.show()
        # self.stack.setCurrentWidget(self.ledger_screen)

    def back_to_setup(self):
        self.stack.setCurrentWidget(self.setup_screen)

