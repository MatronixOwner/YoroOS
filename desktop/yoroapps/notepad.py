"""Yoro Блокнот — simple text editor."""

import os
import sys

from PyQt6.QtCore import QIODevice, QSaveFile
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QApplication, QFileDialog, QMainWindow,
                             QMessageBox, QPlainTextEdit)

from yoroapps import style


class Notepad(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = None
        self.setWindowTitle("Yoro Блокнот")
        self.resize(760, 520)

        self.editor = QPlainTextEdit()
        self.editor.setStyleSheet("font-family: 'Noto Sans Mono', monospace;")
        self.setCentralWidget(self.editor)
        self.editor.textChanged.connect(self._update_status)

        toolbar = self.addToolBar("Файл")
        for text, slot in (("Новый", self.new_file), ("Открыть…", self.open_file),
                           ("Сохранить", self.save_file),
                           ("Сохранить как…", self.save_file_as)):
            action = QAction(text, self)
            action.triggered.connect(slot)
            toolbar.addAction(action)

        self.statusBar().showMessage("Готов")

    def _update_status(self):
        text = self.editor.toPlainText()
        words = len(text.split())
        self.statusBar().showMessage(
            f"Символов: {len(text)}   Слов: {words}")

    def _maybe_save(self):
        if not self.editor.document().isModified():
            return True
        answer = QMessageBox.question(
            self, "Yoro Блокнот", "Сохранить изменения?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            return self.save_file()
        return answer == QMessageBox.StandardButton.Discard

    def new_file(self):
        if self._maybe_save():
            self.editor.clear()
            self.editor.document().setModified(False)
            self.path = None
            self.setWindowTitle("Yoro Блокнот")

    def open_file(self):
        if not self._maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Открыть файл")
        if path:
            self.load(path)

    def load(self, path):
        try:
            with open(path, encoding="utf-8-sig") as f:
                self.editor.setPlainText(f.read())
        except (OSError, UnicodeError) as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))
            return
        self.path = path
        self.editor.document().setModified(False)
        self.setWindowTitle(f"Yoro Блокнот — {os.path.basename(path)}")

    def save_file(self):
        if self.path is None:
            return self.save_file_as()
        return self._save_to(self.path)

    def _save_to(self, path):
        # Commit the new file atomically; failed saves keep document state.
        target = QSaveFile(path)
        if not target.open(QIODevice.OpenModeFlag.WriteOnly):
            QMessageBox.critical(self, "Ошибка сохранения", target.errorString())
            return False
        data = self.editor.toPlainText().encode("utf-8")
        if target.write(data) != len(data) or not target.commit():
            QMessageBox.critical(self, "Ошибка сохранения", target.errorString())
            return False
        self.path = path
        self.editor.document().setModified(False)
        self.setWindowTitle(f"Yoro Блокнот — {os.path.basename(path)}")
        self.statusBar().showMessage(f"Сохранено: {path}")
        return True

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл")
        return self._save_to(path) if path else False

    def closeEvent(self, event):
        if self._maybe_save():
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    style.setup_app(app)
    app.setStyleSheet(style.get_stylesheet())
    window = Notepad()
    if len(sys.argv) > 1:
        window.load(sys.argv[1])
    style.enable_glass(app, window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
