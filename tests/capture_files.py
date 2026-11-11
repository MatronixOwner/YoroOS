"""Produce an offscreen screenshot with representative, non-user data."""
import os
import sys
import tempfile
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from yoroapps import style
from yoroapps.files import Files

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
with tempfile.TemporaryDirectory() as td:
    root = Path(td) / 'Документы'; root.mkdir()
    for name in ('Работа', 'Проекты', 'Архив'): (root / name).mkdir()
    for name in ('Заметки.txt', 'Идеи.txt', 'Список.txt'): (root / name).write_text('Yoro')
    app = QApplication([])
    QIcon.setThemeName('breeze')
    app.setStyleSheet(style.get_stylesheet())
    window = Files(str(root)); window.show()
    def capture():
        image = window.grab().toImage().scaled(800, 528, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        image.save('/work/files-preview.jpg', 'JPG', 65)
        app.quit()
    QTimer.singleShot(2500, capture)
    app.exec()
