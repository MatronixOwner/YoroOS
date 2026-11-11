"""Yoro Корзина — view, restore and empty the freedesktop trash."""

import sys

from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                             QMessageBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from yoroapps import style, trashutil


class Trash(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Корзина — YoroOS")
        self.resize(780, 460)
        self.items = []

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Имя", "Исходное место", "Удалено"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows)
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(1, 380)

        restore_btn = QPushButton("Восстановить")
        restore_btn.setObjectName("accent")
        restore_btn.clicked.connect(self._restore_selected)
        delete_btn = QPushButton("Удалить навсегда")
        delete_btn.clicked.connect(self._delete_selected)
        empty_btn = QPushButton("Очистить корзину")
        empty_btn.clicked.connect(self._empty)

        buttons = QHBoxLayout()
        buttons.addWidget(restore_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch(1)
        buttons.addWidget(empty_btn)

        layout = QVBoxLayout()
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.refresh()

    def refresh(self):
        self.items = trashutil.list_trash()
        self.table.setRowCount(len(self.items))
        for row, item in enumerate(self.items):
            self.table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(item["original_path"]))
            self.table.setItem(
                row, 2, QTableWidgetItem(
                    item["deletion_date"].replace("T", " ")))
        self.statusBar().showMessage(f"В корзине: {len(self.items)}")

    def _selected_items(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()},
                      reverse=True)
        return [self.items[r] for r in rows if r < len(self.items)]

    def _restore_selected(self):
        for item in self._selected_items():
            try:
                trashutil.restore(item)
            except FileExistsError:
                QMessageBox.warning(
                    self, "Корзина",
                    f"Не могу восстановить {item['name']}: файл на исходном"
                    " месте уже существует.")
            except OSError as exc:
                QMessageBox.critical(self, "Ошибка", str(exc))
        self.refresh()

    def _delete_selected(self):
        selected = self._selected_items()
        if not selected:
            return
        if QMessageBox.question(
                self, "Корзина",
                f"Удалить навсегда: {len(selected)}? Это действие нельзя"
                " отменить.") != QMessageBox.StandardButton.Yes:
            return
        for item in selected:
            trashutil.delete_permanently(item)
        self.refresh()

    def _empty(self):
        if not self.items:
            return
        if QMessageBox.question(
                self, "Корзина", "Очистить корзину полностью? Все файлы"
                " будут удалены навсегда.") == QMessageBox.StandardButton.Yes:
            trashutil.empty_trash()
            self.refresh()


def main():
    app = QApplication(sys.argv)
    style.setup_app(app)
    app.setStyleSheet(style.get_stylesheet())
    window = Trash()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
