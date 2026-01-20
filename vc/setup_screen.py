from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QCheckBox, QMessageBox, QComboBox, QRadioButton, QButtonGroup
)

from ..models import JobConfig, ProjectSummary
from ..ui.widgets import title_label, section_label, hline
from ..services.drives_windows import list_windows_drives, drive_display
from ..services.projects_list import load_recent_projects


class SetupScreen(QWidget):
    """
    Screen 1 (Project Setup) — UI skeleton + Existing Project UI.

    Existing Project list is read from a local JSON registry file (UI-only for now).
    """
    def __init__(self, on_start, projects_registry_path: Path):
        super().__init__()
        self.on_start = on_start
        self.projects_registry_path = projects_registry_path

        self.job = JobConfig()
        self._projects: list[ProjectSummary] = []

        root = QVBoxLayout(self)
        root.setSpacing(10)

        root.addWidget(title_label("Studio Ingest Tool"))
        subtitle = QLabel("Fill in the project details, choose drives, then start ingest.")
        subtitle.setStyleSheet("color: #666;")
        root.addWidget(subtitle)
        root.addWidget(hline())

        # ---------------- Project mode ----------------
        root.addWidget(section_label("Project"))

        mode_row = QHBoxLayout()
        self.rb_new = QRadioButton("New Project")
        self.rb_existing = QRadioButton("Add Footage to Existing Project")
        self.rb_new.setChecked(True)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.rb_new)
        self.mode_group.addButton(self.rb_existing)

        mode_row.addWidget(self.rb_new)
        mode_row.addWidget(self.rb_existing)
        mode_row.addStretch(1)
        root.addLayout(mode_row)

        # Existing project dropdown (hidden until existing mode)
        self.existing_lbl = QLabel("Select Existing Project")
        self.existing_combo = QComboBox()
        self.existing_combo.setEditable(True)  # type-to-filter
        self.existing_combo.setInsertPolicy(QComboBox.NoInsert)

        self.refresh_projects_btn = QPushButton("Refresh Projects")
        self.refresh_projects_btn.clicked.connect(self.refresh_projects)

        existing_row = QHBoxLayout()
        existing_row.addWidget(self.existing_combo, 1)
        existing_row.addWidget(self.refresh_projects_btn)

        root.addWidget(self.existing_lbl)
        root.addLayout(existing_row)

        # ---------------- Project information ----------------
        root.addWidget(hline())
        root.addWidget(section_label("Project Information"))

        root.addWidget(QLabel("Client Name"))
        self.client_edit = QLineEdit()
        self.client_edit.setPlaceholderText("e.g. City of Tel Aviv")
        root.addWidget(self.client_edit)

        root.addWidget(QLabel("Project Name"))
        self.project_edit = QLineEdit()
        self.project_edit.setPlaceholderText("e.g. Mayor Weekly Update – Jan 2026")
        root.addWidget(self.project_edit)

        root.addWidget(hline())

        # ---------------- Storage selection ----------------
        root.addWidget(section_label("Where should the files go?"))

        # Archive combo
        root.addWidget(QLabel("Archive Drive (Originals)"))
        self.archive_combo = QComboBox()
        self.archive_refresh_btn = QPushButton("Refresh Drives")
        self.archive_refresh_btn.clicked.connect(self.refresh_drives)
        self.archive_combo.currentIndexChanged.connect(self.on_archive_changed)

        row_a = QHBoxLayout()
        row_a.addWidget(self.archive_combo, 1)
        row_a.addWidget(self.archive_refresh_btn)
        root.addLayout(row_a)

        # Proxy combo
        root.addWidget(QLabel("Proxy SSD (Editor Drive)"))
        self.proxy_combo = QComboBox()
        self.proxy_refresh_btn = QPushButton("Refresh Drives")
        self.proxy_refresh_btn.clicked.connect(self.refresh_drives)
        self.proxy_combo.currentIndexChanged.connect(self.on_proxy_changed)

        row_p = QHBoxLayout()
        row_p.addWidget(self.proxy_combo, 1)
        row_p.addWidget(self.proxy_refresh_btn)
        root.addLayout(row_p)

        root.addWidget(hline())

        # ---------------- Cards ----------------
        root.addWidget(section_label("Camera Cards"))

        cards_row = QHBoxLayout()
        cards_row.addWidget(QLabel("Number of Cards"))
        self.cards_spin = QSpinBox()
        self.cards_spin.setMinimum(1)
        self.cards_spin.setMaximum(10)
        self.cards_spin.setValue(1)
        cards_row.addWidget(self.cards_spin)
        cards_row.addStretch(1)
        root.addLayout(cards_row)

        hint = QLabel("You’ll be asked to insert each card one by one.")
        hint.setStyleSheet("color: #666;")
        root.addWidget(hint)

        root.addWidget(hline())

        # ---------------- Safety mode ----------------
        root.addWidget(section_label("Safety Mode"))
        self.keep_originals_chk = QCheckBox("Keep a full copy of original footage on the Proxy SSD")
        self.keep_originals_chk.setChecked(True)
        root.addWidget(self.keep_originals_chk)

        hint2 = QLabel("Recommended for urgent projects and quick fixes.")
        hint2.setStyleSheet("color: #666;")
        root.addWidget(hint2)

        root.addWidget(hline())

        # ---------------- Start ----------------
        self.start_btn = QPushButton("START INGEST")
        self.start_btn.setMinimumHeight(44)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_clicked)
        root.addWidget(self.start_btn)

        root.addStretch(1)

        # Hooks
        self.rb_new.toggled.connect(self.on_mode_changed)
        self.rb_existing.toggled.connect(self.on_mode_changed)
        self.existing_combo.currentIndexChanged.connect(self.on_existing_selected)

        self.client_edit.textChanged.connect(self.validate)
        self.project_edit.textChanged.connect(self.validate)
        self.cards_spin.valueChanged.connect(self.validate)
        self.keep_originals_chk.stateChanged.connect(self.validate)

        # Init
        self.refresh_drives()
        self.refresh_projects()
        self.on_mode_changed()
        self.validate()

    # ---------- Projects list (UI only) ----------
    def refresh_projects(self):
        self._projects = load_recent_projects(self.projects_registry_path)

        self.existing_combo.blockSignals(True)
        self.existing_combo.clear()
        self.existing_combo.addItem("Select a project...", None)

        for p in self._projects:
            label = f"{p.client} — {p.project}"
            self.existing_combo.addItem(label, p)

        self.existing_combo.blockSignals(False)
        self.validate()

    def on_existing_selected(self):
        if not self.rb_existing.isChecked():
            return

        p = self.existing_combo.currentData()
        if isinstance(p, ProjectSummary):
            # Fill fields and keep them read-only for confidence
            self.client_edit.setText(p.client)
            self.project_edit.setText(p.project)
        self.validate()

    # ---------- Drives ----------
    def refresh_drives(self):
        prev_archive = self.job.archive_path
        prev_proxy = self.job.proxy_path

        drives = list_windows_drives() or []

        def fill_combo(combo, prev_value):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Select a drive...", "")

            for root, label in drives:
                combo.addItem(drive_display(root, label), root)

            if prev_value:
                idx = combo.findData(prev_value)
                if idx != -1:
                    combo.setCurrentIndex(idx)

            combo.blockSignals(False)

        fill_combo(self.archive_combo, prev_archive)
        fill_combo(self.proxy_combo, prev_proxy)

        # Update display strings after combos are populated
        self.on_archive_changed()
        self.on_proxy_changed()
        self.validate()

    def on_archive_changed(self):
        root = self.archive_combo.currentData()
        self.job.archive_path = root if isinstance(root, str) else ""
        self.job.archive_drive_display = self.archive_combo.currentText() if self.job.archive_path else ""
        self.validate()

    def on_proxy_changed(self):
        root = self.proxy_combo.currentData()
        self.job.proxy_path = root if isinstance(root, str) else ""
        self.job.proxy_drive_display = self.proxy_combo.currentText() if self.job.proxy_path else ""
        self.validate()

    # ---------- Mode switching ----------
    def on_mode_changed(self):
        existing = self.rb_existing.isChecked()

        self.existing_lbl.setVisible(existing)
        self.existing_combo.setVisible(existing)
        self.refresh_projects_btn.setVisible(existing)

        # In existing mode, fields are read-only and populated by selection
        self.client_edit.setReadOnly(existing)
        self.project_edit.setReadOnly(existing)

        if not existing:
            # New project mode: allow typing, clear existing selection
            self.existing_combo.setCurrentIndex(0)
            # Keep whatever the user typed
        else:
            # Existing mode: clear text fields until selection
            self.client_edit.setText("")
            self.project_edit.setText("")

        self.validate()

    # ---------- Validation & start ----------
    def validate(self):
        self.job.mode = "existing" if self.rb_existing.isChecked() else "new"
        self.job.num_cards = int(self.cards_spin.value())
        self.job.keep_originals_on_proxy = bool(self.keep_originals_chk.isChecked())

        if self.job.mode == "new":
            self.job.client_name = self.client_edit.text().strip()
            self.job.project_name = self.project_edit.text().strip()
            project_ok = len(self.job.client_name) > 0 and len(self.job.project_name) > 0
        else:
            selected = self.existing_combo.currentData()
            project_ok = isinstance(selected, ProjectSummary)
            self.job.client_name = self.client_edit.text().strip()
            self.job.project_name = self.project_edit.text().strip()

        drives_ok = (len(self.job.archive_path) > 0 and len(self.job.proxy_path) > 0)
        ok = project_ok and drives_ok

        self.start_btn.setEnabled(ok)

    def start_clicked(self):
        self.validate()
        if not self.start_btn.isEnabled():
            return

        if self.job.archive_path == self.job.proxy_path:
            QMessageBox.warning(
                self,
                "Drive Selection",
                "Archive and Proxy locations should be different.\n\nPlease select different destinations."
            )
            return

        # In existing mode, we already filled client/project; no new logic yet
        self.on_start(self.job)
