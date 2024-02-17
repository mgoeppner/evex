from pydantic import BaseModel
from PySide6 import QtCore, QtGui


class EsiCharacter(BaseModel):
    id:  int
    name: str
    access_token: str
    expires_at: int
    refresh_token: str


class EsiCharacterListModel(QtCore.QAbstractListModel):
    def __init__(self, esi_characters = []):
        self.esi_characters = esi_characters

        super().__init__()


    def data(self, index, role):
        esi_character = self.esi_characters[index.row()]

        if role == QtCore.Qt.ItemDataRole.UserRole:
            return esi_character

        if role == QtCore.Qt.ItemDataRole.DisplayRole:
            text = esi_character.name
            return text

        return None

    def rowCount(self, index):
        return len(self.esi_characters)

