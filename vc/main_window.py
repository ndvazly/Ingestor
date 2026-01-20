from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from .models import JobConfig
from .ui.setup_screen import SetupScreen
from .ui.ingest_screen import IngestScreen


class MainWindow(QMainWindow):
    def __init__(self, projects_registry_path: Path, ledger_path: Path):
        super().__init__()
        self.setWindowTitle("Studio Ingest Tool")
        self.setMinimumSize(820, 700)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.setup_screen = SetupScreen(
            on_start=self.start_ingest,
            projects_registry_path=projects_registry_path,
        )
        self.ledger_path = ledger_path
        self.ingest_screen = IngestScreen(
            on_done=self.close,
            on_back_to_setup=self.back_to_setup,
            ledger_path=self.ledger_path,
        )

        self.stack.addWidget(self.setup_screen)
        self.stack.addWidget(self.ingest_screen)

        self.stack.setCurrentWidget(self.setup_screen)

    def start_ingest(self, job: JobConfig):
        self.ingest_screen.load_job(job)
        self.stack.setCurrentWidget(self.ingest_screen)

    def back_to_setup(self):
        self.stack.setCurrentWidget(self.setup_screen)
