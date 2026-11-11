#!/usr/bin/env python3
"""CI-only: run the actual Matronix 1.0.0 window and render local HTML."""
import os
import sys
import faulthandler
faulthandler.enable()
print("SMOKE_IMPORT", flush=True)
sys.path.insert(0, '/usr/share/matronix-browser')
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QApplication
import matronix
if os.environ.get('YORO_TEST_TAB_FIX'):
    from PySide6.QtCore import QSize
    def safe_tab_size(self, index):
        return QSize(matronix.PINNED_WIDTH if self.tabData(index) else 180, 36)
    matronix.TabBar.tabSizeHint = safe_tab_size

print("SMOKE_QAPPLICATION", flush=True)
app = QApplication(sys.argv)
app.setApplicationName('Matronix')
app.setOrganizationName('Matronix')
print("SMOKE_WINDOW", flush=True)
window = matronix.MainWindow()
print("SMOKE_TAB", flush=True)
view = window.add_tab()
print("SMOKE_SHOW", flush=True)
window.show()

def loaded(ok):
    if ok and view.title() == 'Yoro Matronix Smoke':
        print('MATRONIX_RENDER_OK', flush=True)
        app.exit(0)
    elif ok and view.url().host() == 'test.invalid':
        print('MATRONIX_RENDER_FAILED', ok, view.title(), flush=True)
        app.exit(1)

view.loadFinished.connect(loaded)
view.setHtml('<html><head><title>Yoro Matronix Smoke</title></head><body>Matronix test</body></html>', QUrl('https://test.invalid/'))
QTimer.singleShot(90000, lambda: app.exit(2))
sys.exit(app.exec())
