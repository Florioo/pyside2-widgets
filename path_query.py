import os
from enum import Enum

from PySide2.QtCore import QSettings
from PySide2.QtWidgets import QFileDialog, QWidget


class PathQuery:
    class LoadSaveEnum(Enum):
        LOAD = 1
        SAVE = 2

    def __init__(self, parent: QWidget, settings: QSettings, save_name: str, supported_types: str):
        self._parent = parent
        self.settings = settings
        self.save_name = save_name
        self.supported_types = supported_types

    def get_last_folder(self) -> str:
        last_folder = self.settings.value(self.save_name, "", str)

        if not isinstance(last_folder, str):
            last_folder = ""

        return last_folder

    def store_last_folder(self, folder: str) -> None:
        self.settings.setValue(self.save_name, folder)

    def get_path(self, type: LoadSaveEnum) -> str | None:
        last_folder = self.get_last_folder()

        if type == self.LoadSaveEnum.LOAD:
            filePath, _ = QFileDialog.getOpenFileName(
                parent=self._parent,
                caption="Open File",
                dir=last_folder,
                filter=self.supported_types,
                options=QFileDialog.Options(),
            )

        elif type == self.LoadSaveEnum.SAVE:
            filePath, _ = QFileDialog.getSaveFileName(
                parent=self._parent,
                caption="Save File",
                dir=last_folder,
                filter=self.supported_types,
                options=QFileDialog.Options(),
            )
        else:
            raise NotImplementedError

        if not filePath:
            return

        filePath: str

        # Remember the folder for next time
        self.store_last_folder(os.path.dirname(filePath))

        return filePath
