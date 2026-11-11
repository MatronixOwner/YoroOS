#!/usr/bin/env python3
"""CI-only: run the actual Matronix 1.0.0 window and render local HTML."""
import sys
sys.path.insert(0, '/usr/share/matronix-browser')
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QApplication
import matronix

app = QApplication(sys.argv)
app.setApplicationName('Matronix')
app.setOrganizationName('Matronix')
window = matronix.MainWindow()
view = window.add_tab()
window.show()

def loaded(ok):
    if ok and view.title() == 'Yoro Matronix Smoke':
        print('MATRONIX_RENDER_OK', flush=True)
        app.exit(0)
    else:
        print('MATRONIX_RENDER_FAILED', ok, view.title(), flush=True)
        app.exit(1)

view.loadFinished.connect(loaded)
view.setHtml('<html><head><title>Yoro Matronix Smoke</title></head><body>Matronix test</body></html>', QUrl('https://test.invalid/'))
QTimer.singleShot(90000, lambda: app.exit(2))
sys.exit(app.exec())
