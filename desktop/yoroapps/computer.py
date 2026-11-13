"""Yoro Мой компьютер — drives, main folders and system info."""

import platform
import sys

from PyQt6.QtCore import QStorageInfo, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QApplication, QGridLayout, QLabel, QMainWindow,
                             QProgressBar, QPushButton, QVBoxLayout, QWidget)

from yoroapps import style
from yoroapps.settings import os_pretty_name

FOLDERS = [
    ("Домашний каталог", "~"),
    ("Документы", "~/Documents"),
    ("Загрузки", "~/Downloads"),
    ("Изображения", "~/Pictures"),
    ("Музыка", "~/Music"),
    ("Видео", "~/Videos"),
]


def human(n):
    for unit in ("Б", "КБ", "МБ", "ГБ", "ТБ"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "Б" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} ПБ"


class Computer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Мой компьютер — MatroOS")
        self.resize(760, 540)

        layout = QVBoxLayout()

        title = QLabel("Мой компьютер")
        title.setObjectName("title")
        layout.addWidget(title)
        info = QLabel(f"{os_pretty_name()} • ядро {platform.release()} • "
                      f"{platform.machine()}")
        info.setObjectName("subtitle")
        layout.addWidget(info)

        layout.addWidget(QLabel("Папки:"))
        grid = QGridLayout()
        import os
        for i, (name, path) in enumerate(FOLDERS):
            full = os.path.expanduser(path)
            btn = QPushButton(name)
            btn.setMinimumHeight(52)
            btn.clicked.connect(
                lambda _=False, p=full: QDesktopServices.openUrl(
                    QUrl.fromLocalFile(p)))
            grid.addWidget(btn, i // 3, i % 3)
        layout.addLayout(grid)

        layout.addWidget(QLabel("Диски и разделы:"))
        seen = set()
        for vol in QStorageInfo.mountedVolumes():
            if not vol.isValid() or not vol.isReady():
                continue
            root = vol.rootPath()
            total = vol.bytesTotal()
            if total <= 0 or root in seen:
                continue
            seen.add(root)
            avail = vol.bytesAvailable()
            used_pct = int((total - avail) * 100 / total)
            name = vol.displayName() or root
            btn = QPushButton(
                f"{name}  ({root}) — свободно {human(avail)} из {human(total)}")
            btn.clicked.connect(
                lambda _=False, p=root: QDesktopServices.openUrl(
                    QUrl.fromLocalFile(p)))
            layout.addWidget(btn)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(used_pct)
            layout.addWidget(bar)

        layout.addStretch(1)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)


def main():
    app = QApplication(sys.argv)
    style.setup_app(app)
    app.setStyleSheet(style.get_stylesheet())
    window = Computer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
