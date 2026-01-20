from __future__ import annotations

from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal, Slot

from .ingest_engine import ingest_one_card_parallel


@dataclass(frozen=True)
class IngestArgs:
    sd_root: str
    archive_root: str
    ssd_root: str
    base_folder_name: str
    client_project: str
    ingest_date: str
    sd_index: int


class IngestWorker(QObject):
    finished = Signal(dict)   # emits result dict from ingest_one_card_parallel
    failed = Signal(str)      # emits unexpected exception message

    def __init__(self, args: IngestArgs):
        super().__init__()
        self.args = args

    @Slot()
    def run(self):
        try:
            result = ingest_one_card_parallel(
                sd_root=self.args.sd_root,
                archive_root=self.args.archive_root,
                ssd_root=self.args.ssd_root,
                base_folder_name=self.args.base_folder_name,
                client_project=self.args.client_project,
                ingest_date=self.args.ingest_date,
                sd_index=self.args.sd_index,
            )
            self.finished.emit(result)
        except Exception as e:
            self.failed.emit(str(e))
