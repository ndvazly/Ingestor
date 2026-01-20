import sys
import re
import os
import string
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QCheckBox, QTextEdit, QProgressBar,
    QFileDialog, QMessageBox, QStackedWidget, QFrame, QSizePolicy
)


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

GetLogicalDrives = kernel32.GetLogicalDrives
GetLogicalDrives.restype = wintypes.DWORD

GetVolumeInformationW = kernel32.GetVolumeInformationW
GetVolumeInformationW.argtypes = [
    wintypes.LPCWSTR,  # lpRootPathName
    wintypes.LPWSTR,   # lpVolumeNameBuffer
    wintypes.DWORD,    # nVolumeNameSize
    ctypes.POINTER(wintypes.DWORD),  # lpVolumeSerialNumber
    ctypes.POINTER(wintypes.DWORD),  # lpMaximumComponentLength
    ctypes.POINTER(wintypes.DWORD),  # lpFileSystemFlags
    wintypes.LPWSTR,   # lpFileSystemNameBuffer
    wintypes.DWORD     # nFileSystemNameSize
]
GetVolumeInformationW.restype = wintypes.BOOL


def drive_display(root: str, label: str) -> str:
    letter = root[:2]  # "E:"
    if label:
        return f"{letter} - {label}"
    return f"{letter} - (No Label)"


def list_windows_drives() -> list[tuple[str, str]]:
    """
    Returns list of (root, label) like ("E:\\", "MyBook 2").
    Includes fixed + removable drives. Label may be "" if unknown.
    """
    drives_bitmask = GetLogicalDrives()
    results: list[tuple[str, str]] = []

    for letter in string.ascii_uppercase:
        if not (drives_bitmask & (1 << (ord(letter) - ord("A")))):
            continue

        root = f"{letter}:\\"
        if not os.path.exists(root):
            continue

        vol_name_buf = ctypes.create_unicode_buffer(261)
        fs_name_buf = ctypes.create_unicode_buffer(261)
        serial = wintypes.DWORD()
        max_comp = wintypes.DWORD()
        fs_flags = wintypes.DWORD()

        ok = GetVolumeInformationW(
            root,
            vol_name_buf,
            len(vol_name_buf),
            ctypes.byref(serial),
            ctypes.byref(max_comp),
            ctypes.byref(fs_flags),
            fs_name_buf,
            len(fs_name_buf)
        )

        label = vol_name_buf.value.strip() if ok else ""
        results.append((root, label))
    return results


def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")

    dark_qss = """
    QWidget {
        background-color: #1e1e1e;
        color: #e6e6e6;
        font-size: 10pt;
    }

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
        background-color: #252526;
        border: 1px solid #3c3c3c;
        border-radius: 6px;
        padding: 6px;
        selection-background-color: #2d74da;
        selection-color: #ffffff;
    }

    QLabel {
        color: #e6e6e6;
    }

    QCheckBox {
        spacing: 8px;
    }

    QCheckBox::indicator {
        width: 16px;
        height: 16px;
    }

    QCheckBox::indicator:unchecked {
        border: 1px solid #6a6a6a;
        background-color: #2b2b2b;
        border-radius: 3px;
    }

    QCheckBox::indicator:checked {
        border: 1px solid #2d74da;
        background-color: #2d74da;
        border-radius: 3px;
    }

    QPushButton {
        background-color: #2b2b2b;
        border: 1px solid #3c3c3c;
        border-radius: 8px;
        padding: 10px;
    }

    QPushButton:hover {
        border: 1px solid #5a5a5a;
        background-color: #323232;
    }

    QPushButton:pressed {
        background-color: #252526;
    }

    QPushButton:disabled {
        color: #777777;
        background-color: #242424;
        border: 1px solid #2e2e2e;
    }

    QProgressBar {
        background-color: #252526;
        border: 1px solid #3c3c3c;
        border-radius: 6px;
        text-align: center;
        padding: 2px;
    }

    QProgressBar::chunk {
        background-color: #2d74da;
        border-radius: 5px;
    }

    QFrame[frameShape="4"] { /* HLine */
        color: #3c3c3c;
    }

    QMessageBox {
        background-color: #1e1e1e;
    }
    """

    app.setStyleSheet(dark_qss)

# -----------------------------
# Data model (shared state)
# -----------------------------
@dataclass
class JobConfig:
    client_name: str = ""
    project_name: str = ""
    num_cards: int = 1
    archive_path: str = ""
    proxy_path: str = ""
    keep_originals_on_proxy: bool = True

    def safe_project_folder(self) -> str:
        # Simple folder-safe name: letters/numbers/_- and spaces -> underscore
        raw = f"{self.client_name}_{self.project_name}".strip()
        raw = re.sub(r"\s+", "_", raw)
        raw = re.sub(r"[^A-Za-z0-9_\-]", "", raw)
        return raw[:80] if raw else "Untitled_Project"


# -----------------------------
# Small UI helpers
# -----------------------------
def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


def title_label(text: str) -> QLabel:
    lbl = QLabel(text)
    f = QFont()
    f.setPointSize(12)
    f.setBold(True)
    lbl.setFont(f)
    return lbl


def section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    f = QFont()
    f.setPointSize(10)
    f.setBold(True)
    lbl.setFont(f)
    return lbl


# -----------------------------
# Screen 1: Project setup
# -----------------------------
class SetupScreen(QWidget):
    def __init__(self, on_start):
        super().__init__()
        self.on_start = on_start
        self.job = JobConfig()

        root = QVBoxLayout(self)
        root.setSpacing(10)

        root.addWidget(title_label("Ingest0r by azly"))
        subtitle = QLabel("בוא לזוז לקצב, אל המנגינה, זהו הפרקן האוטומטי.")
        subtitle.setStyleSheet("color: #666;")
        root.addWidget(subtitle)
        root.addWidget(hline())

        # Project Information
        root.addWidget(section_label("פרטי הפרויקט"))

        self.client_edit = QLineEdit()
        self.client_edit.setPlaceholderText("לדוגמא: רוביק")
        root.addWidget(QLabel("שם הלקוח"))
        root.addWidget(self.client_edit)

        self.project_edit = QLineEdit()
        self.project_edit.setPlaceholderText("לדוגמא: פתיחת מרכז העוף")
        root.addWidget(QLabel("שם פרויקט"))
        root.addWidget(self.project_edit)

        root.addWidget(hline())

        # Storage Selection
        root.addWidget(section_label("Where should the files go?"))

        # self.archive_display = QLabel("Not selected")
        # self.archive_display.setStyleSheet("color: #b00;")
        # self.archive_btn = QPushButton("Select Archive Drive")
        # self.archive_btn.clicked.connect(self.pick_archive)

        from PySide6.QtWidgets import QComboBox  # add this to imports at top if missing

        self.archive_combo = QComboBox()
        self.archive_refresh_btn = QPushButton("Refresh")

        row_a = QHBoxLayout()
        row_a.addWidget(QLabel("Archive Drive (Originals)"))
        row_a.addStretch(1)
        root.addLayout(row_a)

        row_a2 = QHBoxLayout()
        row_a2.addWidget(self.archive_combo, 1)
        row_a2.addWidget(self.archive_refresh_btn)
        root.addLayout(row_a2)

        self.archive_refresh_btn.clicked.connect(self.refresh_drives)
        self.archive_combo.currentIndexChanged.connect(self.on_archive_changed)

        self.proxy_combo = QComboBox()
        self.proxy_refresh_btn = QPushButton("Refresh")

        row_p = QHBoxLayout()
        row_p.addWidget(QLabel("Proxy SSD (Editor Drive)"))
        row_p.addStretch(1)
        root.addLayout(row_p)

        row_p2 = QHBoxLayout()
        row_p2.addWidget(self.proxy_combo, 1)
        row_p2.addWidget(self.proxy_refresh_btn)
        root.addLayout(row_p2)

        self.proxy_refresh_btn.clicked.connect(self.refresh_drives)
        self.proxy_combo.currentIndexChanged.connect(self.on_proxy_changed)

        # row_a = QHBoxLayout()
        # row_a.addWidget(self.archive_btn)
        # row_a.addWidget(self.archive_display, 1)
        # root.addLayout(row_a)

        # self.proxy_display = QLabel("Not selected")
        # self.proxy_display.setStyleSheet("color: #b00;")
        # self.proxy_btn = QPushButton("Select Proxy SSD")
        # self.proxy_btn.clicked.connect(self.pick_proxy)
        #
        # row_p = QHBoxLayout()
        # row_p.addWidget(self.proxy_btn)
        # row_p.addWidget(self.proxy_display, 1)
        # root.addLayout(row_p)

        root.addWidget(hline())

        # Cards
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

        # Safety mode
        root.addWidget(section_label("Safety Mode"))
        self.keep_originals_chk = QCheckBox("Keep a full copy of original footage on the Proxy SSD")
        self.keep_originals_chk.setChecked(True)
        root.addWidget(self.keep_originals_chk)

        hint2 = QLabel("Recommended for urgent projects and quick fixes.")
        hint2.setStyleSheet("color: #666;")
        root.addWidget(hint2)

        root.addWidget(hline())

        # Start button
        self.start_btn = QPushButton("START INGEST")
        self.start_btn.setMinimumHeight(44)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_clicked)
        root.addWidget(self.start_btn)

        # Spacer
        root.addStretch(1)

        # Validation hooks
        self.client_edit.textChanged.connect(self.validate)
        self.project_edit.textChanged.connect(self.validate)

        self.refresh_drives()

        # self.validate()

    def refresh_drives(self):
        # Keep previous selections if possible
        prev_archive = self.job.archive_path
        prev_proxy = self.job.proxy_path

        drives = list_windows_drives()

        def fill_combo(combo, prev_value):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Select a drive...", "")  # placeholder item

            for root, label in drives:
                # combo.addItem(drive_display(root, label), root)
                letter = root[:2]
                text = f"{letter} - {label}" if label else f"{letter} - (No Label)"
                combo.addItem(text, root)

            # restore selection
            if prev_value:
                idx = combo.findData(prev_value)
                if idx != -1:
                    combo.setCurrentIndex(idx)
            combo.blockSignals(False)

        fill_combo(self.archive_combo, prev_archive)
        fill_combo(self.proxy_combo, prev_proxy)

        self.validate()

    def on_archive_changed(self):
        root = self.archive_combo.currentData()
        self.job.archive_path = root if isinstance(root, str) else ""
        self.validate()

    def on_proxy_changed(self):
        root = self.proxy_combo.currentData()
        self.job.proxy_path = root if isinstance(root, str) else ""
        self.validate()

    # def pick_archive(self):
    #     path = QFileDialog.getExistingDirectory(self, "Select Archive Drive / Folder")
    #     if path:
    #         self.job.archive_path = path
    #         self.archive_display.setText(path)
    #         self.archive_display.setStyleSheet("color: #080;")
    #         self.validate()
    #
    # def pick_proxy(self):
    #     path = QFileDialog.getExistingDirectory(self, "Select Proxy SSD / Folder")
    #     if path:
    #         self.job.proxy_path = path
    #         self.proxy_display.setText(path)
    #         self.proxy_display.setStyleSheet("color: #080;")
    #         self.validate()

    def validate(self):
        self.job.client_name = self.client_edit.text().strip()
        self.job.project_name = self.project_edit.text().strip()
        self.job.num_cards = int(self.cards_spin.value())
        self.job.keep_originals_on_proxy = bool(self.keep_originals_chk.isChecked())

        ok = (
            len(self.job.client_name) > 0
            and len(self.job.project_name) > 0
            and len(self.job.archive_path) > 0
            and len(self.job.proxy_path) > 0
        )
        self.start_btn.setEnabled(ok)

    def start_clicked(self):
        self.validate()
        if not self.start_btn.isEnabled():
            return

        # Basic guard: prevent selecting same folder for both
        if self.job.archive_path == self.job.proxy_path:
            QMessageBox.warning(
                self,
                "Drive Selection",
                "Archive and Proxy locations should be different.\n\nPlease select different destinations."
            )
            return

        self.on_start(self.job)


# -----------------------------
# Screen 2: Card ingest & progress
# -----------------------------
class IngestScreen(QWidget):
    def __init__(self, on_done, on_back_to_setup):
        super().__init__()
        self.on_done = on_done
        self.on_back_to_setup = on_back_to_setup

        self.job: JobConfig | None = None
        self.current_card = 0
        self.ingest_running = False

        self._fake_progress = 0
        self._phase = "idle"  # idle | waiting_card | copying | proxying | finalizing | done
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        root.addWidget(title_label("Ingesting Camera Cards"))
        self.card_counter_lbl = QLabel("Card 0 of 0")
        self.card_counter_lbl.setStyleSheet("color: #666;")
        root.addWidget(self.card_counter_lbl)

        root.addWidget(hline())

        # Project context (read-only)
        root.addWidget(section_label("Project"))

        self.project_context = QLabel("")
        self.project_context.setWordWrap(True)
        self.project_context.setStyleSheet("color: #333;")
        root.addWidget(self.project_context)

        root.addWidget(hline())

        # Instruction box
        self.instruction = QLabel("Insert camera card #1 and click CONTINUE")
        self.instruction.setAlignment(Qt.AlignCenter)
        self.instruction.setWordWrap(True)
        self.instruction.setMinimumHeight(60)
        self.instruction.setStyleSheet(
            "border: 1px solid #3c3c3c; border-radius: 8px; padding: 12px; background: #252526;"
        )
        root.addWidget(self.instruction)

        # Dev-only: simulate card inserted
        self.sim_card_chk = QCheckBox("DEV: simulate card inserted (temporary)")
        self.sim_card_chk.stateChanged.connect(self._update_continue_enabled)
        root.addWidget(self.sim_card_chk)

        # Buttons row
        btn_row = QHBoxLayout()
        self.continue_btn = QPushButton("CONTINUE")
        self.continue_btn.setMinimumHeight(40)
        self.continue_btn.setEnabled(False)
        self.continue_btn.clicked.connect(self.continue_clicked)

        self.cancel_btn = QPushButton("Cancel Ingest")
        self.cancel_btn.clicked.connect(self.cancel_clicked)

        btn_row.addWidget(self.continue_btn, 2)
        btn_row.addWidget(self.cancel_btn, 1)
        root.addLayout(btn_row)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        # Status/log
        root.addWidget(section_label("Status"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(180)
        self.log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.log, 1)

        # Completion controls
        self.eject_btn = QPushButton("EJECT DRIVES")
        self.eject_btn.setMinimumHeight(40)
        self.eject_btn.setVisible(False)
        self.eject_btn.clicked.connect(self.eject_clicked)

        self.close_btn = QPushButton("Close")
        self.close_btn.setMinimumHeight(40)
        self.close_btn.setVisible(False)
        self.close_btn.clicked.connect(self.on_done)

        done_row = QHBoxLayout()
        done_row.addWidget(self.eject_btn)
        done_row.addWidget(self.close_btn)
        root.addLayout(done_row)

        root.addStretch(0)

    def load_job(self, job: JobConfig):
        self.job = job
        self.current_card = 0
        self.ingest_running = False
        self._fake_progress = 0
        self._phase = "waiting_card"
        self.progress.setValue(0)
        self.sim_card_chk.setChecked(False)

        self.eject_btn.setVisible(False)
        self.close_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.continue_btn.setVisible(True)

        self.project_context.setText(
            f"<b>{job.client_name}</b><br>"
            f"{job.project_name}<br><br>"
            f"<b>Archive:</b> {job.archive_path}<br>"
            f"<b>Proxy SSD:</b> {job.proxy_path}<br>"
            f"<b>Keep originals on proxy:</b> {'Yes' if job.keep_originals_on_proxy else 'No'}"
        )

        self.log.clear()
        self._log(f"Ready. {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._advance_to_next_card()

    def _log(self, msg: str):
        self.log.append(msg)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _advance_to_next_card(self):
        assert self.job is not None
        self.current_card += 1
        self.card_counter_lbl.setText(f"Card {self.current_card} of {self.job.num_cards}")
        self.instruction.setText(f"Insert camera card #{self.current_card} and click CONTINUE")
        self._phase = "waiting_card"
        self.progress.setValue(0)
        self._fake_progress = 0
        self.sim_card_chk.setChecked(False)
        self._update_continue_enabled()
        self._log(f"Waiting for card {self.current_card}...")

    def _update_continue_enabled(self):
        # For v0 UX testing only: Continue becomes enabled only if "card inserted" is simulated.
        # Later we’ll replace this with actual removable-drive detection.
        can_continue = (self._phase == "waiting_card") and self.sim_card_chk.isChecked()
        self.continue_btn.setEnabled(can_continue)

    def continue_clicked(self):
        if self._phase != "waiting_card":
            return
        if not self.sim_card_chk.isChecked():
            return

        # Start fake ingest phases for this card
        self.ingest_running = True
        self.continue_btn.setEnabled(False)
        self._phase = "copying"
        self._fake_progress = 0
        self._log(f"Detected card #{self.current_card} (simulated).")
        self._log("Copying originals to ARCHIVE...")
        self._timer.start(60)

    def cancel_clicked(self):
        if not self.job:
            return
        reply = QMessageBox.question(
            self,
            "Cancel ingest?",
            "Canceling will leave copied files intact but incomplete.\n\nDo you want to cancel?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._timer.stop()
            self._log("Ingest canceled by user.")
            self.on_back_to_setup()

    def _tick(self):
        # Fake progress animation for UX validation
        if self._phase == "copying":
            self._fake_progress += 2
            self.progress.setValue(min(self._fake_progress, 100))

            if self._fake_progress == 20:
                self._log("Copying originals to PROXY SSD...")
            if self._fake_progress == 50:
                self._log("Verifying files (simulated)...")
            if self._fake_progress >= 100:
                self._phase = "proxying"
                self._fake_progress = 0
                self.progress.setValue(0)
                self._log("Generating proxies (simulated)...")

        elif self._phase == "proxying":
            self._fake_progress += 3
            self.progress.setValue(min(self._fake_progress, 100))
            if self._fake_progress >= 100:
                self._timer.stop()
                self._log(f"Card {self.current_card} completed successfully.")

                assert self.job is not None
                if self.current_card < self.job.num_cards:
                    self._advance_to_next_card()
                else:
                    self._finalize_job()

        elif self._phase in ("finalizing", "done", "waiting_card", "idle"):
            # no-op
            pass

    def _finalize_job(self):
        self._phase = "finalizing"
        self.progress.setValue(0)
        self._log("Finalizing ingest (simulated)...")
        self._log("Creating Resolve project (simulated)...")
        self._log("Saving logs (simulated)...")

        # After short delay, show completion UI
        QTimer.singleShot(800, self._finish_ui)

    def _finish_ui(self):
        self._phase = "done"
        self.progress.setValue(100)
        self.instruction.setText("✅ Ingest Complete")
        self._log("All cards ingested successfully. Ready for handoff.")

        # Hide continue/cancel, show finish buttons
        self.continue_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.sim_card_chk.setVisible(False)

        self.eject_btn.setVisible(True)
        self.close_btn.setVisible(True)

    def eject_clicked(self):
        # Skeleton: real ejection comes later (we’ll call Windows APIs / mountvol safely).
        QMessageBox.information(
            self,
            "Eject Drives",
            "v0 placeholder:\n\nIn v1 we’ll safely eject the Proxy SSD (and card reader volume if present)."
        )
        self._log("Eject requested (placeholder).")


# -----------------------------
# Main window & navigation
# -----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Studio Ingest Tool")
        self.setMinimumSize(420, 620)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.setup_screen = SetupScreen(on_start=self.start_ingest)
        self.ingest_screen = IngestScreen(on_done=self.close, on_back_to_setup=self.back_to_setup)

        self.stack.addWidget(self.setup_screen)
        self.stack.addWidget(self.ingest_screen)

        self.stack.setCurrentWidget(self.setup_screen)

    def start_ingest(self, job: JobConfig):
        self.ingest_screen.load_job(job)
        self.stack.setCurrentWidget(self.ingest_screen)

    def back_to_setup(self):
        self.stack.setCurrentWidget(self.setup_screen)


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
