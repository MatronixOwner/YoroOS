"""Yoro Settings — appearance, desktop and links to system controls."""
import os
import platform
import shutil
import sys

from PyQt6.QtCore import QProcess, Qt, QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QListWidget, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSlider,
    QStackedWidget, QVBoxLayout, QWidget)
from yoroapps import panelsetup, style, welcome_state

ACCENTS = [("Синий", "#3478f6"), ("Бирюзовый", "#168e97"),
           ("Фиолетовый", "#8260c8"), ("Розовый", "#c44d80"),
           ("Оранжевый", "#d98133"), ("Зелёный", "#4b9664")]
WALLPAPER_DIRS = ["/usr/share/wallpapers/YoroOS", "desktop/wallpapers"]


def os_pretty_name():
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return "YoroOS Desktop"


def heading(title, subtitle):
    box = QVBoxLayout()
    label = QLabel(title); label.setObjectName("title")
    desc = QLabel(subtitle); desc.setObjectName("subtitle"); desc.setWordWrap(True)
    box.addWidget(label); box.addWidget(desc); box.addSpacing(12)
    return box


def card(title, detail):
    frame = QFrame()
    frame.setObjectName('settingsCard')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 15, 18, 15)
    name = QLabel(title); name.setStyleSheet('font-weight: 600; font-size: 11pt;')
    desc = QLabel(detail); desc.setObjectName('subtitle'); desc.setWordWrap(True)
    layout.addWidget(name); layout.addWidget(desc)
    return frame, layout


class Settings(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настройки YoroOS")
        self.audio = QAudioOutput(self); self.audio.setVolume(0.75)
        self.player = QMediaPlayer(self); self.player.setAudioOutput(self.audio)
        self.player.errorOccurred.connect(self._audio_error)
        self.resize(860, 610)
        self.setMinimumSize(650, 470)
        nav = QListWidget()
        nav.setObjectName('places')
        nav.addItems(['Внешний вид', 'Рабочий стол', 'Приветствие', 'Система', 'О системе'])
        nav.setFixedWidth(190)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._appearance_page())
        self.pages.addWidget(self._desktop_page())
        self.pages.addWidget(self._welcome_page())
        self.pages.addWidget(self._system_page())
        self.pages.addWidget(self._about_page())
        # Keep all controls reachable on small VM displays and at high scaling.
        for index in range(self.pages.count()):
            child = self.pages.widget(index)
            self.pages.removeWidget(child)
            scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setWidget(child); self.pages.insertWidget(index, scroll)
        nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        nav.setCurrentRow(0)
        sidebar = QWidget(); sidebar.setObjectName('sidebar')
        side = QVBoxLayout(sidebar); side.setContentsMargins(14, 22, 14, 14)
        brand = QLabel('YoroOS'); brand.setObjectName('title')
        brand_subtitle = QLabel('ЦЕНТР НАСТРОЕК'); brand_subtitle.setObjectName('section')
        side.addWidget(brand); side.addWidget(brand_subtitle); side.addSpacing(16); side.addWidget(nav)
        foot = QLabel('Создано для вас'); foot.setObjectName('subtitle'); side.addWidget(foot)
        layout = QHBoxLayout(); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        layout.addWidget(sidebar); layout.addWidget(self.pages, 1)
        root = QWidget(); root.setLayout(layout); self.setCentralWidget(root)

    def _page(self, title, description):
        page = QWidget(); v = QVBoxLayout(page)
        v.setContentsMargins(32, 28, 32, 24); v.setSpacing(12)
        v.addLayout(heading(title, description))
        return page, v

    def _appearance_page(self):
        page, v = self._page('Внешний вид', 'Настройте цвет и фон рабочего стола.')
        frame, box = card('Тема приложений Yoro', 'Применяется к приложениям Yoro при их следующем запуске; тема Plasma и Matronix не меняется.')
        row = QHBoxLayout()
        for label, mode in (('Светлая', 'light'), ('Тёмная', 'dark')):
            btn = QPushButton(label); btn.clicked.connect(lambda _=False, m=mode: self._set_mode(m)); row.addWidget(btn)
        box.addLayout(row); v.addWidget(frame)
        frame, box = card('Акцент', 'Цвет элементов в приложениях Yoro. Изменение применяется при следующем запуске других приложений.')
        row = QHBoxLayout()
        for name, color in ACCENTS:
            btn = QPushButton(name); btn.setToolTip(name)
            btn.setStyleSheet(f'background:{color}; color:white; border:none; border-radius:7px; padding:9px;')
            btn.clicked.connect(lambda _=False, c=color: self._set_accent(c))
            row.addWidget(btn)
        box.addLayout(row); v.addWidget(frame)
        frame, box = card('Обои', 'Фон применяется к текущему рабочему столу Plasma.')
        row = QHBoxLayout()
        for path in self._find_wallpapers():
            names = {'yoro-horizon.jpg': 'Горизонт', 'gradient-aurora.jpg': 'Аврора', 'gradient-ocean.jpg': 'Океан', 'gradient-sunset.jpg': 'Закат'}
            btn = QPushButton(names.get(os.path.basename(path), os.path.basename(path)))
            btn.clicked.connect(lambda _=False, p=path: self._set_wall(p)); row.addWidget(btn)
        box.addLayout(row); v.addWidget(frame); v.addStretch()
        return page

    def _find_wallpapers(self):
        for directory in WALLPAPER_DIRS:
            if os.path.isdir(directory):
                return sorted(os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(('.jpg', '.png')))
        return []

    def _set_accent(self, color):
        try:
            style.save_accent(color)
            QApplication.instance().setStyleSheet(style.get_stylesheet(color))
            self.statusBar().showMessage('Цвет сохранён', 3000)
        except OSError as exc:
            QMessageBox.warning(self, 'Оформление', str(exc))

    def _set_mode(self, mode):
        try:
            style.save_mode(mode)
            QApplication.instance().setStyleSheet(style.get_stylesheet())
            self.statusBar().showMessage('Тема сохранена', 3000)
        except OSError as exc:
            QMessageBox.warning(self, 'Оформление', str(exc))

    def _set_wall(self, path):
        if not panelsetup.set_wallpaper(path):
            QMessageBox.warning(self, 'Обои', 'Не удалось изменить фон рабочего стола.')
        else:
            self.statusBar().showMessage('Фон обновлён', 3000)

    def _desktop_page(self):
        page, v = self._page('Рабочий стол', 'Размер и положение панели приложений.')
        frame, box = card('Панель приложений', 'Меню, индикаторы и часы остаются на верхней панели.')
        self.height_slider = QSlider(Qt.Orientation.Horizontal)
        self.height_slider.setRange(40, 80); self.height_slider.setValue(64)
        box.addWidget(QLabel('Размер панели')); box.addWidget(self.height_slider)
        row = QHBoxLayout()
        for label, location in (('Снизу', 'bottom'), ('Слева', 'left'), ('Справа', 'right')):
            btn = QPushButton(label); btn.clicked.connect(lambda _=False, l=location: self._apply_panel(l)); row.addWidget(btn)
        box.addLayout(row); v.addWidget(frame); v.addStretch()
        return page

    def _apply_panel(self, location):
        if panelsetup.apply_panel_preset(location, self.height_slider.value()):
            self.statusBar().showMessage('Панель обновлена', 3000)
        else:
            QMessageBox.warning(self, 'Панель', 'Не удалось изменить панель Plasma.')

    def _welcome_page(self):
        page, v = self._page('Приветствие', 'Фирменное приветствие при первом входе в сессию.')
        frame, box = card('Голос', 'Загрузите MP3, на использование которого у вас есть права. При первом входе файл прозвучит без подключения к сети.')
        self.voice_status = QLabel(); self.voice_status.setObjectName('subtitle'); self.voice_status.setWordWrap(True)
        box.addWidget(self.voice_status)
        self.voice_enabled = QCheckBox('Воспроизводить при первом входе')
        self.voice_enabled.setChecked(style.load_preferences().get('welcome_audio', True) is not False)
        self.voice_enabled.toggled.connect(self._set_welcome_audio)
        box.addWidget(self.voice_enabled)
        row = QHBoxLayout()
        choose = QPushButton('Выбрать MP3…'); choose.clicked.connect(self._choose_voice)
        play = QPushButton('Прослушать'); play.clicked.connect(self._play_voice)
        row.addWidget(choose); row.addWidget(play); box.addLayout(row)
        show = QPushButton('Показать экран приветствия'); show.clicked.connect(lambda: QProcess.startDetached('yoro-welcome', ['--show']))
        box.addWidget(show)
        v.addWidget(frame)
        note = QLabel('В Live-образе настройки и загруженный файл удаляются после выключения. Само приветствие появится снова при следующей загрузке.')
        note.setObjectName('subtitle'); note.setWordWrap(True); v.addWidget(note); v.addStretch()
        self._update_voice_status()
        return page

    def _update_voice_status(self):
        self.voice_status.setText('Файл приветствия подключён.' if welcome_state.sound_path() else 'Голосовой файл пока не добавлен.')

    def _set_welcome_audio(self, enabled):
        try:
            style.save_preferences(welcome_audio=enabled)
        except OSError as exc:
            QMessageBox.warning(self, 'Приветствие', str(exc))

    def _choose_voice(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Выберите приветствие', os.path.expanduser('~'), 'MP3 (*.mp3 *.MP3)')
        if not path:
            return
        try:
            self.player.stop()
            welcome_state.import_sound(path)
            self._update_voice_status()
            self.statusBar().showMessage('Приветствие добавлено', 3000)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, 'Приветствие', str(exc))

    def _play_voice(self):
        path = welcome_state.sound_path()
        if not path:
            QMessageBox.information(self, 'Приветствие', 'Сначала выберите MP3-файл.')
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def _audio_error(self, _error, message):
        self.statusBar().showMessage('Ошибка воспроизведения: ' + message, 8000)

    def _system_page(self):
        page, v = self._page('Система', 'Откройте встроенные настройки оборудования и сети.')
        for label, module in (('Экран', 'kcm_kscreen'), ('Сеть', 'kcm_network'),
                              ('Звук', 'kcm_pulseaudio'), ('Электропитание', 'kcm_powerdevilprofilesconfig')):
            btn = QPushButton(label + '   ›'); btn.setMinimumHeight(42)
            btn.clicked.connect(lambda _=False, m=module: self._open_kde(m)); v.addWidget(btn)
        v.addStretch(); return page

    def _open_kde(self, module):
        if not shutil.which('systemsettings'):
            QMessageBox.warning(self, 'Система', 'Системные настройки недоступны.')
            return
        QProcess.startDetached('systemsettings', [module])

    def _about_page(self):
        page, v = self._page('О системе', 'Информация об этой тестовой сборке.')
        frame, box = card(os_pretty_name(), f'Linux {platform.release()}  ·  {platform.machine()}')
        info = QLabel('Live-образ на основе Debian и KDE Plasma.\nИзменения не сохраняются после выключения.\nСобственное ядро YoroOS разрабатывается отдельно.')
        info.setWordWrap(True); box.addWidget(info); v.addWidget(frame); v.addStretch()
        return page


def main():
    app = QApplication(sys.argv)
    style.setup_app(app)
    app.setStyleSheet(style.get_stylesheet())
    window = Settings(); window.show(); sys.exit(app.exec())


if __name__ == '__main__':
    main()
