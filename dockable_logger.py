import logging
import os
import time
from functools import cached_property
from logging.handlers import RotatingFileHandler

from pydantic import BaseModel
from qt_settings import QGenericSettingsWidget
from qtpy.QtCore import QObject, Signal
from qtpy.QtGui import QAction, QColor
from qtpy.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QStyle,
    QTextEdit,
    QWidget,
)


class QDockableLoggingWidget(QDockWidget):
    def __init__(self, parameters: "QLogConfigWidget", font=None):
        super().__init__(parent=None, objectName="python_logger")  # type: ignore
        # Set title
        self.setWindowTitle("Python Logger")

        self.parameters = parameters.data

        # Configure the text edit
        self.text_edit = QTextEdit()
        self.text_edit.setAutoFillBackground(False)
        self.text_edit.setStyleSheet("QTextEdit {background-color:rgb(30, 30, 30);\ncolor: white }")
        self.text_edit.setReadOnly(True)
        self.text_edit.document().setMaximumBlockCount(self.parameters.max_log_lines)

        if font is not None:
            self.text_edit.setFont(font)

        # Create the log handler
        self.log_handler = LogHandler()
        self.log_handler.setFormatter(ConsoleFormatter())
        self.log_handler.data_signal.connect(self.append_text_to_output)

        if self.parameters.enable_file_logging:
            # create a rotating log file handler
            filename = f"python_log_{time.strftime('%Y%m%d-%H%M%S')}.log"
            self.log_file_handler = RotatingFileHandler(
                filename=os.path.join(self.parameters.log_path, filename), maxBytes=5 * 1024 * 1024, backupCount=30
            )

            self.log_file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            self.log_file_handler.setLevel(logging.DEBUG)

        # Set central widget
        self.setWidget(self.text_edit)

    def register_logger(self, logger: logging.Logger):
        logger.addHandler(self.log_handler)
        if self.parameters.enable_file_logging:
            logger.addHandler(self.log_file_handler)

    def append_text_to_output(self, text):
        """Append text to the output text box"""
        self.text_edit.append(text)


class ConsoleFormatter(logging.Formatter):
    FORMATS = {
        logging.ERROR: ("[ERR ]", QColor(255, 100, 100)),
        logging.DEBUG: ("[DBG ]", QColor(200, 200, 200)),
        logging.INFO: ("[INFO]", QColor(100, 250, 100)),
        logging.WARNING: ("[WARN]", QColor(255, 255, 50)),
        logging.CRITICAL: ("[CRIT]", QColor(255, 0, 0)),
    }

    def format(self, record):
        """Format logs"""
        opt = ConsoleFormatter.FORMATS.get(record.levelno)

        if opt:
            prefix, color = opt
            color = QColor(color).name()
        else:
            prefix, color = "[????]", QColor(255, 255, 255).name()

        self._style._fmt = f'<font color="{QColor(color).name()}">{prefix} (%(name)s) </font> %(message)s'

        res = logging.Formatter.format(self, record)

        # Replace newlines with <br>x
        res = res.replace("\n", "<br>")

        return res


class LogHandler(logging.Handler, QObject):
    # This is need to transition whatever thread that called to the QT thread
    data_signal = Signal(str)

    class _brigde(QObject):
        log = Signal(str)

    def __init__(self):
        super().__init__()
        self.data_signal = self.bridge.log

    @cached_property
    def bridge(self):
        return self._brigde()

    def emit(self, record):
        msg = self.format(record)
        self.bridge.log.emit(msg)


class QLogConfigWidget(QGenericSettingsWidget):
    class Model(BaseModel):
        max_log_lines: int = 1000
        log_path: str = os.path.expanduser("~/Desktop/")
        enable_file_logging: bool = False

    def __init__(self) -> None:
        super().__init__()

        # Create the inputs
        self.max_log_lines_input = QSpinBox()
        self.max_log_lines_input.setValue(1000)
        self.max_log_lines_input.setMinimum(100)
        self.max_log_lines_input.setMaximum(10000)

        # Enable logging to file
        self.enable_file_logging_input = QCheckBox("Enable file logging")

        self.log_path_input = QLineEdit()
        select_folder_action = QAction(self)
        select_folder_action.triggered.connect(self.query_folder)
        select_folder_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.log_path_input.addAction(select_folder_action, QLineEdit.ActionPosition.TrailingPosition)

        # Set the layout
        self._layout = QFormLayout()

        # Add message to restart to apply changes
        self._layout.addRow("Restart to apply changes", QWidget())
        self._layout.addRow("Max Lines to show", self.max_log_lines_input)
        self._layout.addWidget(self.enable_file_logging_input)
        self._layout.addRow("Log Path", self.log_path_input)
        self.setLayout(self._layout)

        # Save the settings when the inputs change
        self.max_log_lines_input.valueChanged.connect(self._on_value_changed)
        self.log_path_input.textChanged.connect(self._on_value_changed)
        self.enable_file_logging_input.stateChanged.connect(self._on_value_changed)

    def query_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", self.log_path_input.text())

        if path is None or path == "":
            return

        self.log_path_input.setText(path)

    @property
    def data(self) -> Model:
        return self.Model(
            max_log_lines=self.max_log_lines_input.value(),
            log_path=self.log_path_input.text(),
            enable_file_logging=self.enable_file_logging_input.isChecked(),
        )

    @data.setter
    def data(self, data: Model):
        self.max_log_lines_input.setValue(data.max_log_lines)
        self.log_path_input.setText(data.log_path)
        self.enable_file_logging_input.setChecked(data.enable_file_logging)
