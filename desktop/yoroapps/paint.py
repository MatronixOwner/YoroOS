"""Yoro Paint — simple drawing app."""

import sys

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QImage, QPainter, QPen
from PyQt6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
                             QMainWindow, QMessageBox, QPushButton, QScrollArea, QSlider,
                             QVBoxLayout, QWidget)

from yoroapps import style

COLORS = ["#111111", "#e05252", "#e67e22", "#f2c531", "#2ecc71",
          "#2fa8e0", "#3d5af1", "#9b59d0", "#e93d82", "#ffffff"]


class Canvas(QWidget):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.image = QImage(1200, 800, QImage.Format.Format_RGB32)
        self.image.fill(QColor("white"))
        self.pen_color = QColor("#111111")
        self.pen_width = 4
        self.eraser = False
        self.last = None
        self.setFixedSize(1200, 800)

    def paintEvent(self, event):
        with QPainter(self) as painter:
            painter.drawImage(0, 0, self.image)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.last = event.position().toPoint()
            self._draw_to(self.last)

    def mouseMoveEvent(self, event):
        if self.last is not None and (
                event.buttons() & Qt.MouseButton.LeftButton):
            point = event.position().toPoint()
            self._draw_to(point)
            self.last = point

    def mouseReleaseEvent(self, event):
        self.last = None

    def _draw_to(self, point):
        with QPainter(self.image) as painter:
            color = QColor("white") if self.eraser else self.pen_color
            width = self.pen_width * (3 if self.eraser else 1)
            painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap,
                                Qt.PenJoinStyle.RoundJoin))
            if self.last is not None:
                painter.drawLine(self.last, point)
            else:
                painter.drawPoint(point)
        self.update()
        self.changed.emit()

    def clear(self):
        self.image.fill(QColor("white"))
        self.update()
        self.changed.emit()

    def load(self, path):
        loaded = QImage(path)
        if loaded.isNull():
            return False
        self.image = QImage(1200, 800, QImage.Format.Format_RGB32)
        self.image.fill(QColor("white"))
        with QPainter(self.image) as painter:
            painter.drawImage(0, 0, loaded.scaled(
                1200, 800, Qt.AspectRatioMode.KeepAspectRatio))
        self.update()
        return True


class Paint(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yoro Paint")
        self.resize(980, 640)
        self.canvas = Canvas()
        self.dirty = False
        self.canvas.changed.connect(self._mark_dirty)

        toolbar = self.addToolBar("Файл")
        for text, slot in (("Открыть…", self.open_image),
                           ("Сохранить PNG…", self.save_image),
                           ("Очистить", self.clear_canvas)):
            action = QAction(text, self)
            action.triggered.connect(slot)
            toolbar.addAction(action)

        palette = QHBoxLayout()
        palette.addWidget(QLabel("Цвет:"))
        for hex_color in COLORS:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setStyleSheet(
                f"background: {hex_color}; border: 2px solid #3a3f4b;"
                "border-radius: 14px;")
            btn.clicked.connect(
                lambda _=False, c=hex_color: self._set_color(c))
            palette.addWidget(btn)

        self.eraser_btn = QPushButton("Ластик")
        self.eraser_btn.setCheckable(True)
        self.eraser_btn.toggled.connect(
            lambda on: setattr(self.canvas, "eraser", on))
        palette.addWidget(self.eraser_btn)
        palette.addStretch(1)
        palette.addWidget(QLabel("Кисть:"))

        size = QSlider(Qt.Orientation.Horizontal)
        size.setRange(1, 30)
        size.setValue(4)
        size.setMaximumWidth(160)
        size.valueChanged.connect(
            lambda v: setattr(self.canvas, "pen_width", v))
        palette.addWidget(size)

        layout = QVBoxLayout()
        layout.addLayout(palette)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)
        layout.addWidget(scroll, 1)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Рисуйте мышью по полотну")

    def _mark_dirty(self):
        self.dirty = True
        self.setWindowTitle("Yoro Paint •")

    def _maybe_save(self):
        if not self.dirty:
            return True
        answer = QMessageBox.question(self, "Yoro Paint", "Сохранить изменения?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            return self.save_image()
        return answer == QMessageBox.StandardButton.Discard

    def clear_canvas(self):
        if self._maybe_save():
            self.canvas.clear()

    def closeEvent(self, event):
        if self._maybe_save(): event.accept()
        else: event.ignore()

    def _set_color(self, hex_color):
        self.canvas.pen_color = QColor(hex_color)
        self.canvas.eraser = False
        self.eraser_btn.setChecked(False)

    def open_image(self):
        if not self._maybe_save():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть изображение", "",
            "Картинки (*.png *.jpg *.jpeg *.bmp)")
        if path:
            if not self.canvas.load(path):
                QMessageBox.critical(self, "Yoro Paint", "Не удалось открыть файл")
            else:
                self.dirty = False
                self.setWindowTitle("Yoro Paint")

    def save_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить PNG", "рисунок.png", "PNG (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            if not self.canvas.image.save(path, "PNG"):
                QMessageBox.critical(self, "Yoro Paint", "Не удалось сохранить файл")
                return False
            self.dirty = False
            self.setWindowTitle("Yoro Paint")
            self.statusBar().showMessage(f"Сохранено: {path}")
            return True
        return False


def main():
    app = QApplication(sys.argv)
    style.setup_app(app)
    app.setStyleSheet(style.get_stylesheet())
    window = Paint()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
