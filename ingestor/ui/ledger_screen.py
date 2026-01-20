from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QDialog, QDialogButtonBox, QFormLayout, QMessageBox, QComboBox, QSpinBox
)

from ..ui.widgets import title_label, section_label, hline
from ..services.ledger import append_session_row
from ..models import JobConfig


class LedgerScreen(QWidget):
    """
    Simple ledger viewer for ingest_ledger.csv
    - Loads CSV (if exists)
    - Displays in a table
    - Text search filters rows (client/project/drive/status/date)
    """
    def __init__(self, ledger_path: Path, on_back = None):
        super().__init__()
        self.ledger_path = Path(ledger_path)
        self.on_back = on_back

        self._headers: List[str] = []
        self._rows: List[Dict[str, str]] = []

        root = QVBoxLayout(self)
        root.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.addWidget(title_label("Ingest Ledger"))
        header_row.addStretch(1)

        root.addLayout(header_row)

        subtitle = QLabel("This is the ingest PC ledger (one row per ingest session).")
        subtitle.setStyleSheet("color: #666;")
        root.addWidget(subtitle)

        root.addWidget(hline())

        # Search + actions
        actions = QHBoxLayout()
        actions.addWidget(QLabel("Search"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to filter (client, project, drives, status, dates...)")
        self.search_edit.textChanged.connect(self.apply_filter)
        actions.addWidget(self.search_edit, 1)

        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.open_add_dialog)
        actions.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        actions.addWidget(self.refresh_btn)
        root.addLayout(actions)

        root.addWidget(hline())

        root.addWidget(section_label("Sessions"))

        self.table = QTableWidget(0, 0)
        # self.table.setAlternatingRowColors(True)
        # self.table.setSelectionBehavior(self.table.selectRow)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        root.addWidget(self.table, 1)

        # hint = QLabel("Tip: Click a column header to sort.")
        # hint.setStyleSheet("color: #666;")
        # root.addWidget(hint)
        #
        self.refresh()

    def _format_datetime(self, value: str) -> str:
        try:
            dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%d/%m/%y %H:%M")
        except Exception:
            return value

    def refresh(self):
        self._headers, self._rows = self._load_csv(self.ledger_path)
        self._populate_table(self._headers, self._rows)
        self.apply_filter()

    def apply_filter(self):
        query = (self.search_edit.text() or "").strip().lower()
        if not query:
            self._populate_table(self._headers, self._rows)
            return

        filtered: List[Dict[str, str]] = []
        for r in self._rows:
            blob = "  ".join(str(v) for v in r.values()).lower()
            if query in blob:
                filtered.append(r)

        self._populate_table(self._headers, filtered)

    @staticmethod
    def _load_csv(path: Path):
        if not path.exists():
            return [], []

        try:
            with path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames or [])
                rows = [dict(row) for row in reader]
                return headers, rows
        except Exception as e:
            # Show error in UI
            return [], [{"error": f"Failed to read ledger: {e}"}]

    def _populate_table(self, headers: List[str], rows: List[Dict[str, str]]):
        self.table.setSortingEnabled(False)

        if not headers and rows and "error" in rows[0]:
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(["Error"])
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(rows[0]["error"]))
            self.table.resizeColumnsToContents()
            self.table.setSortingEnabled(False)
            return

        # Choose a friendly subset / order if headers match the known ledger schema
        preferred = [
            "session_started_at",
            # "session_finished_at",
            # "status",
            # "mode",
            "client",
            "project",
            "num_cards",
            "archive_drive",
            "proxy_drive",
            # "keep_originals_on_proxy",
        ]
        if headers:
            ordered = [h for h in preferred if h in headers]
            # ordered = [h for h in preferred if h in headers] + [h for h in headers if h not in preferred]
        else:
            ordered = preferred

        self.table.setColumnCount(len(ordered))
        self.table.setHorizontalHeaderLabels([self._pretty(h) for h in ordered])
        self.table.setRowCount(len(rows))

        for i, r in enumerate(rows):
            for j, h in enumerate(ordered):
                val = str(r.get(h, ""))
                if h in ("session_started_at", "session_finished_at"):
                    val = self._format_datetime(val)
                item = QTableWidgetItem(val)
                # Keep sorting as text; for dates this is fine given ISO-like strings
                item.setData(Qt.DisplayRole, val)
                self.table.setItem(i, j, item)

        # self.table.resizeColumnsToContents()
        from PySide6.QtWidgets import QHeaderView
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)  # manual widths only
        header.setStretchLastSection(False)

        widths = {
            "session_started_at": 140,
            "client": 140,
            "project": 300,
            "num_cards": 80,
            "archive_drive": 160,
            "proxy_drive": 160,
        }

        for col, name in enumerate(ordered):  # ordered = list of column keys in display order
            self.table.setColumnWidth(col, widths.get(name, 140))  # default width if not specified

        self.table.setSortingEnabled(True)

    @staticmethod
    def _pretty(header: str) -> str:
        # return header.replace("_", " ").title()
        NAMES = {
            "session_started_at": "Date",
            "archive_drive": "MyBook",
            "proxy_drive": "SSD",
        }

        return NAMES.get(header, header.replace("_", " ").title())

        # if on_back:
        #     self.back_btn = QPushButton("Back")
        #     self.back_btn.clicked.connect(self.on_back)
        #     header_row.addWidget(self.back_btn)

    def open_add_dialog(self):
        # You can adjust which fields you want to allow manual entry for:
        # We’ll keep it simple: date/time, client, project, archive, ssd, status, note
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Ledger Row")

        form = QFormLayout(dlg)

        dt_edit = QLineEdit(datetime.now().strftime("%d/%m/%y %H:%M"))  # your preferred format
        client_edit = QLineEdit()
        project_edit = QLineEdit()
        archive_edit = QLineEdit()
        ssd_edit = QLineEdit()
        cards_spin = QSpinBox()
        cards_spin.setMinimum(1)
        cards_spin.setMaximum(10)
        cards_spin.setValue(1)


        # status_combo = QComboBox()
        # status_combo.addItems(["OK", "FAILED", "CANCELED"])
        #
        # note_edit = QLineEdit()

        form.addRow("Date/Time", dt_edit)
        form.addRow("Client", client_edit)
        form.addRow("Project", project_edit)
        form.addRow("MyBook", archive_edit)
        form.addRow("SSD Drive", ssd_edit)
        form.addRow("Num Cards", cards_spin)


        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addRow(buttons)

        def on_ok():
            # Minimal validation
            if not client_edit.text().strip() or not project_edit.text().strip():
                QMessageBox.warning(dlg, "Missing info", "Client and Project are required.")
                return

            job: JobConfig = JobConfig()
            job.client_name = client_edit.text().strip()
            job.project_name = project_edit.text().strip()
            job.num_cards = cards_spin.text().strip()
            job.archive_path = archive_edit.text().strip()
            job.proxy_path = ssd_edit.text().strip()
            job_date = datetime.strptime(dt_edit.text().strip(), "%d/%m/%y %H:%M")

            try:
                append_session_row(self.ledger_path, started_at=job_date,
                                   finished_at=job_date, status='OK', job=job)
                dlg.accept()
                self.refresh()  # reload + reapply filter
            except Exception as e:
                QMessageBox.critical(dlg, "Failed", f"Could not write to ledger:\n{e}")

        buttons.accepted.connect(on_ok)
        buttons.rejected.connect(dlg.reject)

        dlg.exec()
