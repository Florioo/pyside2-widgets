from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication, QMainWindow, QDockWidget, QListWidget, QLabel,QPushButton,QWidget,QTextEdit
from PySide2.QtGui import QFont, QColor
from PySide2.QtCore import Signal, QObject, Slot, Property

import logging
from functools import cached_property

class QDockableLoggingWidget(QDockWidget):
    def __init__(self,parent=None,font=None):
        super().__init__("Python Log",parent,objectName="python_logger")
        


        # Configure the text edit
        self.text_edit = QTextEdit()
        if font is not None:
            self.text_edit.setFont(font)
            
        self.text_edit.setAutoFillBackground(False)
        self.text_edit.setStyleSheet(u"QTextEdit {background-color:rgb(30, 30, 30);\ncolor: white }")
        self.text_edit.setReadOnly(True)

        self.log_handler = LogHandler()
        self.log_handler.setFormatter(ConsoleFormatter())
        self.log_handler.data_signal.connect(self.append_text_to_output)
        
        # Set central widget
        self.setWidget(self.text_edit)
        
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
        
        