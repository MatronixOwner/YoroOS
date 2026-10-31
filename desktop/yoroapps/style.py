"""Shared look & feel for all YoroOS desktop applications."""

import json
import os

DEFAULT_ACCENT = "#3daee9"  # KDE Breeze blue


def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "yoroos", "theme.json")


def load_accent():
    try:
        with open(config_path(), encoding="utf-8") as f:
            return json.load(f).get("accent", DEFAULT_ACCENT)
    except (OSError, ValueError):
        return DEFAULT_ACCENT


def save_accent(accent):
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"accent": accent}, f)


def get_stylesheet(accent=None):
    accent = accent or load_accent()
    return f"""
* {{
    font-family: "Noto Sans", "Segoe UI", sans-serif;
    font-size: 10.5pt;
}}
QMainWindow, QWidget {{
    background: #1b1e24;
    color: #e8eaed;
}}
QPushButton {{
    background: #2a2e37;
    border: 1px solid #3a3f4b;
    border-radius: 8px;
    padding: 6px 14px;
}}
QPushButton:hover {{ background: #333947; border-color: {accent}; }}
QPushButton:pressed {{ background: {accent}; color: #10131a; }}
QPushButton#accent {{
    background: {accent};
    color: #10131a;
    border: none;
    font-weight: bold;
}}
QLineEdit, QPlainTextEdit, QTextEdit, QTreeView, QListWidget, QListView {{
    background: #12151b;
    border: 1px solid #2e333f;
    border-radius: 8px;
    selection-background-color: {accent};
    selection-color: #10131a;
}}
QTreeView::item:selected, QListWidget::item:selected {{
    background: {accent};
    color: #10131a;
}}
QHeaderView::section {{
    background: #232733;
    border: none;
    padding: 4px;
}}
QToolBar {{
    background: #20242e;
    border-bottom: 1px solid #2e333f;
    spacing: 4px;
    padding: 4px;
}}
QStatusBar {{ background: #20242e; color: #9aa3b2; }}
QLabel#title {{ font-size: 16pt; font-weight: bold; color: {accent}; }}
QLabel#subtitle {{ color: #9aa3b2; }}
QSlider::groove:horizontal {{
    height: 6px; background: #2e333f; border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 16px; margin: -5px 0; border-radius: 8px; background: {accent};
}}
QProgressBar {{
    background: #12151b; border: 1px solid #2e333f; border-radius: 6px;
    text-align: center; height: 14px;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 5px; }}
"""
