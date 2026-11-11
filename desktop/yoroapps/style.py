"""A calm, light visual language shared by Yoro's Qt applications."""
import json
import os
import re

DEFAULT_ACCENT = "#3478f6"


def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "yoroos", "theme.json")


def load_accent():
    try:
        with open(config_path(), encoding="utf-8") as f:
            value = json.load(f).get("accent", DEFAULT_ACCENT)
            return value if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value) else DEFAULT_ACCENT
    except (OSError, ValueError, AttributeError):
        return DEFAULT_ACCENT


def save_accent(accent):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        raise ValueError("Invalid accent color")
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"accent": accent}, f)



def setup_app(app):
    """Make system icon themes discoverable even without a Qt platform theme."""
    from PyQt6.QtGui import QIcon
    paths = QIcon.themeSearchPaths()
    for path in (os.path.expanduser('~/.local/share/icons'), '/usr/local/share/icons', '/usr/share/icons'):
        if path not in paths:
            paths.append(path)
    QIcon.setThemeSearchPaths(paths)
    if not QIcon.themeName():
        if os.path.exists('/usr/share/icons/Colloid/index.theme'):
            QIcon.setThemeName('Colloid')
        elif os.path.exists('/usr/share/icons/breeze/index.theme'):
            QIcon.setThemeName('breeze')


def get_stylesheet(accent=None):
    accent = accent if isinstance(accent, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", accent) else load_accent()
    return f"""
* {{ font-family: "Noto Sans", sans-serif; font-size: 10pt; color: #222733; }}
QMainWindow, QWidget {{ background-color: #f8f9fb; }}
QWidget#sidebar {{ background-color: #edf0f5; border-right: 1px solid #d9dee8; }}
QWidget#toolbar {{ background-color: #f5f6f9; border-bottom: 1px solid #e0e4eb; }}
QLabel {{ background: transparent; }}
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
