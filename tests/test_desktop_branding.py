import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


menus = load('yoro_menus', ROOT / 'distro/scripts/hide-foreign-menu-items.py')
panel = load('yoro_panel', ROOT / 'desktop/yoroapps/panelsetup.py')


class MenuTest(unittest.TestCase):
    def test_overrides_only_foreign_applications(self):
        with tempfile.TemporaryDirectory() as td:
            source, dest = Path(td) / 'apps', Path(td) / 'override'
            source.mkdir()
            (source / 'foreign.desktop').write_text('[Desktop Entry]\nName=Foreign\nNoDisplay=false\nExec=foreign\n[Desktop Action A]\nName=Test\n')
            (source / 'yoro-files.desktop').write_text('[Desktop Entry]\nName=Yoro\n')
            (source / 'matronix-browser.desktop').write_text('[Desktop Entry]\nName=Browser\n')
            (source / 'matronix-launcher.desktop').write_text('[Desktop Entry]\nName=Launcher\n')
            self.assertEqual(menus.run(source, dest), 1)
            s = (dest / 'foreign.desktop').read_text()
            self.assertIn('NoDisplay=true\n', s)
            self.assertNotIn('NoDisplay=false', s)
            self.assertIn('Exec=foreign', s)
            self.assertFalse((dest / 'yoro-files.desktop').exists())
            self.assertFalse((dest / 'matronix-browser.desktop').exists())
            self.assertFalse((dest / 'matronix-launcher.desktop').exists())

    def test_unparseable_skipped(self):
        self.assertIsNone(menus.transform('[Other]\nName=Something\n'))


class PanelTest(unittest.TestCase):
    def test_dock_layout_is_centered_floating_and_opaque(self):
        with patch.object(panel, 'run_plasma_script', return_value=True) as run:
            self.assertTrue(panel.apply_desktop_layout())
        script = run.call_args.args[0]
        for fragment in ('dock.alignment = "center"', 'dock.lengthMode = "fit"',
                         'dock.floating = true', 'dock.opacity = "opaque"',
                         'top.floating = false', 'top.opacity = "opaque"',
                         'applications:matronix-launcher.desktop'):
            self.assertIn(fragment, script)

    def test_retries_until_plasma_ready(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.object(panel, '_marker_path', return_value=str(Path(td) / 'sub' / 'marker')), \
             patch.object(panel, 'apply_desktop_layout', side_effect=[False, False, True]) as apply, \
             patch.object(panel, 'set_wallpaper', return_value=True), \
             patch.object(panel.time, 'sleep'):
            panel.main()
            self.assertEqual(apply.call_count, 3)
            self.assertTrue((Path(td) / 'sub' / 'marker').exists())

    def test_no_marker_if_plasma_unavailable(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.object(panel, '_marker_path', return_value=str(Path(td) / 'marker')), \
             patch.object(panel, 'apply_desktop_layout', return_value=False), \
             patch.object(panel, 'set_wallpaper', return_value=False), \
             patch.object(panel.time, 'sleep'):
            panel.main()
            self.assertFalse((Path(td) / 'marker').exists())

if __name__ == '__main__':
    unittest.main()
