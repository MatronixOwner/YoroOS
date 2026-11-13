"""A calm, light visual language shared by Yoro's Qt applications."""
import json
import os
import re

DEFAULT_ACCENT = "#3478f6"


def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "yoroos", "theme.json")


def load_preferences():
    try:
        with open(config_path(), encoding="utf-8") as f:
            value = json.load(f)
            return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_preferences(**updates):
    data = load_preferences()
    data.update(updates)
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Replace atomically so interrupted writes do not destroy other preferences.
    import tempfile
    fd, temp = tempfile.mkstemp(prefix='.theme-', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_accent():
    value = load_preferences().get("accent", DEFAULT_ACCENT)
    return value if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value) else DEFAULT_ACCENT


def save_accent(accent):
    if not isinstance(accent, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        raise ValueError("Invalid accent color")
    save_preferences(accent=accent)


def load_mode():
    mode = load_preferences().get('mode', 'light')
    return mode if mode in ('light', 'dark') else 'light'


def save_mode(mode):
    if mode not in ('light', 'dark'):
        raise ValueError('Invalid appearance mode')
    save_preferences(mode=mode)


def setup_app(app):
    """Make system icon themes discoverable even without a Qt platform theme."""
    from PyQt6.QtGui import QIcon
    paths = QIcon.themeSearchPaths()
    for path in (os.path.expanduser('~/.local/share/icons'), '/usr/local/share/icons', '/usr/share/icons'):
        if path not in paths:
            paths.append(path)
    QIcon.setThemeSearchPaths(paths)
    if not QIcon.themeName():
        if os.path.exists('/usr/share/icons/kora/index.theme'):
            QIcon.setThemeName('kora')
        elif os.path.exists('/usr/share/icons/breeze/index.theme'):
            QIcon.setThemeName('breeze')


def get_stylesheet(accent=None, mode=None, glass=False):
    accent = accent if isinstance(accent, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", accent) else load_accent()
    sheet = f"""
* {{ font-family: "Noto Sans", sans-serif; font-size: 10pt; color: #222733; }}
QMainWindow, QWidget {{ background-color: #f8f9fb; }}
QWidget#sidebar {{ background-color: #edf0f5; border-right: 1px solid #d9dee8; }}
QWidget#toolbar {{ background-color: #f5f6f9; border-bottom: 1px solid #e0e4eb; }}
QLabel {{ background: transparent; }}
QFrame#settingsCard {{ background: #ffffff; border: 1px solid #dce1e8; border-radius: 12px; }}
QLabel#title {{ font-size: 17pt; font-weight: 700; color: #222733; }}
QLabel#subtitle, QLabel#section {{ color: #747d8e; }}
QLabel#section {{ font-size: 9pt; font-weight: 700; }}
QPushButton, QToolButton {{ background: #ffffff; border: 1px solid #d8dde7;
    border-radius: 7px; padding: 6px 11px; }}
QPushButton:hover, QToolButton:hover {{ background: #eef2f8; border-color: #c3ccda; }}
QPushButton:pressed, QToolButton:pressed, QToolButton:checked {{ background: #dce6f8; }}
QPushButton:disabled, QToolButton:disabled {{ color: #adb4bf; background: #f1f2f4; }}
QPushButton#accent {{ background: {accent}; color: white; border: none; font-weight: 600; }}
QLineEdit, QPlainTextEdit, QTextEdit, QTreeView, QListWidget, QListView {{
    background: white; border: 1px solid #dce1e8; border-radius: 7px;
    selection-background-color: {accent}; selection-color: white; }}
QLineEdit {{ padding: 6px 9px; }}
QPlainTextEdit, QTextEdit {{ padding: 8px; }}
QTreeView::item, QListWidget::item, QListView::item {{ padding: 5px; }}
QTreeView::item:selected, QListWidget::item:selected, QListView::item:selected {{ background: {accent}; color: white; }}
QListWidget#places {{ background: transparent; border: none; outline: none; }}
QListWidget#places::item {{ margin: 1px 5px; padding: 7px; border-radius: 6px; }}
QListWidget#places::item:selected {{ background: #dce6f8; color: #273449; }}
QHeaderView::section {{ background: #f8f9fb; border: none; border-bottom: 1px solid #e5e8ed; padding: 7px; color: #687385; }}
QToolBar {{ background: #f5f6f9; border: none; border-bottom: 1px solid #e0e4eb; spacing: 5px; padding: 7px; }}
QStatusBar {{ background: #f8f9fb; color: #747d8e; }}
QMenuBar, QMenu {{ background: #f8f9fb; }}
QMenu::item:selected {{ background: {accent}; color: white; }}
QSlider::groove:horizontal {{ height: 5px; background: #d9dfe8; border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 15px; margin: -5px 0; border-radius: 7px; background: {accent}; }}
QProgressBar {{ background: #e5eaf1; border: none; border-radius: 5px; text-align: center; height: 12px; }}
QProgressBar::chunk {{ background: {accent}; border-radius: 5px; }}
"""

    if (mode or load_mode()) == 'dark':
        # The terminal retains its own dark VTE styling; these tokens apply to
        # Yoro's Qt applications, not Plasma or the upstream Matronix Browser.
        palette = {
            '#222733': '#e8edf5', '#f8f9fb': '#17202d', '#edf0f5': '#1d2939',
            '#d9dee8': '#344153', '#f5f6f9': '#202c3c', '#e0e4eb': '#344153',
            '#747d8e': '#a5b4c7', '#ffffff': '#293749', '#d8dde7': '#405069',
            '#eef2f8': '#34455b', '#c3ccda': '#596c86', '#dce6f8': '#3d5270',
            '#adb4bf': '#8290a2', '#f1f2f4': '#273341', '#dce1e8': '#405069',
            'background: white': 'background: #253244', '#273449': '#edf3fc',
            '#e5e8ed': '#344153', '#687385': '#a5b4c7', '#d9dfe8': '#405069',
            '#e5eaf1': '#344153',
        }
        for old, new in palette.items():
            sheet = sheet.replace(old, new)
    if glass:
        dark = (mode or load_mode()) == 'dark'
        surface = 'rgba(22, 33, 48, 220)' if dark else 'rgba(240, 248, 255, 215)'
        sidebar = 'rgba(32, 48, 66, 125)' if dark else 'rgba(215, 232, 249, 105)'
        toolbar = 'rgba(30, 43, 60, 125)' if dark else 'rgba(237, 247, 255, 110)'
        opaque = '#17202d' if dark else '#f8f9fb'
        side_opaque = '#1d2939' if dark else '#edf0f5'
        tool_opaque = '#202c3c' if dark else '#f5f6f9'
        sheet = sheet.replace(f'QMainWindow, QWidget {{ background-color: {opaque}; }}',
            f'QWidget {{ background: transparent; }} QMainWindow, QWidget#glassWindow {{ background-color: {surface}; }}')
        sheet = sheet.replace(f'QWidget#sidebar {{ background-color: {side_opaque};',
            f'QWidget#sidebar {{ background-color: {sidebar};')
        sheet = sheet.replace(f'QWidget#toolbar {{ background-color: {tool_opaque};',
            f'QWidget#toolbar {{ background-color: {toolbar};')
        pane = 'rgba(31, 45, 63, 185)' if dark else 'rgba(250, 253, 255, 175)'
        sheet += f'\nQTreeView, QListView, QListWidget {{ background-color: {pane}; }}\n'
        sheet += '\nQListWidget#places { background: transparent; }\n'
        if not dark:
            sheet += '\nQLabel#subtitle, QLabel#section { color: #4d5d72; }\n'
    return sheet


def enable_glass(app, window):
    """Request a blurred ARGB client surface on composited X11; otherwise stay opaque.

    The X11 property is KWin's documented full-window blur request. This does
    not affect the opacity of text or widgets and doesn't change foreign apps.
    """
    from PyQt6.QtCore import Qt
    if app.platformName() != 'xcb':
        return False
    import ctypes
    try:
        x = ctypes.CDLL('libX11.so.6')
        x.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x.XOpenDisplay.restype = ctypes.c_void_p
        x.XDefaultScreen.argtypes = [ctypes.c_void_p]
        x.XDefaultScreen.restype = ctypes.c_int
        x.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x.XInternAtom.restype = ctypes.c_ulong
        x.XGetSelectionOwner.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x.XGetSelectionOwner.restype = ctypes.c_ulong
        x.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                                      ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_void_p, ctypes.c_int]
        x.XFlush.argtypes = [ctypes.c_void_p]
        x.XCloseDisplay.argtypes = [ctypes.c_void_p]
        display = x.XOpenDisplay(None)
        if not display:
            return False
        try:
            screen = x.XDefaultScreen(display)
            selection = x.XInternAtom(display, f'_NET_WM_CM_S{screen}'.encode(), False)
            if not x.XGetSelectionOwner(display, selection):
                return False
            window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            window.setObjectName('glassWindow')
            wid = int(window.winId())
            app.sync()  # Make Qt's XCB window visible to our Xlib connection.
            atom = x.XInternAtom(display, b'_KDE_NET_WM_BLUR_BEHIND_REGION', False)
            # Empty CARDINAL array means blur the entire client region.
            x.XChangeProperty(display, wid, atom, 6, 32, 0, None, 0)
            x.XFlush(display)
            app.setProperty('matroGlass', True)
            app.setStyleSheet(get_stylesheet(glass=True))
            return True
        finally:
            x.XCloseDisplay(display)
    except (OSError, AttributeError):
        return False
