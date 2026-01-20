from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor

from ..services.settings_store import load_settings, save_settings, AppSettings

# from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSpinBox, QCheckBox, QMessageBox, QComboBox, QRadioButton, QButtonGroup, QGraphicsDropShadowEffect
)

from ..models import JobConfig, ProjectSummary
from ..ui.widgets import title_label, section_label, hline
from ..services.drives_windows import list_windows_drives, drive_display
# from ..services.drives_windows import list_removable_drives, drive_display

from ..services.projects_list import load_recent_projects


class SetupScreen(QWidget):
    """
    Screen 1 (Project Setup) — UI skeleton + Existing Project UI.

    Existing Project list is read from a local JSON registry file (UI-only for now).
    """
    # def __init__(self, on_start, projects_registry_path: Path, on_open_ledger):
    def __init__(self, on_start, projects_registry_path: Path, on_open_ledger, settings_path: Path):
        super().__init__()
        self.on_start = on_start
        self._suppress_settings_save = True
        self.on_open_ledger = on_open_ledger
        self.projects_registry_path = projects_registry_path

        self.job = JobConfig()
        self._projects: list[ProjectSummary] = []
        self.settings_path = settings_path

        # self.setStyleSheet("""QWidget {background-color: rgba(17, 24, 39, 0.9); border-radius: 16px;}""")
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # root.addWidget(title_label("תחנת עיכול"))
        # subtitle = QLabel("Fill in the project details, choose drives, then start ingest.")
        # subtitle.setStyleSheet("color: #666;")
        # root.addWidget(subtitle)

        top_actions = QHBoxLayout()
        top_actions.addStretch(1)
        self.ledger_btn = QPushButton("📒 יומן פריקות")
        self.ledger_btn.clicked.connect(self.on_open_ledger)
        top_actions.addWidget(self.ledger_btn)
        root.addLayout(top_actions)

        root.addWidget(hline())

        # ---------------- Project mode ----------------
        # root.addWidget(section_label("סוג פריקה"))

        mode_row = QHBoxLayout()
        self.rb_new = QRadioButton("פרויקט חדש")
        self.rb_existing = QRadioButton("גלם חדש לפרויקט קיים")
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
        root.addWidget(section_label("ספר לי קצת פרטים, מותק שילי"))

        root.addWidget(QLabel("שם הלקוח"))
        self.client_edit = QLineEdit()
        self.client_edit.setPlaceholderText(" למשל - Ruvik")
        root.addWidget(self.client_edit)

        root.addWidget(QLabel("שם הפרויקט"))
        self.project_edit = QLineEdit()
        self.project_edit.setPlaceholderText("למשל - Hanukat Merkaz HaOf")
        root.addWidget(self.project_edit)

        root.addWidget(hline())

        # ---------------- Storage selection ----------------
        root.addWidget(section_label("לאן פורקים?"))

        # Archive combo
        root.addWidget(QLabel("MyBook"))
        self.archive_combo = QComboBox()
        self.archive_refresh_btn = QPushButton("רענן")
        self.archive_refresh_btn.clicked.connect(self.refresh_drives)
        self.archive_combo.currentIndexChanged.connect(self.on_archive_changed)

        row_a = QHBoxLayout()
        row_a.addWidget(self.archive_combo, 1)
        row_a.addWidget(self.archive_refresh_btn)
        root.addLayout(row_a)

        # Proxy combo
        root.addWidget(QLabel("SSD"))
        self.proxy_combo = QComboBox()
        self.proxy_refresh_btn = QPushButton("רענן")
        self.proxy_refresh_btn.clicked.connect(self.refresh_drives)
        self.proxy_combo.currentIndexChanged.connect(self.on_proxy_changed)

        row_p = QHBoxLayout()
        row_p.addWidget(self.proxy_combo, 1)
        row_p.addWidget(self.proxy_refresh_btn)
        root.addLayout(row_p)

        root.addWidget(hline())

        # ---------------- Cards ----------------
        root.addWidget(section_label("כרטיסים"))

        cards_row = QHBoxLayout()
        cards_row.addWidget(QLabel("כמה כירטוס"))
        self.cards_spin = QSpinBox()
        self.cards_spin.setMinimum(1)
        self.cards_spin.setMaximum(10)
        self.cards_spin.setValue(1)
        cards_row.addWidget(self.cards_spin)
        cards_row.addStretch(1)
        root.addLayout(cards_row)

        # hint = QLabel("You’ll be asked to insert each card one by one.")
        # hint.setStyleSheet("color: #666;")
        # root.addWidget(hint)

        root.addWidget(hline())

        # ---------------- Safety mode ----------------
        # root.addWidget(section_label("Safety Mode"))
        self.keep_originals_chk = QCheckBox("Keep a full copy of original footage on the Proxy SSD")
        self.keep_originals_chk.setChecked(True)
        # root.addWidget(self.keep_originals_chk)
        #
        # hint2 = QLabel("Recommended for urgent projects and quick fixes.")
        # hint2.setStyleSheet("color: #666;")
        # root.addWidget(hint2)
        #
        # root.addWidget(hline())

        self.glow = QGraphicsDropShadowEffect()
        self.glow.setBlurRadius(40)
        self.glow.setOffset(0, 0)
        self.glow.setColor(QColor(59, 130, 246, 180))

        # ---------------- Start ----------------
        self.start_btn = QPushButton("צ'אפסה")
        self.start_btn.setMinimumHeight(44)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_clicked)
        self.start_btn.setGraphicsEffect(self.glow)
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

        self._settings = load_settings(self.settings_path)
        # prevent save spam while restoring
        self._suppress_settings_save = True
        try:
            if self._settings.last_archive_root:
                idx = self.archive_combo.findData(self._settings.last_archive_root)
                if idx != -1:
                    self.archive_combo.setCurrentIndex(idx)

            if self._settings.last_proxy_root:
                idx = self.proxy_combo.findData(self._settings.last_proxy_root)
                if idx != -1:
                    self.proxy_combo.setCurrentIndex(idx)
        finally:
            self._suppress_settings_save = False

        self.refresh_projects()
        self.on_mode_changed()
        self._suppress_settings_save = False
        self.validate()

    def _save_settings(self):
        if getattr(self, "_suppress_settings_save", False):
            return

        try:
            archive = self.archive_combo.currentData()
            proxy = self.proxy_combo.currentData()

            archive_root = archive if isinstance(archive, str) and archive else ""
            proxy_root = proxy if isinstance(proxy, str) and proxy else ""

            # IMPORTANT: don't overwrite a valid file with empty placeholders
            if not archive_root and not proxy_root:
                return

            s = AppSettings(
                last_archive_root=archive_root,
                last_proxy_root=proxy_root,
            )
            save_settings(self.settings_path, s)
        except Exception:
            pass

    # def _save_settings(self):
    #     try:
    #         archive = self.archive_combo.currentData()
    #         proxy = self.proxy_combo.currentData()
    #
    #         # Only save real selections (not the "Select a drive..." placeholder)
    #         archive_root = archive if isinstance(archive, str) and archive else ""
    #         proxy_root = proxy if isinstance(proxy, str) and proxy else ""
    #
    #         s = AppSettings(
    #             last_archive_root=archive_root,
    #             last_proxy_root=proxy_root,
    #         )
    #         save_settings(self.settings_path, s)
    #     except Exception:
    #         pass

    # def _save_settings(self):
    #     try:
    #         s = AppSettings(
    #             last_archive_root=self.job.archive_path,
    #             last_proxy_root=self.job.proxy_path,
    #         )
    #         save_settings(self.settings_path, s)
    #     except Exception:
    #         pass

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
        # drives = list_removable_drives() or []

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
        self._save_settings()
        self.validate()

    def on_proxy_changed(self):
        root = self.proxy_combo.currentData()
        self.job.proxy_path = root if isinstance(root, str) else ""
        self.job.proxy_drive_display = self.proxy_combo.currentText() if self.job.proxy_path else ""
        self._save_settings()
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
