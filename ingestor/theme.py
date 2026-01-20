from PySide6.QtWidgets import QApplication


def apply_dark_theme(app: QApplication) -> None:
    """
    App-wide dark theme via Fusion style + stylesheet.
    """
    app.setStyle("Fusion")

    dark_qss = """
    QWidget {
        background-color: #1e1e1e;
        color: #e6e6e6;
        font-size: 10pt;
    }

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
        background-color: #252526;
        border: 1px solid #3c3c3c;
        border-radius: 6px;
        padding: 6px;
        selection-background-color: #2d74da;
        selection-color: #ffffff;
    }

    QComboBox QAbstractItemView {
        background-color: #252526;
        border: 1px solid #3c3c3c;
        selection-background-color: #2d74da;
        selection-color: #ffffff;
        outline: 0;
    }

    QLineEdit:read-only {
        color: #bdbdbd;
        background-color: #202020;
        border: 1px solid #2e2e2e;
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
    """

    app.setStyleSheet(dark_qss)
