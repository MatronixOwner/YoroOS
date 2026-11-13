"""A small first-session welcome; no network or remote TTS at login."""
import os
import sys

from PyQt6.QtCore import QProcess, QTimer, QUrl, Qt
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from yoroapps import style, welcome_state


class Welcome(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Добро пожаловать в MatroOS')
        self.resize(610, 430)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.75)
        self.player.setAudioOutput(self.audio)
        layout = QVBoxLayout(self); layout.setContentsMargins(50, 40, 50, 38); layout.setSpacing(14)
        logo = QLabel(); logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for path in ('/usr/share/icons/hicolor/512x512/apps/matroos-logo.png',
                     os.path.join(os.path.dirname(__file__), '..', 'icons', 'matroos-logo.png')):
            if os.path.isfile(path):
                logo.setPixmap(QPixmap(path).scaled(78, 78, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                break
        layout.addWidget(logo)
        kicker = QLabel('ВАШЕ ПРОСТРАНСТВО'); kicker.setObjectName('section'); kicker.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel('Добро пожаловать в MatroOS'); title.setObjectName('title'); title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text = QLabel('Всё готово к началу работы. Настройте рабочий стол под себя или сразу переходите к приложениям.')
        text.setObjectName('subtitle'); text.setWordWrap(True); text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        live = QLabel('Live-сессия: изменения исчезнут после выключения.')
        live.setObjectName('subtitle'); live.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for widget in (kicker, title, text, live): layout.addWidget(widget)
        layout.addStretch()
        row = QHBoxLayout(); settings = QPushButton('Открыть настройки'); settings.clicked.connect(self.open_settings)
        start = QPushButton('Начать работу'); start.setObjectName('accent'); start.clicked.connect(self.close)
        row.addStretch(); row.addWidget(settings); row.addWidget(start); row.addStretch(); layout.addLayout(row)

    def open_settings(self):
        QProcess.startDetached('yoro-settings', [])
        self.close()

    def play_welcome(self):
        path = welcome_state.sound_path()
        if path and style.load_preferences().get('welcome_audio', True) is not False:
            self.player.setSource(QUrl.fromLocalFile(str(path)))
            self.player.play()


def main():
    if "--show" not in sys.argv and not welcome_state.is_first_run():
        return
    app = QApplication([sys.argv[0]]); style.setup_app(app); app.setStyleSheet(style.get_stylesheet())
    window = Welcome(); style.enable_glass(app, window); window.show()
    try:
        welcome_state.mark_seen()
    except OSError as exc:
        print('Unable to save welcome state:', exc, file=sys.stderr)
    QTimer.singleShot(1200, window.play_welcome)
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
