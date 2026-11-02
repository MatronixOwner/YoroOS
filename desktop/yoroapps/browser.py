"""Matronix Browser — YoroOS web browser (Chromium engine, own UI)."""

import os

# Chromium sandbox often fails in live systems; disable it for the
# browser process only (standard practice for embedded QtWebEngine).
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

import sys  # noqa: E402
import urllib.parse  # noqa: E402

from PyQt6.QtCore import QUrl  # noqa: E402
from PyQt6.QtGui import QAction  # noqa: E402
from PyQt6.QtWebEngineCore import QWebEngineProfile  # noqa: E402
from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QFileDialog, QLineEdit,  # noqa: E402
                             QMainWindow, QProgressBar, QPushButton,
                             QTabWidget)

from yoroapps import style  # noqa: E402

HOME_HTML = """<!doctype html><html><head><meta charset="utf-8">
<title>Matronix Browser</title><style>
body{margin:0;font-family:sans-serif;color:#e8eaed;height:100vh;
background:linear-gradient(135deg,#0d1330,#3b1d5e 55%,#0f4c81);
display:flex;align-items:center;justify-content:center}
.card{text-align:center}
h1{font-size:44px;margin:0 0 6px} h1 span{color:#3daee9}
p{color:#b8c4d6}.links a{display:inline-block;margin:8px;padding:12px 18px;
background:rgba(255,255,255,.12);border-radius:12px;color:#fff;
text-decoration:none}.links a:hover{background:rgba(255,255,255,.22)}
</style></head><body><div class="card">
<h1>Matronix <span>Browser</span></h1><p>Браузер YoroOS • быстрый старт</p>
<div class="links">
<a href="https://duckduckgo.com">🔎 Поиск</a>
<a href="https://wikipedia.org">📚 Википедия</a>
<a href="https://github.com/MatronixOwner/YoroOS">💻 YoroOS на GitHub</a>
<a href="https://www.youtube.com">▶ YouTube</a>
</div></div></body></html>"""


def normalize_url(text):
    text = text.strip()
    if not text:
        return None
    if text.startswith(("http://", "https://", "file://", "about:")):
        return QUrl(text)
    if " " in text or "." not in text:
        return QUrl("https://duckduckgo.com/?q=" + urllib.parse.quote(text))
    return QUrl("https://" + text)


class TabView(QWebEngineView):
    def __init__(self, browser):
        super().__init__()
        self.browser = browser

    def createWindow(self, _type):
        return self.browser.add_tab()


class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Matronix Browser")
        self.resize(1100, 720)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self._tab_changed)
        self.setCentralWidget(self.tabs)

        plus = QPushButton("+")
        plus.clicked.connect(lambda: self.add_tab(home=True))
        self.tabs.setCornerWidget(plus)

        toolbar = self.addToolBar("Навигация")
        self.act_back = QAction("←", self)
        self.act_back.triggered.connect(lambda: self._view().back())
        self.act_fwd = QAction("→", self)
        self.act_fwd.triggered.connect(lambda: self._view().forward())
        act_reload = QAction("⟳", self)
        act_reload.setShortcut("Ctrl+R")
        act_reload.triggered.connect(lambda: self._view().reload())
        act_home = QAction("⌂", self)
        act_home.triggered.connect(lambda: self._load_home(self._view()))

        self.address = QLineEdit()
        self.address.setPlaceholderText("Введите адрес или запрос…")
        self.address.returnPressed.connect(self._go)

        toolbar.addAction(self.act_back)
        toolbar.addAction(self.act_fwd)
        toolbar.addAction(act_reload)
        toolbar.addAction(act_home)
        toolbar.addWidget(self.address)

        new_tab = QAction("Новая вкладка", self)
        new_tab.setShortcut("Ctrl+T")
        new_tab.triggered.connect(lambda: self.add_tab(home=True))
        self.addAction(new_tab)
        close_tab = QAction("Закрыть вкладку", self)
        close_tab.setShortcut("Ctrl+W")
        close_tab.triggered.connect(
            lambda: self.close_tab(self.tabs.currentIndex()))
        self.addAction(close_tab)
        focus_addr = QAction("Адресная строка", self)
        focus_addr.setShortcut("Ctrl+L")
        focus_addr.triggered.connect(self._focus_address)
        self.addAction(focus_addr)

        self.progress = QProgressBar()
        self.progress.setMaximumWidth(180)
        self.progress.hide()
        self.statusBar().addPermanentWidget(self.progress)

        (QWebEngineProfile.defaultProfile().downloadRequested
         .connect(self._download))

        start = sys.argv[1] if len(sys.argv) > 1 else None
        view = self.add_tab()
        if start:
            view.load(normalize_url(start))
        else:
            self._load_home(view)

    # ---- tabs ----
    def _view(self):
        return self.tabs.currentWidget()

    def add_tab(self, home=False):
        view = TabView(self)
        index = self.tabs.addTab(view, "Новая вкладка")
        self.tabs.setCurrentIndex(index)
        view.urlChanged.connect(
            lambda url, v=view: self._url_changed(v, url))
        view.titleChanged.connect(
            lambda title, v=view: self._title_changed(v, title))
        view.loadProgress.connect(self._progress)
        view.loadFinished.connect(lambda _ok: self.progress.hide())
        if home:
            self._load_home(view)
        return view

    def close_tab(self, index):
        if self.tabs.count() == 1:
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        widget.deleteLater()

    def _load_home(self, view):
        view.setHtml(HOME_HTML)
        i = self.tabs.indexOf(view)
        if i >= 0:
            self.tabs.setTabText(i, "Matronix — старт")
        self.address.setText("")

    # ---- navigation ----
    def _go(self):
        url = normalize_url(self.address.text())
        if url is not None:
            self._view().load(url)

    def _focus_address(self):
        self.address.setFocus()
        self.address.selectAll()

    def _url_changed(self, view, url):
        if view is self._view():
            text = url.toString()
            self.address.setText("" if text == "about:blank" else text)
            history = view.history()
            self.act_back.setEnabled(history.canGoBack())
            self.act_fwd.setEnabled(history.canGoForward())

    def _title_changed(self, view, title):
        i = self.tabs.indexOf(view)
        if i >= 0:
            self.tabs.setTabText(i, (title or "Вкладка")[:28])
        if view is self._view():
            self.setWindowTitle(f"{title} — Matronix Browser"
                                if title else "Matronix Browser")

    def _progress(self, value):
        if value < 100:
            self.progress.setValue(value)
            self.progress.show()
        else:
            self.progress.hide()

    def _tab_changed(self, _index):
        view = self._view()
        if view is not None:
            self._url_changed(view, view.url())
            self._title_changed(view, view.title())

    # ---- downloads ----
    def _download(self, item):
        suggested = item.suggestedFileName() or "download"
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл",
                                              suggested)
        if not path:
            item.cancel()
            return
        directory, filename = os.path.split(path)
        item.setDownloadDirectory(directory)
        item.setDownloadFileName(filename)
        item.accept()
        self.statusBar().showMessage(f"Скачиваю: {filename}…")
        item.finished.connect(
            lambda: self.statusBar().showMessage(f"Скачано: {filename}"))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Matronix Browser")
    app.setStyleSheet(style.get_stylesheet())
    window = Browser()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
