from PySide6 import QtCore, QtWidgets, QtGui

class Omnibox(QtWidgets.QTextEdit):
    activated = QtCore.Signal()

    _completer: QtWidgets.QCompleter | None
    _highlighted = False

    def __init__(self):
        super().__init__()

        self._completer = None
        self._highlighted = False

        self.setPlaceholderText("type something...")


    @QtCore.Slot()
    def insertCompletion(self, completion: str):
        if self._completer.widget() != self:
            return

        text_cursor = self.textCursor()
        extra = len(completion) - len(self._completer.completionPrefix())

        text_cursor.movePosition(QtGui.QTextCursor.MoveOperation.Left)
        text_cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfWord)

        text_cursor.insertText(completion[(-1*extra):])

        self.setTextCursor(text_cursor)
        self._highlighted = False


    @QtCore.Slot()
    def highlightCompletion(self):
        self._highlighted = True

    
    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if self._completer and self._completer.popup().isVisible() and self._highlighted:
            ignore_keys = [QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Escape, QtCore.Qt.Key.Key_Tab, QtCore.Qt.Key.Key_Backtab]
            if event.key() in ignore_keys:
                event.ignore()
                return

        # Tab to auto accept first completetion
        if self._completer and self._completer.popup().isVisible() and event.key() == QtCore.Qt.Key.Key_Tab:
            self.insertCompletion(self._completer.currentCompletion())
            self._completer.popup().hide()
            return

        # Keys that need to trigger something somewhere else
        parent_trigger_keys = [QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Escape]
        if event.key() in parent_trigger_keys:
            self.activated.emit()
            return

        # Ctrl space to force trigger
        is_force_open = (event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier and event.key() == QtCore.Qt.Key.Key_Space)
        if self._completer and is_force_open:
            self._completer.complete()
            return

        is_shortcut = (event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier and event.key() == QtCore.Qt.Key.Key_E)

        if not self._completer or not is_shortcut:
            super().keyPressEvent(event)

        ctrl_or_shift = (event.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier) or (event.modifiers() == QtCore.Qt.KeyboardModifier.ShiftModifier)

        if not self._completer or (ctrl_or_shift and not event.text()):
            return

        has_modifier = (event.modifiers() != QtCore.Qt.KeyboardModifier.NoModifier) and (not ctrl_or_shift)

        if self._completer:
            completion_prefix = self.textUnderCursor()

            if not is_shortcut and (has_modifier or not event.text() or len(completion_prefix) < 1 or completion_prefix[-1] in "~!@#$%^&*()_+{}|:\"<>?,./;'[]\\="):
                self._completer.popup().hide()
                return

            if completion_prefix != self._completer.completionPrefix():
                self._completer.setCompletionPrefix(completion_prefix)

            self._completer.complete()


    def completer(self) -> QtWidgets.QCompleter:
        return self._completer


    def setCompleter(self, completer: QtWidgets.QCompleter):
        if self._completer:
            self._completer.disconnect(self)

        self._completer = completer

        if self._completer:
            self._completer.setWidget(self)
            self._completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
            self._completer.setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
            #self._completer.setFilterMode(QtCore.Qt.MatchFlag.MatchContains)

            self._completer.activated.connect(self.insertCompletion)
            self._completer.highlighted.connect(self.highlightCompletion)


    def focusInEvent(self, event: QtGui.QFocusEvent):
        if self._completer:
            self._completer.setWidget(self)

        super().focusInEvent(event)


    def textUnderCursor(self) -> str:
        text_cursor = self.textCursor()
        text_cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)
        return text_cursor.selectedText()
