"""Headless widget and functional tests; run with the system PyQt6 packages."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from yoroapps.files import Files
from yoroapps.notepad import Notepad
from yoroapps import calculator, computer, media, paint, settings, trashapp, style

APP = QApplication.instance() or QApplication([])
style.setup_app(APP)
APP.setStyleSheet(style.get_stylesheet())

class WidgetTest(unittest.TestCase):
    def test_svg_icon_theme_is_available(self):
        with tempfile.TemporaryDirectory() as td:
            theme = Path(td) / 'test-icons'
            icons = theme / 'scalable/places'; icons.mkdir(parents=True)
            (theme / 'index.theme').write_text('[Icon Theme]\nName=test-icons\nDirectories=scalable/places\n[scalable/places]\nSize=32\nType=Scalable\n')
            (icons / 'folder.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><rect width="32" height="32" fill="blue"/></svg>')
            oldpaths, oldtheme = QIcon.themeSearchPaths(), QIcon.themeName()
            try:
                QIcon.setThemeSearchPaths([td]); QIcon.setThemeName('test-icons')
                self.assertFalse(QIcon.fromTheme('folder').pixmap(32, 32).isNull())
            finally:
                QIcon.setThemeSearchPaths(oldpaths); QIcon.setThemeName(oldtheme)

    def test_files_navigation_and_views(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / 'folder').mkdir()
            w = Files(str(root))
            self.assertEqual(w.current_path, str(root))
            w.open_path(str(root / 'folder'))
            self.assertEqual(w.current_path, str(root / 'folder'))
            w.go_back(); self.assertEqual(w.current_path, str(root))
            w.go_forward(); self.assertEqual(w.current_path, str(root / 'folder'))
            w.set_view(1); self.assertEqual(w.views.currentIndex(), 1)
            w.search.setText('test'); self.assertEqual(w.model.nameFilters(), ['*test*'])
            w.close()

    def test_notepad_atomic_save_and_failed_save_keeps_changes(self):
        with tempfile.TemporaryDirectory() as td:
            w = Notepad(); w.editor.setPlainText('Привет'); w.editor.document().setModified(True)
            self.assertTrue(w._save_to(str(Path(td) / 'hello.txt')))
            self.assertEqual((Path(td) / 'hello.txt').read_text(), 'Привет')
            w.editor.setPlainText('изменено')
            w.editor.document().setModified(True)
            with patch('yoroapps.notepad.QMessageBox.critical'):
                self.assertFalse(w._save_to(str(Path(td) / 'missing' / 'file.txt')))
            self.assertTrue(w.editor.document().isModified())
            self.assertEqual(w.path, str(Path(td) / 'hello.txt'))
            w.editor.document().setModified(False); w.close()

    def test_all_other_windows_construct(self):
        for cls in (calculator.Calculator, computer.Computer,
                    media.MediaPlayer, paint.Paint, settings.Settings, trashapp.Trash):
            with self.subTest(cls=cls.__name__):
                w = cls(); w.show(); APP.processEvents(); w.close()

if __name__ == '__main__': unittest.main()
