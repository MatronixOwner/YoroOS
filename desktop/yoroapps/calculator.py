"""Yoro Калькулятор."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QGridLayout, QLabel, QMainWindow,
                             QPushButton, QVBoxLayout, QWidget)

from yoroapps import calcengine, style

BUTTONS = [
    ["C", "⌫", "%", "÷"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "−"],
    ["1", "2", "3", "+"],
    ["±", "0", ".", "="],
]


class Calculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yoro Калькулятор")
        self.resize(330, 470)
        self.expression = ""
        self.just_evaluated = False

        self.history = QLabel("")
        self.history.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.history.setStyleSheet("color: #9aa3b2; font-size: 11pt;")

        self.display = QLabel("0")
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setStyleSheet(
            "font-size: 30pt; font-weight: bold; padding: 8px;")

        grid = QGridLayout()
        grid.setSpacing(6)
        for r, row in enumerate(BUTTONS):
            for c, label in enumerate(row):
                btn = QPushButton(label)
                btn.setMinimumHeight(58)
                btn.setStyleSheet("font-size: 15pt; border-radius: 12px;")
                if label == "=":
                    btn.setObjectName("accent")
                elif label in "÷×−+%":
                    btn.setStyleSheet(
                        "font-size: 15pt; border-radius: 12px;"
                        "background: #333947;")
                btn.clicked.connect(lambda _=False, t=label: self._press(t))
                grid.addWidget(btn, r, c)

        layout = QVBoxLayout()
        layout.addWidget(self.history)
        layout.addWidget(self.display)
        layout.addLayout(grid)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

    def _press(self, key):
        if key == "C":
            self.expression = ""
            self.history.setText("")
            self.display.setText("0")
            return
        if key == "⌫":
            self.expression = self.expression[:-1]
            self.display.setText(self.expression or "0")
            return
        if key == "=":
            if not self.expression:
                return
            try:
                result = calcengine.evaluate(self.expression)
                text = calcengine.format_result(result)
            except (ValueError, ZeroDivisionError):
                self.display.setText("Ошибка")
                self.expression = ""
                return
            self.history.setText(self.expression + " =")
            self.expression = text
            self.display.setText(text)
            self.just_evaluated = True
            return
        if key == "±":
            if self.expression.startswith("-"):
                self.expression = self.expression[1:]
            elif self.expression:
                self.expression = "-" + self.expression
            self.display.setText(self.expression or "0")
            return

        if self.just_evaluated and key.isdigit():
            self.expression = ""
        self.just_evaluated = False
        self.expression += key
        self.display.setText(self.expression)

    def keyPressEvent(self, event):
        text = event.text()
        if text and text in "0123456789.+-*/%()":
            self._press({"*": "×", "/": "÷", "-": "−"}.get(text, text))
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter,
                             Qt.Key.Key_Equal):
            self._press("=")
        elif event.key() == Qt.Key.Key_Backspace:
            self._press("⌫")
        elif event.key() == Qt.Key.Key_Escape:
            self._press("C")
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(style.get_stylesheet())
    window = Calculator()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
