import asyncio
import ctypes
import os
import sys
from pathlib import Path

from pynput import keyboard
from qasync import asyncSlot, QApplication, QEventLoop

from PySide6 import  QtCore, QtWidgets, QtGui

from evex.gui.omnibox_widget import OmniboxWidget
from evex.esi import login as esi_login
from evex.models import EsiCharacter
from evex.settings import load_settings, save_settings, Settings
from evex.utils import get_resource


class MainWindow(QtWidgets.QMainWindow):
    omnibox_activated = QtCore.Signal(str)

    def __init__(self, settings: Settings=None):
        super().__init__()

        self.settings = settings

        self.omnibox = OmniboxWidget()
        self.omnibox_activated.connect(self.trigger_omnibox)

        self.tray_menu = QtWidgets.QMenu()
        
        #self.tray_menu_show = QtGui.QAction("Show/Hide Main Window")
        #self.tray_menu_show.triggered.connect(self.toggle)
        #self.tray_menu.addAction(self.tray_menu_show)

        self.tray_menu_login = QtGui.QAction("Login with EVE SSO...")
        self.tray_menu_login.triggered.connect(self.login)
        self.tray_menu.addAction(self.tray_menu_login)

        self.tray_menu_characters = QtWidgets.QMenu("Characters...")

        self.tray_menu.addMenu(self.tray_menu_characters)

        self.tray_menu_quit = QtGui.QAction("Quit")
        self.tray_menu.addAction(self.tray_menu_quit)

        if self.settings and len(self.settings.characters):
            character_names = list(map(lambda c: c.name, self.settings.characters.values()))
            self.omnibox.setEsiCharacters(self.settings.characters)

            self.add_characters_to_tray(character_names)


    def add_characters_to_tray(self, character_names: list[str]):
        self.character_actions = []
        self.tray_menu_characters.clear()

        for name in character_names:
            action = QtGui.QAction(name)
            action.setDisabled(True)
            self.character_actions.append(action)
            self.tray_menu_characters.addAction(action)


    @asyncSlot()
    async def login(self):
        esi_character = await esi_login()
        self.settings.characters[esi_character.id] = esi_character

        save_settings(self.settings)

        character_names = list(map(lambda c: c.name, self.settings.characters.values()))
        self.omnibox.setEsiCharacters(self.settings.characters)

        self.add_characters_to_tray(character_names)


    @QtCore.Slot()
    def toggle(self):
        self.setVisible(not self.isVisible())


    @QtCore.Slot()
    def trigger_omnibox(self, character_name):
        self.omnibox.activated.emit(character_name)


if __name__ == "__main__":
    app_id = u"com.mgoeppner.evex"

    if os.name == "nt":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    app = QApplication([])

    icon_path = get_resource("icon.png")
    icon = QtGui.QIcon(icon_path)

    settings_path = Path.joinpath(Path.home(), ".config", "evex")
    if not settings_path.exists():
        settings_path.mkdir(parents=True, exist_ok=True)

    settings = load_settings()

    app.setApplicationName("evex")
    app.setWindowIcon(icon)
    app.setStyle("fusion")

    window = MainWindow(settings)
    window.setWindowTitle("evex")
    window.setWindowIcon(icon)
    window.resize(800, 600)

    window.tray_menu_quit.triggered.connect(app.quit)

    tray = QtWidgets.QSystemTrayIcon()
    tray.setContextMenu(window.tray_menu)
    tray.setIcon(icon)
    tray.setVisible(True)

    def on_activate():
        character_name: str | None = None

        if os.name == "nt":
            GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
            GetWindowText = ctypes.windll.user32.GetWindowTextW
            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW

            hwnd = GetForegroundWindow()
            title_len = GetWindowTextLength(hwnd)
            title_buff = ctypes.create_unicode_buffer(title_len + 1)
            GetWindowText(hwnd, title_buff, title_len + 1)

            title = title_buff.value

            if title.startswith("EVE - "):
                character_name = title.removeprefix("EVE - ").strip()


        window.omnibox_activated.emit(character_name)


    listener = keyboard.GlobalHotKeys({settings.hotkeys.trigger: on_activate})
    listener.start()

    loop = QEventLoop(app)

    asyncio.set_event_loop(loop)

    with loop:
        loop.run_forever()

    #sys.exit(app.exec())
