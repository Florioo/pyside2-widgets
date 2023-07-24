from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget, QListWidget, QLabel,QPushButton,QWidget,QTextEdit,QSpinBox,QFormLayout, QFileDialog,QLineEdit,QStyle,QCheckBox
from PySide6.QtGui import QFont, QColor,QAction
from PySide6.QtCore import Signal, QObject, Slot, QSettings

import logging
from logging.handlers import RotatingFileHandler


from functools import cached_property
from typing import Dict
import os
import time

class QDockableLoggingWidget(QDockWidget):
    def __init__(self, settings: QSettings, font=None):
        super().__init__("Python Log",objectName="python_logger")
        
        self.parameters = ConfigWidget(settings)
        self.parameters.load()

        # Configure the text edit
        self.text_edit = QTextEdit()            
        self.text_edit.setAutoFillBackground(False)
        self.text_edit.setStyleSheet(u"QTextEdit {background-color:rgb(30, 30, 30);\ncolor: white }")
        self.text_edit.setReadOnly(True)
        self.text_edit.document().setMaximumBlockCount(self.parameters.max_log_lines)
        
        if font is not None:
            self.text_edit.setFont(font)
        
        #Create the log handler
        self.log_handler = LogHandler()
        self.log_handler.setFormatter(ConsoleFormatter())
        self.log_handler.data_signal.connect(self.append_text_to_output)
        
        if self.parameters.enable_file_logging:
            #create a rotating log file handler
            filename = f"python_log_{time.strftime('%Y%m%d-%H%M%S')}.log"
            self.log_file_handler = RotatingFileHandler(filename=os.path.join(self.parameters.log_path,filename),
                                                        maxBytes=5*1024*1024,
                                                        backupCount=30)

            self.log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.log_file_handler.setLevel(logging.DEBUG)

        # Set central widget
        self.setWidget(self.text_edit)

    def register_logger(self, logger: logging.Logger):
        logger.addHandler(self.log_handler)
        if self.parameters.enable_file_logging:
            logger.addHandler(self.log_file_handler)
                    
    def append_text_to_output(self, text):
        """Append text to the output text box
        """
        self.text_edit.append(text) 
         
        
class ConsoleFormatter(logging.Formatter):
    FORMATS = {
        logging.ERROR:   ("[ERR ]", QColor(255, 100, 100)),
        logging.DEBUG:   ("[DBG ]", QColor(200, 200, 200)),
        logging.INFO:    ("[INFO]", QColor(100, 250, 100)),
        logging.WARNING: ("[WARN]", QColor(255, 255,  50)),
        logging.CRITICAL:("[CRIT]", QColor(255,   0,   0)),
    }
        
    def format( self, record ):
        """Format logs"""
        opt = ConsoleFormatter.FORMATS.get(record.levelno)
        
        if opt:
            prefix, color = opt
            color = QColor(color).name()
        else:
            prefix, color = "[????]", QColor(255, 255, 255).name()
     
        self._style._fmt = f"<font color=\"{QColor(color).name()}\">{prefix} (%(name)s) </font> %(message)s"

        res = logging.Formatter.format( self, record )
        
        # Replace newlines with <br>x
        res = res.replace("\n", "<br>")
        
        return res
    
class LogHandler(logging.Handler):
    # This is need to transition whatever thread that called to the QT thread
    data_signal: Signal
    
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
        
class ConfigWidget(QWidget):
    
    STORAGE_NAME = "dockable_logger_config"
    
    
    DEFAULT_MAX_LOG_LINES = 1000
    DEFAULT_LOG_PATH = os.path.expanduser("~/Desktop/")
    DEFAULT_ENABLE_FILE_LOGGING = False
    
    changed = Signal()
    
    def __init__(self, settings: QSettings) -> None:
        super().__init__()
        
        self.settings = settings
        
        # Create the inputs
        self.max_log_lines_input = QSpinBox()
        self.max_log_lines_input.setMinimum(1)
        self.max_log_lines_input.setMaximum(10000)
        
        # Enable logging to file
        self.enable_file_logging_input = QCheckBox("Enable file logging")
        
        
        self.log_path_input = QLineEdit()
        select_folder_action = QAction(self)
        select_folder_action.triggered.connect(self.query_folder)
        select_folder_action.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.log_path_input.addAction(select_folder_action, QLineEdit.TrailingPosition)

        
        # Set the layout
        self.layout = QFormLayout()
        self.layout.addRow("Max Lines to show", self.max_log_lines_input)
        self.layout.addWidget(self.enable_file_logging_input)
        self.layout.addRow("Log Path", self.log_path_input)
        self.setLayout(self.layout)

        # Save the settings when the inputs change
        self.max_log_lines_input.valueChanged.connect(self.save)
        self.log_path_input.textChanged.connect(self.save)
        self.enable_file_logging_input.stateChanged.connect(self.save)
        
        # Load the settings at startup
        self.load()
    
 
    @property
    def max_log_lines(self) -> int:
        return self.max_log_lines_input.value()
    @property
    def log_path(self) -> str:
        return self.log_path_input.text()
    @property
    def enable_file_logging(self) -> bool:
        return self.enable_file_logging_input.isChecked()
    
    def query_folder(self):
        path =  QFileDialog.getExistingDirectory(self, "Select Directory", self.log_path)
        
        if path is  None or path == "":
            return
        
        self.log_path_input.setText(path)
        self.save()
                          
    def to_dict(self):
        return {
            "max_log_lines": self.max_log_lines,
            "log_path": self.log_path,
            "enable_file_logging": self.enable_file_logging
        }
        
    def from_dict(self, config: Dict):
        self.max_log_lines_input.setValue(config.get("max_log_lines", self.DEFAULT_MAX_LOG_LINES))
        self.log_path_input.setText(config.get("log_path", self.DEFAULT_LOG_PATH))
        self.enable_file_logging_input.setChecked(config.get("enable_file_logging", self.DEFAULT_ENABLE_FILE_LOGGING))

    def save(self):
        self.settings.setValue(self.STORAGE_NAME, self.to_dict())
        self.changed.emit()
        
    def load(self):
        config = self.settings.value(self.STORAGE_NAME, {})
        self.from_dict(config)
        
    
