"""Yoro Консоль — command console with YoroOS flavor.

Line-based console on top of /bin/bash (via QProcess). Interactive
full-screen programs (vim, top) should be run in Konsole; this one is
for quick commands and Yoro system commands.
"""

import os
import platform
import sys

from PyQt6.QtCore import QProcess
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6.QtWidgets import (QApplication, QLineEdit, QMainWindow,
                             QPlainTextEdit, QVBoxLayout, QWidget)

from yoroapps import style

BANNER = r"""__   __               ___  ____
\ \ / /__  _ __ ___  / _ \/ ___|
 \ V / _ \| '__/ _ \| | | \___ \
  | | (_) | | | (_) | |_| |___) |
  |_|\___/|_|  \___/ \___/|____/
Yoro Консоль. 'yoro-help' — команды YoroOS, остальное — обычный bash.
"""


class Console(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yoro Консоль")
        self.resize(820, 520)
        self.cwd = os.path.expanduser("~")
        self.history = []
        self.history_pos = -1
        self.process = None

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Noto Sans Mono", 10))

        self.input = QLineEdit()
        self.input.setFont(QFont("Noto Sans Mono", 10))
        self.input.setPlaceholderText("Команда… (Enter — выполнить)")
        self.input.returnPressed.connect(self._run)

        layout = QVBoxLayout()
        layout.addWidget(self.output, 1)
        layout.addWidget(self.input)
        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._print(BANNER)
        self._prompt()
        self.input.setFocus()

    def _print(self, text):
        self.output.appendPlainText(text.rstrip("\n"))

    def _prompt(self):
        self._print(f"yoro@YoroOS:{self.cwd}$ ")

    def _run(self):
        cmd = self.input.text().strip()
        self.input.clear()
        if cmd:
            self.history.append(cmd)
            self.history_pos = len(self.history)
        # Echo the command after the prompt line.
        block = self.output.document().lastBlock()
        self.output.moveCursor(QTextCursor.MoveOperation.End)
        self.output.insertPlainText(cmd + "\n")
        _ = block

        if not cmd:
            self._prompt()
            return
        if cmd == "clear":
            self.output.clear()
            self._prompt()
            return
        if cmd == "exit":
            self.close()
            return
        if cmd == "cd" or cmd.startswith("cd "):
            target = cmd[2:].strip() or os.path.expanduser("~")
            target = os.path.normpath(
                os.path.join(self.cwd, os.path.expanduser(target)))
            if os.path.isdir(target):
                self.cwd = target
            else:
                self._print(f"cd: нет такой папки: {target}")
            self._prompt()
            return
        if cmd == "yoro-help":
            self._print(
                "Команды YoroOS:\n"
                "  yoro           — о системе\n"
                "  yoro-apps      — список Yoro-приложений\n"
                "  yoro-help      — эта справка\n"
                "  clear, cd, exit — как обычно\n"
                "Остальные команды выполняет bash.")
            self._prompt()
            return
        if cmd == "yoro":
            self._print("YoroOS Desktop (Debian + Linux)")
            self._print(f"Ядро Linux: {platform.release()} "
                        f"({platform.machine()})")
            self._prompt()
            return
        if cmd == "yoro-apps":
            self._print("yoro-notepad, yoro-files, yoro-media, yoro-settings,"
                        " yoro-console, yoro-computer, yoro-trash,"
                        " matronix-browser")
            self._prompt()
            return

        self.input.setEnabled(False)
        proc = QProcess(self)
        proc.setWorkingDirectory(self.cwd)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(
            lambda: self.output.insertPlainText(
                bytes(proc.readAllStandardOutput()).decode(
                    "utf-8", "replace")))
        proc.finished.connect(self._finished)
        self.process = proc
        proc.start("/bin/bash", ["-c", cmd])

    def _finished(self, code, _status):
        if self.process is not None:
            rest = bytes(self.process.readAllStandardOutput()).decode(
                "utf-8", "replace")
            if rest:
                self.output.insertPlainText(rest)
        if code != 0:
            self._print(f"[код выхода {code}]")
        self.process = None
        self.input.setEnabled(True)
        self.input.setFocus()
        self._prompt()

    def keyPressEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Up and self.history:
            self.history_pos = max(0, self.history_pos - 1)
            self.input.setText(self.history[self.history_pos])
            return
        if event.key() == Qt.Key.Key_Down and self.history:
            self.history_pos = min(len(self.history), self.history_pos + 1)
            self.input.setText(
                self.history[self.history_pos]
                if self.history_pos < len(self.history) else "")
            return
        super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    style.setup_app(app)
    app.setStyleSheet(style.get_stylesheet())
    window = Console()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
