# -*- coding: utf-8 -*-
"""
Simple GUI for the data resampler.

Lets the user pick an input CSV, configure the resampling arguments and
export the result to the same folder as the input file.

Launch with `python -m data_resampler` (or `data-resampler` once installed).
"""

import sys
from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .core import DEFAULT_AGGREGATION, resample_csv


INTERVALS = ["1min", "5min", "10min", "15min", "30min", "1h", "1D"]
PER_COLUMN = "per column (default rules)"
AGGREGATIONS = [PER_COLUMN, "mean", "sum", "min", "max", "median", "first", "last"]
DEFAULT_DATE_FORMAT = "%d-%m-%y %H:%M:%S"


class ResamplerWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Data Resampler")
        self.resize(560, 380)

        # --- Input file ---
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Select a CSV file...")
        self.input_edit.editingFinished.connect(self._on_input_changed)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_input)
        input_row = QHBoxLayout()
        input_row.addWidget(self.input_edit)
        input_row.addWidget(browse_btn)

        # --- Resampling arguments ---
        self.interval_combo = QComboBox()
        self.interval_combo.setEditable(True)  # allow custom values, e.g. "2h"
        self.interval_combo.addItems(INTERVALS)
        self.interval_combo.setCurrentText("15min")
        self.interval_combo.currentTextChanged.connect(self._update_output_name)

        self.aggregation_combo = QComboBox()
        self.aggregation_combo.addItems(AGGREGATIONS)

        self.timestamp_combo = QComboBox()
        self.timestamp_combo.setEditable(True)  # filled from the file header
        self.timestamp_combo.setCurrentText("Timestamp")

        self.date_format_edit = QLineEdit(DEFAULT_DATE_FORMAT)
        self.auto_date_check = QCheckBox("Detect automatically")
        self.auto_date_check.toggled.connect(
            lambda checked: self.date_format_edit.setEnabled(not checked)
        )
        date_row = QHBoxLayout()
        date_row.addWidget(self.date_format_edit)
        date_row.addWidget(self.auto_date_check)

        # --- Output file name (saved next to the input file) ---
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Output file name")

        form = QFormLayout()
        form.addRow("Input file:", input_row)
        form.addRow("Interval:", self.interval_combo)
        form.addRow("Aggregation:", self.aggregation_combo)
        form.addRow("Timestamp column:", self.timestamp_combo)
        form.addRow("Date format:", date_row)
        form.addRow("Output file name:", self.output_edit)

        # --- Run button and log ---
        self.run_btn = QPushButton("Resample && Export")
        self.run_btn.clicked.connect(self._run)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.run_btn)
        layout.addWidget(self.log)

    # ------------------------------------------------------------------ #
    def _browse_input(self) -> None:
        start_dir = str(Path(self.input_edit.text()).parent) if self.input_edit.text() else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select input CSV", start_dir, "CSV files (*.csv);;All files (*)"
        )
        if path:
            self.input_edit.setText(path)
            self._on_input_changed()

    def _on_input_changed(self) -> None:
        """Read the header of the chosen file to offer its column names."""
        path = Path(self.input_edit.text())
        if not path.is_file():
            return
        try:
            columns = list(pd.read_csv(path, nrows=0).columns)
        except Exception as exc:  # noqa: BLE001 - show any read problem to the user
            self._log(f"Could not read header: {exc}")
            return

        current = self.timestamp_combo.currentText()
        self.timestamp_combo.clear()
        self.timestamp_combo.addItems(columns)
        if current in columns:
            self.timestamp_combo.setCurrentText(current)
        self._log(f"Loaded columns: {', '.join(columns)}")
        self._update_output_name()

    def _update_output_name(self) -> None:
        path = Path(self.input_edit.text())
        if path.suffix:
            self.output_edit.setText(f"{path.stem}_{self.interval_combo.currentText()}.csv")

    def _run(self) -> None:
        input_path = Path(self.input_edit.text())
        if not input_path.is_file():
            QMessageBox.warning(self, "No input file", "Please select a valid input CSV file.")
            return

        output_name = self.output_edit.text().strip() or f"{input_path.stem}_resampled.csv"
        output_path = input_path.parent / output_name

        if output_path.exists():
            answer = QMessageBox.question(
                self, "Overwrite?", f"{output_path.name} already exists. Overwrite it?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        aggregation = self.aggregation_combo.currentText()
        if aggregation == PER_COLUMN:
            aggregation = DEFAULT_AGGREGATION

        date_format = None if self.auto_date_check.isChecked() else self.date_format_edit.text()

        self._log(f"Resampling {input_path.name} to {self.interval_combo.currentText()}...")
        try:
            df = resample_csv(
                input_file=input_path,
                output_file=output_path,
                interval=self.interval_combo.currentText(),
                timestamp_column=self.timestamp_combo.currentText(),
                date_format=date_format or None,
                aggregation=aggregation,
            )
        except Exception as exc:  # noqa: BLE001 - show any error to the user
            self._log(f"Error: {exc}")
            QMessageBox.critical(self, "Resampling failed", str(exc))
            return

        self._log(f"Done: {len(df)} rows written to {output_path}")

    def _log(self, message: str) -> None:
        self.log.appendPlainText(message)


def main() -> None:
    app = QApplication(sys.argv)
    window = ResamplerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
