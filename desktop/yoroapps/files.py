"""Yoro Files: a light, keyboard-friendly file manager for local files."""
import os
import sys

from PyQt6.QtCore import QDir, QMimeData, QSize, Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QFileSystemModel, QIcon, QKeySequence
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QSplitter, QStackedWidget, QToolButton,
    QTreeView, QVBoxLayout, QWidget)

from yoroapps import fileops, style, trashutil

PLACES = [
    ("Домой", "user-home", "~"),
    ("Рабочий стол", "user-desktop", "~/Desktop"),
    ("Документы", "folder-documents", "~/Documents"),
    ("Загрузки", "folder-download", "~/Downloads"),
    ("Изображения", "folder-pictures", "~/Pictures"),
    ("Музыка", "folder-music", "~/Music"),
    ("Видео", "folder-videos", "~/Videos"),
    ("Файловая система", "drive-harddisk", "/"),
]
CUT_MIME = "application/x-yoro-cut"


class Files(QMainWindow):
    def __init__(self, start=None):
        super().__init__()
        self.setWindowTitle("Файлы")
        self.resize(1000, 660)
        self.setMinimumSize(680, 420)
        self._history = []
        self._history_index = -1
        self._path = ""
        self.model = QFileSystemModel(self)
        self.model.setReadOnly(True)
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs)
        self.model.setNameFilterDisables(False)
        self.model.setRootPath("")

        self.list_view = QTreeView()
        self.list_view.setModel(self.model)
        self.list_view.setRootIsDecorated(False)
        self.list_view.setUniformRowHeights(True)
        self.list_view.setSortingEnabled(True)
        self.list_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.list_view.setColumnWidth(0, 310)
        self.list_view.setColumnWidth(1, 95)
        self.list_view.setColumnWidth(2, 115)
        self.list_view.setColumnWidth(3, 160)
        self.grid_view = QListView()
        self.grid_view.setModel(self.model)
        self.grid_view.setViewMode(QListView.ViewMode.IconMode)
        self.grid_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid_view.setMovement(QListView.Movement.Static)
        self.grid_view.setIconSize(QSize(48, 48))
        self.grid_view.setGridSize(QSize(120, 88))
        self.grid_view.setWordWrap(True)
        for view in (self.list_view, self.grid_view):
            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
            view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            view.doubleClicked.connect(lambda idx: self.open_path(self.model.filePath(idx)))
            view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            view.customContextMenuRequested.connect(lambda pos, v=view: self._context_menu(v, pos))
        self.views = QStackedWidget()
        self.views.addWidget(self.list_view)
        self.views.addWidget(self.grid_view)

        self.places = QListWidget()
        self.places.setObjectName("places")
        self.places.setIconSize(QSize(19, 19))
        for label, icon, path in PLACES:
            item = QListWidgetItem(QIcon.fromTheme(icon), label)
            item.setData(Qt.ItemDataRole.UserRole, os.path.expanduser(path))
            self.places.addItem(item)
        self.places.itemClicked.connect(lambda item: self.open_path(item.data(Qt.ItemDataRole.UserRole)))
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(10, 20, 10, 14)
        heading = QLabel("ИЗБРАННОЕ")
        heading.setObjectName("section")
        side_layout.addWidget(heading)
        side_layout.addWidget(self.places, 1)

        self.title = QLabel("Файлы")
        self.title.setObjectName("title")
        self.path_label = QLabel()
        self.path_label.setObjectName("subtitle")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.address = QLineEdit()
        self.address.setPlaceholderText("Путь к папке")
        self.address.setClearButtonEnabled(True)
        self.address.returnPressed.connect(lambda: self.open_path(self.address.text()))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск в этой папке")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(240)
        self.search.textChanged.connect(self._filter)

        self.back = self._tool("go-previous", "‹", "Назад", self.go_back)
        self.forward = self._tool("go-next", "›", "Вперёд", self.go_forward)
        self.up = self._tool("go-up", "↑", "Вверх", self.go_up)
        self.list_button = self._tool("view-list-details", "☰", "Список", lambda: self.set_view(0))
        self.grid_button = self._tool("view-grid", "▦", "Значки", lambda: self.set_view(1))
        self.list_button.setCheckable(True)
        self.grid_button.setCheckable(True)
        self.set_view(0)
        new = self._tool("folder-new", "+", "Новая папка", self.new_folder)
        menu_button = self._tool("application-menu", "⋯", "Действия", None)
        menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(menu_button)
        menu_button.setMenu(menu)
        self._actions(menu)
        row = QHBoxLayout()
        row.setSpacing(6)
        for button in (self.back, self.forward, self.up):
            row.addWidget(button)
        row.addSpacing(8)
        row.addWidget(self.address, 1)
        row.addWidget(self.search)
        for button in (self.list_button, self.grid_button, new, menu_button):
            row.addWidget(button)
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar_layout = QVBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(18, 14, 18, 14)
        heading_row = QHBoxLayout()
        heading_row.addWidget(self.title)
        heading_row.addStretch()
        toolbar_layout.addLayout(heading_row)
        toolbar_layout.addWidget(self.path_label)
        toolbar_layout.addSpacing(7)
        toolbar_layout.addLayout(row)
        main = QWidget()
        main_layout = QVBoxLayout(main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar)
        main_layout.addWidget(self.views, 1)
        split = QSplitter()
        split.addWidget(sidebar)
        split.addWidget(main)
        split.setChildrenCollapsible(False)
        split.setSizes([210, 790])
        self.setCentralWidget(split)
        self.open_path(start or os.path.expanduser("~"))

    def _tool(self, icon, fallback, tooltip, slot):
        button = QToolButton()
        themed = QIcon.fromTheme(icon)
        if themed.isNull():
            button.setText(fallback)
        else:
            button.setIcon(themed)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setMinimumSize(34, 32)
        if slot:
            button.clicked.connect(slot)
        return button

    def _actions(self, menu):
        for label, shortcut, slot in (
            ("Новая папка", "Ctrl+Shift+N", self.new_folder),
            ("Переименовать", "F2", self.rename_selected),
            ("Копировать", "Ctrl+C", lambda: self.copy_selected(False)),
            ("Вырезать", "Ctrl+X", lambda: self.copy_selected(True)),
            ("Вставить", "Ctrl+V", self.paste),
            ("Переместить в корзину", "Delete", self.trash_selected),
            ("Домой", "Alt+Home", lambda: self.open_path(os.path.expanduser("~"))),
            ("Назад", "Alt+Left", self.go_back),
            ("Вперёд", "Alt+Right", self.go_forward),
            ("Вверх", "Alt+Up", self.go_up),
        ):
            action = QAction(label, self)
            action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(slot)
            self.addAction(action)
            menu.addAction(action)
        hidden = QAction("Показывать скрытые файлы", self, checkable=True)
        hidden.setShortcut(QKeySequence("Ctrl+H"))
        hidden.toggled.connect(self._toggle_hidden)
        self.addAction(hidden)
        menu.addSeparator()
        menu.addAction(hidden)

    @property
    def current_path(self):
        return self._path

    def open_path(self, path, record=True):
        if not path or not path.strip():
            return
        path = os.path.abspath(os.path.expanduser(path.strip()))
        if os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            return
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Файлы", f"Не удалось открыть папку:\n{path}")
            return
        if not os.access(path, os.R_OK | os.X_OK):
            QMessageBox.warning(self, "Файлы", f"Нет доступа к папке:\n{path}")
            return
        self._path = path
        index = self.model.index(path)
        self.list_view.setRootIndex(index)
        self.grid_view.setRootIndex(index)
        self.address.setText(path)
        self.search.clear()
        self.title.setText(os.path.basename(path) or "Файловая система")
        self.path_label.setText(path)
        self.setWindowTitle(f"{os.path.basename(path) or '/'} — Файлы")
        if record and (self._history_index < 0 or self._history[self._history_index] != path):
            self._history = self._history[:self._history_index + 1] + [path]
            self._history_index = len(self._history) - 1
        self.back.setEnabled(self._history_index > 0)
        self.forward.setEnabled(self._history_index < len(self._history) - 1)
        self.statusBar().showMessage("Готово")

    def go_back(self):
        if self._history_index > 0:
            self._history_index -= 1
            self.open_path(self._history[self._history_index], False)

    def go_forward(self):
        if self._history_index + 1 < len(self._history):
            self._history_index += 1
            self.open_path(self._history[self._history_index], False)

    def go_up(self):
        self.open_path(os.path.dirname(self.current_path) or "/")

    def set_view(self, mode):
        self.views.setCurrentIndex(mode)
        self.list_button.setChecked(mode == 0)
        self.grid_button.setChecked(mode == 1)

    def _filter(self, text):
        self.model.setNameFilters([f"*{text}*"] if text else [])

    def _toggle_hidden(self, enabled):
        flags = QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs
        self.model.setFilter(flags | QDir.Filter.Hidden if enabled else flags)

    def selected_paths(self):
        view = self.views.currentWidget()
        return [self.model.filePath(i) for i in view.selectionModel().selectedRows(0)]

    def new_folder(self):
        name, ok = QInputDialog.getText(self, "Новая папка", "Название папки:")
        if not ok:
            return
        if not fileops.valid_name(name):
            QMessageBox.warning(self, "Новая папка", "Введите допустимое название без символа /.")
            return
        try:
            os.mkdir(os.path.join(self.current_path, name))
        except OSError as exc:
            QMessageBox.warning(self, "Новая папка", str(exc))

    def rename_selected(self):
        paths = self.selected_paths()
        if len(paths) != 1:
            return
        name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=os.path.basename(paths[0]))
        if ok:
            try:
                fileops.rename(paths[0], name)
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Переименовать", str(exc))

    def copy_selected(self, cut=False):
        paths = self.selected_paths()
        if not paths:
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        if cut:
            mime.setData(CUT_MIME, b"1")
        QApplication.clipboard().setMimeData(mime)
        self.statusBar().showMessage("Вырезано" if cut else "Скопировано", 3000)

    def paste(self):
        mime = QApplication.clipboard().mimeData()
        paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
        if not paths:
            return
        cut = mime.hasFormat(CUT_MIME)
        errors = fileops.copy_or_move(paths, self.current_path, move=cut)
        if errors:
            QMessageBox.warning(self, "Не удалось завершить операцию", "\n".join(f"{p}: {e}" for p, e in errors))
        elif cut:
            QApplication.clipboard().clear()
        else:
            self.statusBar().showMessage("Готово", 3000)

    def trash_selected(self):
        paths = self.selected_paths()
        if not paths:
            return
        if QMessageBox.question(self, "Корзина", f"Переместить выбранные объекты ({len(paths)}) в корзину?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        errors = []
        for path in paths:
            try:
                trashutil.move_to_trash(path)
            except OSError as exc:
                errors.append(f"{path}: {exc}")
        if errors:
            QMessageBox.warning(self, "Корзина", "\n".join(errors))
        else:
            self.statusBar().showMessage("Перемещено в корзину", 3000)

    def _context_menu(self, view, pos):
        menu = QMenu(self)
        for action in self.actions():
            menu.addAction(action)
        menu.exec(view.viewport().mapToGlobal(pos))


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(style.get_stylesheet())
    window = Files(sys.argv[1] if len(sys.argv) > 1 else None)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
