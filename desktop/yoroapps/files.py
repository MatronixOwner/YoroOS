"""Yoro Файлы — file manager."""

import os
import sys

from PyQt6.QtCore import QDir, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFileSystemModel
from PyQt6.QtWidgets import (QApplication, QHBoxLayout,
                             QLineEdit, QListWidget, QMainWindow, QMessageBox,
                             QPushButton, QSplitter, QTreeView, QVBoxLayout,
                             QWidget)

from PyQt6.QtCore import Qt

from yoroapps import style, trashutil

PLACES = [
    ("Домашний каталог", os.path.expanduser("~")),
    ("Документы", os.path.expanduser("~/Documents")),
    ("Загрузки", os.path.expanduser("~/Downloads")),
    ("Изображения", os.path.expanduser("~/Pictures")),
    ("Музыка", os.path.expanduser("~/Music")),
    ("Видео", os.path.expanduser("~/Videos")),
    ("Корень диска", "/"),
]


class Files(QMainWindow):
    def __init__(self, start=None):
        super().__init__()
        self.setWindowTitle("Yoro Файлы")
        self.resize(920, 560)

        self.model = QFileSystemModel()
        self.model.setRootPath("")
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.view = QTreeView()
        self.view.setModel(self.model)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.view.doubleClicked.connect(self._on_double_click)
        for col, width in ((0, 320), (1, 100), (2, 110), (3, 150)):
            self.view.setColumnWidth(col, width)

        self.places = QListWidget()
        for label, _path in PLACES:
            self.places.addItem(label)
        self.places.currentRowChanged.connect(self._place_selected)

        splitter = QSplitter()
        splitter.addWidget(self.places)
        splitter.addWidget(self.view)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([190, 730])

        self.address = QLineEdit()
        self.address.returnPressed.connect(
            lambda: self.open_path(self.address.text()))

        back = QPushButton("←")
        back.clicked.connect(lambda: self.open_path(
            os.path.dirname(self.current_path.rstrip("/")) or "/"))
        up_label = QPushButton("Вверх")
        up_label.clicked.connect(back.click)

        delete_btn = QPushButton("В корзину")
        delete_btn.clicked.connect(self._delete_selected)

        hidden_btn = QPushButton("Скрытые")
        hidden_btn.setCheckable(True)
        hidden_btn.toggled.connect(self._toggle_hidden)

        top = QHBoxLayout()
        top.addWidget(back)
        top.addWidget(self.address, 1)
        top.addWidget(hidden_btn)
        top.addWidget(delete_btn)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(splitter)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        delete_action = QAction("В корзину", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self._delete_selected)
        self.addAction(delete_action)

        self.open_path(start or os.path.expanduser("~"))

    @property
    def current_path(self):
        return self.model.filePath(self.view.rootIndex())

    def open_path(self, path):
        path = os.path.expanduser(path)
        if os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            return
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Yoro Файлы", f"Нет такой папки: {path}")
            return
        self.view.setRootIndex(self.model.index(path))
        self.address.setText(path)
        self.setWindowTitle(f"Yoro Файлы — {path}")
        self.statusBar().showMessage(path)

    def _place_selected(self, row):
        if 0 <= row < len(PLACES):
            path = PLACES[row][1]
            os.makedirs(path, exist_ok=True)
            self.open_path(path)

    def _on_double_click(self, index):
        self.open_path(self.model.filePath(index))

    def _toggle_hidden(self, on):
        flags = QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot
        if on:
            flags |= QDir.Filter.Hidden
        self.model.setFilter(flags)

    def _delete_selected(self):
        indexes = self.view.selectionModel().selectedRows()
        for index in indexes:
            path = self.model.filePath(index)
            try:
                trashutil.move_to_trash(path)
            except OSError as exc:
                QMessageBox.critical(self, "Ошибка", f"{path}: {exc}")
        if indexes:
            self.statusBar().showMessage("Перемещено в корзину")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(style.get_stylesheet())
    window = Files(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
