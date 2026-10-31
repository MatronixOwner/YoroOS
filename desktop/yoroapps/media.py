"""Yoro Медиа — audio/video player based on QtMultimedia."""

import os
import sys

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
                             QListWidget, QMainWindow, QPushButton, QSlider,
                             QVBoxLayout, QWidget)

from yoroapps import style


def format_ms(ms):
    seconds = max(0, int(ms // 1000))
    return f"{seconds // 60}:{seconds % 60:02d}"


class MediaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yoro Медиа")
        self.resize(860, 560)

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.audio.setVolume(0.8)
        self.player.setAudioOutput(self.audio)

        self.video = QVideoWidget()
        self.player.setVideoOutput(self.video)

        self.playlist = QListWidget()
        self.playlist.setMaximumWidth(260)
        self.playlist.currentRowChanged.connect(self._row_changed)
        self.files = []

        open_btn = QPushButton("Открыть…")
        open_btn.clicked.connect(self.open_files)
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("accent")
        self.play_btn.clicked.connect(self.toggle_play)
        stop_btn = QPushButton("■")
        stop_btn.clicked.connect(self.player.stop)

        self.position = QSlider(Qt.Orientation.Horizontal)
        self.position.sliderMoved.connect(self.player.setPosition)
        self.time_label = QLabel("0:00 / 0:00")

        volume = QSlider(Qt.Orientation.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(80)
        volume.setMaximumWidth(130)
        volume.valueChanged.connect(lambda v: self.audio.setVolume(v / 100))

        controls = QHBoxLayout()
        controls.addWidget(open_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(stop_btn)
        controls.addWidget(self.position, 1)
        controls.addWidget(self.time_label)
        controls.addWidget(QLabel("Громкость"))
        controls.addWidget(volume)

        right = QVBoxLayout()
        right.addWidget(self.video, 1)
        right.addLayout(controls)

        layout = QHBoxLayout()
        layout.addWidget(self.playlist)
        layout.addLayout(right, 1)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.player.positionChanged.connect(self._position_changed)
        self.player.durationChanged.connect(
            lambda d: self.position.setRange(0, d))
        self.player.playbackStateChanged.connect(self._state_changed)
        self.player.mediaStatusChanged.connect(self._media_status)

    def open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Открыть медиафайлы", os.path.expanduser("~"),
            "Медиа (*.mp3 *.wav *.ogg *.flac *.mp4 *.mkv *.webm *.avi);;"
            "Все файлы (*)")
        for path in paths:
            self.files.append(path)
            self.playlist.addItem(os.path.basename(path))
        if paths and self.playlist.currentRow() < 0:
            self.playlist.setCurrentRow(0)

    def _row_changed(self, row):
        if 0 <= row < len(self.files):
            self.player.setSource(QUrl.fromLocalFile(self.files[row]))
            self.setWindowTitle(
                f"Yoro Медиа — {os.path.basename(self.files[row])}")
            self.player.play()

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _position_changed(self, pos):
        if not self.position.isSliderDown():
            self.position.setValue(pos)
        self.time_label.setText(
            f"{format_ms(pos)} / {format_ms(self.player.duration())}")

    def _state_changed(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_btn.setText("❚❚" if playing else "▶")

    def _media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            row = self.playlist.currentRow() + 1
            if row < len(self.files):
                self.playlist.setCurrentRow(row)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(style.get_stylesheet())
    window = MediaPlayer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
