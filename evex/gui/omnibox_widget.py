import time
import sqlite3
import webbrowser
from PySide6 import QtCore, QtWidgets, QtGui

import requests

from evex.commands import COMMANDS, generate_command_completions
from evex.esi import set_destination
from evex.gui.completers import SystemCompleter
from evex.gui.omnibox import Omnibox
from evex.models import EsiCharacter, EsiCharacterListModel
from evex.sde import get_solar_system_id

class OmniboxWidget(QtWidgets.QWidget):
    activated = QtCore.Signal(str)


    def __init__(self):
        super().__init__()

        self.esi_state = None
        self.esi_characters: dict[int, EsiCharacter] = {}

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)

        self.activated.connect(self.show_and_focus)

        self.resize(1024, 64)
        
        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(8)

        self.character_context_box = QtWidgets.QComboBox()
        self.character_context_box.setStyleSheet("QComboBox { color: #969696; background-color: #2d2d2d; }")
        self.character_context_box.addItems(["N/A"])
        self.character_context_box.setFont(QtGui.QFont("Arial", 12))
        self.character_context_box.setFixedWidth(192)
        self.character_context_box.setFixedHeight(64)
        self.character_context_box.currentIndexChanged.connect(self.character_context_changed)
        layout.addWidget(self.character_context_box)
        
        self.textbox = Omnibox()
        self.textbox.setFont(QtGui.QFont("Arial", 32))
        self.textbox.setCompleter(SystemCompleter())
        self.textbox.completer().setCommands(generate_command_completions())
        self.textbox.textChanged.connect(self.update_completer)
        self.textbox.activated.connect(self.exec_command)

        self.cancel_shortcut = QtGui.QShortcut(QtGui.QKeySequence.Cancel, self)
        self.cancel_shortcut.activated.connect(self.cancel_command)

        layout.addWidget(self.textbox)


    def setEsiCharacters(self, esi_characters: dict[int, EsiCharacter]):

        self.esi_characters = esi_characters
        self.character_context_box.setModel(EsiCharacterListModel(list(esi_characters.values())))


    @QtCore.Slot()
    def character_context_changed(self, index):
        self.esi_state = self.character_context_box.currentData()


    @QtCore.Slot()
    def hide_and_reset(self):
        self.hide()
        self.textbox.clear()


    @QtCore.Slot()
    def show_and_focus(self, character_name):
        if character_name:
           index = self.character_context_box.findData(character_name, QtCore.Qt.ItemDataRole.DisplayRole)

           if index >= 0:
               self.character_context_box.setCurrentIndex(index)

        self.show()
        self.activateWindow()
        self.textbox.setFocus()


    @QtCore.Slot()
    def update_completer(self):
        text = self.textbox.toPlainText()

        for command in COMMANDS:
            if command.match(text):
                self.textbox.completer().setSystems()
                return

        self.textbox.completer().setCommands(generate_command_completions())


    @QtCore.Slot()
    def exec_command(self):
        text = self.textbox.toPlainText().strip()

        for command in COMMANDS:
            if command.match(text):
                modifier, args = command.parse(text)
                command.action(self.esi_state, modifier, args)
                break

        self.hide_and_reset()


    @QtCore.Slot()
    def cancel_command(self):
        self.hide_and_reset()
