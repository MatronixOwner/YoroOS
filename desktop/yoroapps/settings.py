"""Yoro Центр Настроек: оформление, панель, кастомизация, система."""

import os
import platform
import shutil
import sys

from PyQt6.QtCore import QProcess, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget,
                             QMainWindow, QMessageBox, QPushButton, QSlider,
                             QStackedWidget, QVBoxLayout, QWidget)

from yoroapps import panelsetup, style

ACCENTS = [
    ("Синий Breeze", "#3daee9"), ("Бирюзовый", "#1abc9c"),
    ("Фиолетовый", "#9b59d0"), ("Розовый", "#e93d82"),
    ("Оранжевый", "#e67e22"), ("Зелёный", "#2ecc71"),
]

WALLPAPER_DIRS = ["/usr/share/wallpapers/YoroOS", "desktop/wallpapers"]

# Customization libraries: name -> info
CUST_LIBS = [
    {
        "name": "Hyprland", "kind": "Wayland-композитор (тайлинг)",
        "binary": "Hyprland", "apt": "hyprland",
        "config": "~/.config/hypr/hyprland.conf",
        "template": (
            "# YoroOS Hyprland config — https://wiki.hyprland.org\n"
            "monitor=,preferred,auto,1\n"
            "$mod = SUPER\n"
            "bind = $mod, Q, exec, yoro-console\n"
            "bind = $mod, E, exec, yoro-files\n"
            "bind = $mod, B, exec, matronix-browser\n"
            "bind = $mod, C, killactive,\n"
            "general { gaps_in = 6; gaps_out = 12; border_size = 2 }\n"
            "decoration { rounding = 12 }\n"
            "animations { enabled = true }\n"),
    },
    {
        "name": "Wayfire", "kind": "Wayland-композитор (3D-эффекты, куб)",
        "binary": "wayfire", "apt": "wayfire",
        "config": "~/.config/wayfire.ini",
        "template": (
            "# YoroOS Wayfire config\n[core]\nplugins = alpha animate autostart command cube decoration expo grid idle move place resize switcher vswitch window-rules wobbly zoom\n"
            "[autostart]\nbackground = wf-background\n"
            "[input]\nxkb_layout = us,ru\n"),
    },
    {
        "name": "Picom", "kind": "X11-композитор (тени, размытие, анимации)",
        "binary": "picom", "apt": "picom",
        "config": "~/.config/picom/picom.conf",
        "template": (
            "# YoroOS Picom config (работает в X11-сессии)\n"
            "backend = \"glx\";\nvsync = true;\ncorner-radius = 12;\n"
            "shadow = true;\nshadow-radius = 14;\nshadow-opacity = 0.35;\n"
            "fading = true;\nfade-in-step = 0.06;\nfade-out-step = 0.06;\n"
            "blur-method = \"dual_kawase\";\nblur-strength = 6;\n"),
    },
    {
        "name": "Eww", "kind": "Elkowars Wacky Widgets — виджеты и бары",
        "binary": "eww", "apt": None,
        "url": "https://github.com/elkowar/eww/releases",
        "config": "~/.config/eww/eww.yuck",
        "template": (
            ";; YoroOS Eww config — https://elkowar.github.io/eww\n"
            "(defwidget bar []\n"
            "  (centerbox :class \"bar\"\n"
            "    (label :text \"YoroOS\")\n"
            "    (label :text {time})\n"
            "    (label :text \"Matronix\")))\n"
            "(defpoll time :interval \"1s\" \"date '+%H:%M'\")\n"
            "(defwindow bar :monitor 0 :geometry (geometry :x \"0%\" "
            ":y \"0%\" :width \"100%\" :height \"32px\" :anchor \"top center\")"
            " :stacking \"fg\" (bar))\n"),
    },
]

KDE_MODULES = [
    ("Экран и монитор", "kcm_kscreen"), ("Сеть (Wi-Fi)", "kcm_network"),
    ("Звук", "kcm_pulseaudio"), ("Электропитание", "kcm_powerdevilprofilesconfig"),
    ("Пользователи", "kcm_users"),
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
        self.resize(880, 560)

        nav = QListWidget()
        nav.addItems(["Оформление", "Панель и Пуск", "Кастомизация",
                      "Система", "О программе"])
        nav.setMaximumWidth(210)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._appearance_page())
        self.pages.addWidget(self._panel_page())
        self.pages.addWidget(self._customize_page())
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

    # ---------------- Оформление ----------------
    def _appearance_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        title = QLabel("Оформление")
        title.setObjectName("title")
        v.addWidget(title)
        v.addWidget(self._sub("Цвет акцента Yoro-приложений:"))
        row = QHBoxLayout()
        for name, color in ACCENTS:
            btn = QPushButton(name)
            btn.setStyleSheet(
                f"background: {color}; color: #10131a; border: none;"
                "border-radius: 8px; padding: 10px; font-weight: bold;")
            btn.clicked.connect(lambda _=False, c=color: self._set_accent(c))
            row.addWidget(btn)
        v.addLayout(row)

        v.addWidget(self._sub("Обои рабочего стола:"))
        wallpapers = self._find_wallpapers()
        if not wallpapers:
            v.addWidget(QLabel("Обои YoroOS не найдены "
                               "(/usr/share/wallpapers/YoroOS)."))
        row2 = QHBoxLayout()
        names = {"gradient-aurora.jpg": "🌌 Аврора",
                 "gradient-ocean.jpg": "🌊 Океан",
                 "gradient-sunset.jpg": "🌇 Закат"}
        for path in wallpapers:
            btn = QPushButton(names.get(os.path.basename(path),
                                        os.path.basename(path)))
            btn.setMinimumHeight(44)
            btn.clicked.connect(lambda _=False, p=path: self._set_wall(p))
            row2.addWidget(btn)
        v.addLayout(row2)
        v.addStretch(1)
        return page

    def _sub(self, text):
        label = QLabel(text)
        label.setObjectName("subtitle")
        return label

    def _find_wallpapers(self):
        for d in WALLPAPER_DIRS:
            if os.path.isdir(d):
                return sorted(os.path.join(d, f) for f in os.listdir(d)
                              if f.lower().endswith((".jpg", ".png")))
        return []

    def _set_accent(self, color):
        style.save_accent(color)
        QApplication.instance().setStyleSheet(style.get_stylesheet(color))
        self.statusBar().showMessage(f"Акцент: {color}")

    def _set_wall(self, path):
        ok = panelsetup.set_wallpaper(path)
        self.statusBar().showMessage(
            "Обои применены" if ok else
            "Не удалось применить (нужна сессия KDE Plasma)")

    # ---------------- Панель и Пуск ----------------
    def _panel_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        title = QLabel("Панель и меню «Пуск»")
        title.setObjectName("title")
        v.addWidget(title)
        v.addWidget(self._sub(
            "Фирменная панель YoroOS: кнопка «Пуск» с логотипом Yoro и "
            "закреплённые Yoro-приложения. Положение и высота — ниже."))

        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(36, 72)
        self.height_slider.setValue(46)
        v.addWidget(self._sub("Высота панели:"))
        v.addWidget(self.height_slider)

        row = QHBoxLayout()
        for text, loc in (("Панель снизу", "bottom"), ("Панель сверху", "top"),
                          ("Слева", "left"), ("Справа", "right")):
            btn = QPushButton(text)
            btn.clicked.connect(lambda _=False, l=loc: self._apply_panel(l))
            row.addWidget(btn)
        v.addLayout(row)

        reset = QPushButton("Сбросить панель к виду YoroOS")
        reset.setObjectName("accent")
        reset.clicked.connect(lambda: self._apply_panel("bottom"))
        v.addWidget(reset)
        v.addWidget(self._sub(
            "Тонкая настройка: правый клик по панели → «Настроить панель»."))
        v.addStretch(1)
        return page

    def _apply_panel(self, location):
        ok = panelsetup.apply_panel_preset(location,
                                           self.height_slider.value())
        self.statusBar().showMessage(
            "Панель обновлена" if ok else
            "Не удалось (нужен запущенный KDE Plasma и qdbus)")

    # ---------------- Кастомизация ----------------
    def _customize_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        title = QLabel("Библиотеки кастомизации")
        title.setObjectName("title")
        v.addWidget(title)
        v.addWidget(self._sub(
            "Скачивайте композиторы и виджеты и настраивайте их под себя. "
            "Установка попросит пароль администратора."))

        for lib in CUST_LIBS:
            box = QVBoxLayout()
            installed = shutil.which(lib["binary"]) is not None
            head = QLabel(f"{lib['name']} — {lib['kind']}"
                          + ("  ✅ установлен" if installed else ""))
            head.setStyleSheet("font-weight: bold; font-size: 12pt;")
            box.addWidget(head)
            row = QHBoxLayout()
            b_install = QPushButton("Скачать / Установить")
            b_install.clicked.connect(
                lambda _=False, l=lib: self._install_lib(l))
            b_conf = QPushButton("Открыть конфиг")
            b_conf.clicked.connect(
                lambda _=False, l=lib: self._open_config(l))
            row.addWidget(b_install)
            row.addWidget(b_conf)
            row.addStretch(1)
            box.addLayout(row)
            v.addLayout(box)
        v.addStretch(1)
        return page

    def _install_lib(self, lib):
        if lib.get("apt"):
            if shutil.which("pkexec") is None:
                QMessageBox.warning(self, "Установка",
                                    "pkexec не найден — поставьте вручную: "
                                    f"sudo apt install {lib['apt']}")
                return
            QProcess.startDetached(
                "pkexec", ["/bin/sh", "-c",
                           f"apt-get update && apt-get install -y {lib['apt']}"])
            self.statusBar().showMessage(
                f"{lib['name']}: установка запущена (введите пароль)…")
        else:
            QDesktopServices.openUrl(QUrl(lib["url"]))
            self.statusBar().showMessage(
                f"{lib['name']}: открыта страница загрузки")

    def _open_config(self, lib):
        path = os.path.expanduser(lib["config"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(lib["template"])
        if shutil.which("yoro-notepad"):
            QProcess.startDetached("yoro-notepad", [path])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        self.statusBar().showMessage(f"Конфиг: {path}")

    # ---------------- Система ----------------
    def _system_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        title = QLabel("Системные настройки")
        title.setObjectName("title")
        v.addWidget(title)
        v.addWidget(QLabel(f"ОС: {os_pretty_name()}"))
        v.addWidget(QLabel(f"Ядро Linux: {platform.release()}"))
        v.addWidget(QLabel(f"Архитектура: {platform.machine()}"))
        for name, module in KDE_MODULES:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _=False, m=module: self._open_kde(m))
            v.addWidget(btn)
        v.addStretch(1)
        return page

    def _about_page(self):
        page = QWidget()
        v = QVBoxLayout(page)
        title = QLabel("YoroOS Desktop")
        title.setObjectName("title")
        v.addWidget(title)
        text = QLabel(
            "Своя система: рабочий стол на Debian + KDE Plasma, "
            "сверху — только свои приложения Matronix/Yoro:\n"
            "Matronix Browser, Блокнот, Файлы, Медиа, Paint, Калькулятор,\n"
            "Консоль, Мой компьютер, Корзина и этот Центр Настроек.\n\n"
            "Windows-программы запускаются через Wine.\n"
            "Собственное ядро YoroOS Core — вторым режимом загрузки.")
        v.addWidget(text)
        v.addStretch(1)
        return page

    def _open_kde(self, module):
        if shutil.which("systemsettings") is None:
            QMessageBox.information(
                self, "Настройки KDE", "systemsettings не установлен.")
            return
        QProcess.startDetached("systemsettings", [module] if module else [])


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(style.get_stylesheet())
    window = Settings()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
