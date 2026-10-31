"""Yoro Центр Настроек — appearance + shortcuts to KDE system settings."""

import os
import platform
import shutil
import sys

from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget,
                             QMainWindow, QMessageBox, QPushButton,
                             QStackedWidget, QVBoxLayout, QWidget)

from yoroapps import style

ACCENTS = [
    ("Синий Breeze", "#3daee9"),
    ("Бирюзовый", "#1abc9c"),
    ("Фиолетовый", "#9b59d0"),
    ("Розовый", "#e93d82"),
    ("Оранжевый", "#e67e22"),
    ("Зелёный", "#2ecc71"),
]

KDE_MODULES = [
    ("Экран и монитор", "kcm_kscreen"),
    ("Сеть (Wi-Fi)", "kcm_network"),
    ("Звук", "kcm_pulseaudio"),
    ("Электропитание", "kcm_powerdevilprofilesconfig"),
    ("Пользователи", "kcm_users"),
    ("Программы по умолчанию", "kcm_componentchooser"),
]


def os_pretty_name():
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return "YoroOS Desktop"


class Settings(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yoro Центр Настроек")
        self.resize(820, 520)

        nav = QListWidget()
        nav.addItems(["Оформление", "Система", "О программе"])
        nav.setMaximumWidth(200)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._appearance_page())
        self.pages.addWidget(self._system_page())
        self.pages.addWidget(self._about_page())
        nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        nav.setCurrentRow(0)

        layout = QHBoxLayout()
        layout.addWidget(nav)
        layout.addWidget(self.pages, 1)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def _appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("Оформление Yoro-приложений")
        title.setObjectName("title")
        layout.addWidget(title)
        hint = QLabel("Цвет акцента применяется ко всем приложениям YoroOS "
                      "(новые окна откроются уже с ним).")
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        for name, color in ACCENTS:
            btn = QPushButton(name)
            btn.setStyleSheet(
                f"background: {color}; color: #10131a; border: none;"
                "border-radius: 8px; padding: 10px; font-weight: bold;")
            btn.clicked.connect(lambda _=False, c=color: self._set_accent(c))
            row.addWidget(btn)
        layout.addLayout(row)

        kde_btn = QPushButton("Открыть полные настройки KDE…")
        kde_btn.clicked.connect(lambda: self._open_kde(""))
        layout.addWidget(kde_btn)
        layout.addStretch(1)
        return page

    def _system_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("Системные настройки")
        title.setObjectName("title")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"ОС: {os_pretty_name()}"))
        layout.addWidget(QLabel(f"Ядро: {platform.release()}"))
        layout.addWidget(QLabel(f"Архитектура: {platform.machine()}"))
        for name, module in KDE_MODULES:
            btn = QPushButton(name)
            btn.clicked.connect(
                lambda _=False, m=module: self._open_kde(m))
            layout.addWidget(btn)
        layout.addStretch(1)
        return page

    def _about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        title = QLabel("YoroOS Desktop")
        title.setObjectName("title")
        layout.addWidget(title)
        text = QLabel(
            "Гибридная система: рабочий стол на Linux (Debian + KDE Plasma)\n"
            "+ собственное ядро YoroOS Core вторым режимом загрузки.\n\n"
            "Windows-программы запускаются через Wine.\n"
            "Браузер: Chromium.\n\n"
            "Приложения Yoro: Блокнот, Файлы, Медиа, Консоль, "
            "Мой компьютер, Корзина, Центр Настроек.")
        text.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(text)
        layout.addStretch(1)
        return page

    def _set_accent(self, color):
        style.save_accent(color)
        QApplication.instance().setStyleSheet(style.get_stylesheet(color))
        self.statusBar().showMessage(f"Акцент изменён: {color}")

    def _open_kde(self, module):
        if shutil.which("systemsettings") is None:
            QMessageBox.information(
                self, "Yoro Центр Настроек",
                "Настройки KDE (systemsettings) не найдены в этой системе.")
            return
        args = [module] if module else []
        QProcess.startDetached("systemsettings", args)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(style.get_stylesheet())
    window = Settings()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
