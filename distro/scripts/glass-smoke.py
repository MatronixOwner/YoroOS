#!/usr/bin/env python3
"""Check a real X11 Matro Files surface and KWin blur hint in the Live session."""
import ctypes
import os
import sys
sys.path.insert(0, '/usr/share/yoroos')
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication
from yoroapps import style
from yoroapps.files import Files

app = QApplication(sys.argv)
style.setup_app(app)
app.setStyleSheet(style.get_stylesheet())
window = Files(os.path.expanduser('~'))
if not style.enable_glass(app, window):
    raise SystemExit('glass surface unavailable')
if not window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground):
    raise SystemExit('no ARGB surface')
window.show()
app.processEvents()
x = ctypes.CDLL('libX11.so.6')
x.XOpenDisplay.argtypes = [ctypes.c_char_p]; x.XOpenDisplay.restype = ctypes.c_void_p
x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]; x.XInternAtom.restype = ctypes.c_ulong
x.XGetWindowProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_long, ctypes.c_long,
                                 ctypes.c_int, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int),
                                 ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_void_p)]
x.XFree.argtypes = [ctypes.c_void_p]; x.XCloseDisplay.argtypes = [ctypes.c_void_p]
d = x.XOpenDisplay(None)
atom = x.XInternAtom(d, b'_KDE_NET_WM_BLUR_BEHIND_REGION', 0)
type_ = ctypes.c_ulong(); fmt = ctypes.c_int(); n = ctypes.c_ulong(); remaining = ctypes.c_ulong(); data = ctypes.c_void_p()
status = x.XGetWindowProperty(d, int(window.winId()), atom, 0, 1, 0, 0,
                              ctypes.byref(type_), ctypes.byref(fmt), ctypes.byref(n), ctypes.byref(remaining), ctypes.byref(data))
if data: x.XFree(data)
x.XCloseDisplay(d)
if status != 0 or type_.value != 6 or fmt.value != 32:
    raise SystemExit('KWin blur property missing')
print('MATRO_GLASS_SCREENSHOT_READY', flush=True)
QTimer.singleShot(8000, lambda: (print('MATRO_GLASS_OK', flush=True), app.quit()))
sys.exit(app.exec())
