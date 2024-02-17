import sqlite3
from PySide6 import QtCore, QtWidgets

from evex.sde import get_solar_system_names
from evex.utils import get_resource

class SystemCompleter(QtWidgets.QCompleter):
    def __init__(self, parent=None):

        self.system_names = get_solar_system_names()
        self.system_name_model = QtCore.QStringListModel(self.system_names)

        super().__init__(parent)
        self.setModel(self.system_name_model)


    def setCommands(self, commands: list[str]):
        model = QtCore.QStringListModel(commands)
        self.setModel(model)


    def setSystems(self):
        self.setModel(self.system_name_model)


    def setCharacters(self, character_names: list[str]):
        model = QtCore.QStringListModel(character_names)
        self.setModel(model)
