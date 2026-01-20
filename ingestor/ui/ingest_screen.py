from __future__ import annotations

from datetime import datetime, date
# import winsound

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QProgressBar, QMessageBox, QSizePolicy, QCheckBox
)

from ..models import JobConfig
from ..ui.widgets import title_label, section_label, hline
from ..services.ledger import append_session_row
from PySide6.QtWidgets import QComboBox, QMessageBox
# from ..services.drives_windows import list_removable_drives, drive_display
from ..services.drives_windows import list_windows_drives, drive_display
from ..services.drives_windows import get_drive_space

from PySide6.QtCore import QThread
from ..services.ingest_worker import IngestWorker, IngestArgs


class IngestScreen(QWidget):
    def __init__(self, on_done, on_back_to_setup, ledger_path):
        super().__init__()
        self.on_done = on_done
        self.on_back_to_setup = on_back_to_setup
        self.ledger_path = ledger_path
        self._session_started_at = None

        self.job: JobConfig | None = None
        self.current_sd_index = 0

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

        root.addWidget(section_label("Project"))
        self.project_context = QLabel("")
        self.project_context.setWordWrap(True)
        self.project_context.setStyleSheet("color: #333;")
        root.addWidget(self.project_context)

        root.addWidget(hline())

        self.instruction = QLabel("Insert camera card #1 and click CONTINUE")
        self.instruction.setAlignment(Qt.AlignCenter)
        self.instruction.setWordWrap(True)
        self.instruction.setMinimumHeight(60)
        self.instruction.setStyleSheet(
            "border: 1px solid #3c3c3c; border-radius: 8px; padding: 12px; background: #252526;"
        )
        root.addWidget(self.instruction)

        # --- Source card drive selection (v1) ---
        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("Source Card Drive"))
        self.source_combo = QComboBox()
        self.source_combo.currentIndexChanged.connect(self._update_continue_enabled)

        self.source_refresh_btn = QPushButton("Refresh")
        self.source_refresh_btn.clicked.connect(self.refresh_source_drives)

        src_row.addWidget(self.source_combo, 1)
        src_row.addWidget(self.source_refresh_btn)
        root.addLayout(src_row)

        # --- Space check (v1) ---
        self.space_card_used = QLabel("Card used: —")
        self.space_archive_free = QLabel("Archive free: —")
        self.space_proxy_free = QLabel("SSD free: —")
        self.space_status = QLabel("")
        self.space_status.setStyleSheet("color: #666;")

        root.addWidget(self.space_card_used)
        root.addWidget(self.space_archive_free)
        root.addWidget(self.space_proxy_free)
        root.addWidget(self.space_status)

        # Dev-only toggle remains (UX skeleton mode)
        # self.sim_card_chk = QCheckBox("DEV: simulate card inserted (temporary)")
        # self.sim_card_chk.stateChanged.connect(self._update_continue_enabled)
        # root.addWidget(self.sim_card_chk)

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

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        root.addWidget(self.progress)

        root.addWidget(section_label("Status"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(180)
        self.log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self.log, 1)

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

        self.current_sd_index = 1

        self._thread: QThread | None = None
        self._worker: IngestWorker | None = None

    def refresh_source_drives(self):

        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItem("Select card drive...", "")

        # drives = list_removable_drives() or []
        drives = list_windows_drives() or []
        for root, label in drives:
            self.source_combo.addItem(drive_display(root, label), root)

        self.source_combo.blockSignals(False)
        self._update_continue_enabled()

    def load_job(self, job: JobConfig):
        self.job = job
        self._session_started_at = datetime.now()
        self.current_sd_index = 0
        self._fake_progress = 0
        self._phase = "waiting_card"
        self.progress.setValue(0)
        # self.sim_card_chk.setChecked(False)

        self.eject_btn.setVisible(False)
        self.close_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.continue_btn.setVisible(True)

        self.refresh_source_drives()
        self._update_continue_enabled()

        self.project_context.setText(
            f"<b>{job.client_name}</b><br>"
            f"{job.project_name}<br><br>"
            f"<b>Mode:</b> {job.mode}<br>"
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
        self.current_sd_index += 1
        self.card_counter_lbl.setText(f"Card {self.current_sd_index} of {self.job.num_cards}")
        self.instruction.setText(f"Insert camera card #{self.current_sd_index} and click CONTINUE")
        self._phase = "waiting_card"
        self.progress.setValue(0)
        self._fake_progress = 0
        # self.sim_card_chk.setChecked(False)
        self._update_continue_enabled()
        self._log(f"Waiting for card {self.current_sd_index}...")
        self._update_continue_enabled()


    # def _update_continue_enabled(self):
    #     can_continue = (self._phase == "waiting_card") and self.sim_card_chk.isChecked()
    #     self.continue_btn.setEnabled(can_continue)


    def _update_continue_enabled(self):
        # Must be waiting for a card
        if self._phase != "waiting_card":
            self.continue_btn.setEnabled(False)
            return

        # Require source selection
        source_ok = bool(self.source_combo.currentData())

        # Run space check (updates UI labels too)
        space_ok, msg = self._check_space_ok() if source_ok else (False, "Select the source card drive.")
        self.space_status.setText(msg)

        # Keep DEV checkbox gate for now (we’ll remove later)
        # dev_ok = self.sim_card_chk.isChecked()

        self.continue_btn.setEnabled(source_ok and space_ok)

    # def _update_continue_enabled(self):
    #     # Require:
    #     # 1) we are waiting for a card
    #     # 2) a source drive is selected
    #     # (we keep the DEV checkbox for now to preserve your current flow)
    #     source_ok = bool(self.source_combo.currentData())
    #     can_continue = (self._phase == "waiting_card") and source_ok and self.sim_card_chk.isChecked()
    #     self.continue_btn.setEnabled(can_continue)

    def continue_clicked(self):
        # if self._phase != "waiting_card":
        #     return
        # if not self.sim_card_chk.isChecked():
        #     return

        self.continue_btn.setEnabled(False)
        self._phase = "copying"
        self._fake_progress = 0
        self._log(f"Detected card #{self.current_sd_index} (simulated).")
        self._log("Copying originals to ARCHIVE...")
        # self._timer.start(60)
        sd_root = self.source_combo.currentData()
        if not isinstance(sd_root, str) or not sd_root:
            self._log("Select source card drive.")
            return

        if not self.job or not self.job.archive_path or not self.job.proxy_path:
            self._log("Missing destination drives.")
            return

        base_folder = "Cactus"
        client_project = self.job.safe_project_folder()  # or build from client/project fields
        ingest_date = date.today().isoformat()  # later we can add a date picker

        args = IngestArgs(
            sd_root=sd_root,
            archive_root=self.job.archive_path,
            ssd_root=self.job.proxy_path,
            base_folder_name=base_folder,
            client_project=client_project,
            ingest_date=ingest_date,
            sd_index=self.current_sd_index,
        )

        # 2) Lock UI
        self._set_copy_running_ui(True)

        # 3) Start worker thread
        self._thread = QThread(self)
        self._worker = IngestWorker(args)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_ingest_finished)
        self._worker.failed.connect(self._on_ingest_crashed)

        # cleanup
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)

        self._thread.start()

        # 1) Gather inputs
        sd_root = self.source_combo.currentData()
        if not isinstance(sd_root, str) or not sd_root:
            self._log("Select source card drive.")
            return

        if not self.job or not self.job.archive_path or not self.job.proxy_path:
            self._log("Missing destination drives.")
            return

        base_folder = "Cactus"
        client_project = self.job.safe_project_folder()  # or build from client/project fields
        ingest_date = date.today().isoformat()  # later we can add a date picker

        args = IngestArgs(
            sd_root=sd_root,
            archive_root=self.job.archive_path,
            ssd_root=self.job.proxy_path,
            base_folder_name=base_folder,
            client_project=client_project,
            ingest_date=ingest_date,
            sd_index=self.current_sd_index,
        )

        # 2) Lock UI
        self._set_copy_running_ui(True)

        # 3) Start worker thread
        self._thread = QThread(self)
        self._worker = IngestWorker(args)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_ingest_finished)
        self._worker.failed.connect(self._on_ingest_crashed)

        # cleanup
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._clear_worker_refs)

        self._thread.start()

    def cancel_clicked(self):
        if not self.job:
            return
        reply = QMessageBox.question(
            self,
            "Cancel ingest?",
            "Canceling will leave copied files intact but incomplete.\n\nDo you want to cancel?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            # self._timer.stop()
            self._log("Ingest canceled by user.")
            # try:
            #     if self._session_started_at and self.job:
            #         append_session_row(
            #             self.ledger_path,
            #             started_at=self._session_started_at,
            #             finished_at=datetime.now(),
            #             status="CANCELED",
            #             job=self.job,
            #         )
            # except Exception:
            #     print('failed ledger')
            self.on_back_to_setup()

    def _tick(self):
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
                self._log(f"Card {self.current_sd_index} completed successfully.")

                assert self.job is not None
                if self.current_sd_index < self.job.num_cards:
                    self._advance_to_next_card()
                else:
                    self._finalize_job()

    def _finalize_job(self):
        self._phase = "finalizing"
        self.progress.setValue(0)
        self._log("Finalizing ingest (simulated)...")
        self._log("Creating Resolve project (simulated)...")
        self._log("Saving logs (simulated)...")

        QTimer.singleShot(800, self._finish_ui)

    def _finish_ui(self):
        self._phase = "done"
        self.progress.setValue(100)
        self.instruction.setText("✅ Ingest Complete")
        self._log("All cards ingested successfully. Ready for handoff.")

        # Write one row to the ingest ledger (ingest PC only)
        try:
            if self._session_started_at and self.job:
                append_session_row(
                    self.ledger_path,
                    started_at=self._session_started_at,
                    finished_at=datetime.now(),
                    status="OK",
                    job=self.job,
                )
        except Exception:
            print('ledger failed')

        self.continue_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.sim_card_chk.setVisible(False)

        self.eject_btn.setVisible(True)
        self.close_btn.setVisible(True)
        self._show_success_dialog()

    def eject_clicked(self):
        QMessageBox.information(
            self,
            "Eject Drives",
            "v0 placeholder:\n\nIn v1 we’ll safely eject the Proxy SSD (and card reader volume if present).",
        )
        self._log("Eject requested (placeholder).")

    @staticmethod
    def _fmt_bytes(n: int) -> str:
        # Friendly GB formatting
        gb = n / (1024 ** 3)
        return f"{gb:.1f} GB"

    @staticmethod
    def _required_with_margin(used_bytes: int) -> int:
        # max(2GB, 5%) safety buffer
        margin = max(int(used_bytes * 0.05), 2 * 1024**3)
        return used_bytes + margin

    def _check_space_ok(self) -> tuple[bool, str]:
        """
        Returns (ok, message). Requires BOTH archive and proxy drives to fit the card.
        """
        if not self.job:
            return False, "No job loaded."

        src = self.source_combo.currentData()
        if not isinstance(src, str) or not src:
            return False, "Select the source card drive."

        # Need destinations selected (from Setup screen)
        archive = self.job.archive_path
        proxy = self.job.proxy_path
        if not archive or not proxy:
            return False, "Missing destination drive selection."

        try:
            src_total, src_free = get_drive_space(src)
            used = max(0, src_total - src_free)
            req = self._required_with_margin(used)

            a_total, a_free = get_drive_space(archive)
            p_total, p_free = get_drive_space(proxy)

            # Update UI text
            self.space_card_used.setText(f"Card used: {self._fmt_bytes(used)} (needs ~{self._fmt_bytes(req)})")

            ok_a = a_free >= req
            ok_p = p_free >= req

            self.space_archive_free.setText(
                f"Archive free: {self._fmt_bytes(a_free)} " + ("✅" if ok_a else "❌")
            )
            self.space_proxy_free.setText(
                f"SSD free: {self._fmt_bytes(p_free)} " + ("✅" if ok_p else "❌")
            )

            if ok_a and ok_p:
                return True, "Space check OK."
            else:
                parts = []
                if not ok_a:
                    parts.append(f"Archive needs {self._fmt_bytes(req)} but has {self._fmt_bytes(a_free)}")
                if not ok_p:
                    parts.append(f"SSD needs {self._fmt_bytes(req)} but has {self._fmt_bytes(p_free)}")
                return False, " | ".join(parts)

        except Exception as e:
            # If anything fails (permissions/unready drive), block
            return False, f"Space check error: {e}"

    def _clear_worker_refs(self):
        self._worker = None
        self._thread = None

    def _set_copy_running_ui(self, running: bool):
        # Disable inputs while copying
        self.continue_btn.setEnabled(not running)
        self.source_combo.setEnabled(not running)
        self.source_refresh_btn.setEnabled(not running)

        # If you still have the DEV checkbox:
        # self.sim_card_chk.setEnabled(not running)

        # Optional: show state label
        if running:
            self.space_status.setText(f"Copying SD{self.current_sd_index} to Archive + SSD…")
        else:
            # space_status will be updated by space check / waiting state
            pass

    def _on_ingest_crashed(self, msg: str):
        self._set_copy_running_ui(False)
        self._log(f"❌ Ingest crashed: {msg}")
        # You can also pop a QMessageBox here.

    def _on_ingest_finished(self, result: dict):
        self._set_copy_running_ui(False)

        if result.get("ok"):
            self._log(f"✅ SD{self.current_sd_index} copy OK.")
            # Advance to next card or finish session
            if self.current_sd_index < self.job.num_cards:
                self.current_sd_index += 1
                self._log(f"Insert next card: SD{self.current_sd_index}")
                self._phase = "waiting_card"
                self.refresh_source_drives()
                self._update_continue_enabled()
            else:
                self._log("✅ All cards ingested.")
                # move to completion UI
                self._finish_ui()
        else:
            self._phase = "failed"
            self._log(f"❌ FAILED: {result.get('message', 'Unknown error')}")
            # Optional: show logs if provided
            a_log = result.get("archive_log")
            s_log = result.get("ssd_log")
            if a_log or s_log:
                self._log(f"Archive log: {a_log}")
                self._log(f"SSD log: {s_log}")
            # Stop session here
            # self._finish_failed_ui()

    def _show_success_dialog(self):
        # winsound.PlaySound("sound.wav", winsound.SND_FILENAME)
        QMessageBox.information(
            self,
            "Ingest Complete",
            "Ingest completed successfully!",
            QMessageBox.Ok,
        )
        self._reset_ingest_screen()
        self.on_back_to_setup()

    def _reset_ingest_screen(self):
        self._phase = "waiting_card"
        self.current_sd_index = 1

        # Reset UI elements
        self.source_combo.setCurrentIndex(-1)
        self.space_status.setText("Insert SD1 and select its drive.")

        # Re-enable inputs
        self.source_combo.setEnabled(True)
        self.source_refresh_btn.setEnabled(True)
        self.continue_btn.setEnabled(False)

        if hasattr(self, "sim_card_chk"):
            self.sim_card_chk.setChecked(False)
            self.sim_card_chk.setEnabled(True)

        # If you want to keep the same job loaded, stop here.
        # If you want a *new* job after success, this is where
        # you'd navigate back to the setup screen instead.
