"""Regression checks for MatroOS Game without touching a user's desktop."""
import configparser
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GameBuildTest(unittest.TestCase):
    def test_defaults_merge_without_deleting_other_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'kwinrc').write_text('[Compositing]\nBackend=OpenGL\n[Plugins]\nsomeEffectEnabled=true\n')
            subprocess.run(['python3', str(ROOT / 'game/scripts/write-defaults.py'), directory], check=True)
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read(root / 'kwinrc')
            self.assertEqual(parser['Compositing']['Backend'], 'OpenGL')
            self.assertEqual(parser['Plugins']['someEffectEnabled'], 'true')
            self.assertEqual(parser['Plugins']['blurEnabled'], 'false')
            self.assertEqual(parser['org.kde.kdecoration2']['ButtonsOnRight'], 'IAX')
            self.assertEqual(parser['org.kde.kdecoration2']['ButtonsOnLeft'], '')
            self.assertEqual(parser['org.kde.kdecoration2']['theme'], '__aurorae__svg__YoroArc')
            self.assertIn('Theme=kora', (root / 'kdeglobals').read_text())
            self.assertIn('cursorTheme=Bibata-Modern-Ice', (root / 'kcminputrc').read_text())

    def test_game_is_separate_from_debian_image(self):
        game = (ROOT / 'game/Containerfile').read_text()
        self.assertIn('FROM ghcr.io/ublue-os/bazzite:stable', game)
        self.assertIn('bootc container lint', game)
        self.assertTrue((ROOT / 'game/assets/matroos-game-wallpaper.png').exists())
        self.assertIn('--distribution trixie', (ROOT / 'distro/build-iso.sh').read_text())

    def test_layout_is_full_width_and_not_a_login_reset(self):
        panel = (ROOT / 'game/plasma/default-panel.js').read_text()
        self.assertIn('panel.location = "bottom"', panel)
        self.assertIn('panel.lengthMode = "fill"', panel)
        self.assertIn('panel.floating = false', panel)
        self.assertEqual(panel.count('panel.addWidget("org.kde.plasma.panelspacer")'), 2)
        for app in ('yoro-files.desktop', 'matronix-browser.desktop', 'steam.desktop'):
            self.assertIn(app, panel)
        self.assertIn('matroos-logo', panel)
        self.assertNotIn('.remove()', panel)
        self.assertNotIn('autostart', (ROOT / 'game/scripts/build-image.sh').read_text())


if __name__ == '__main__':
    unittest.main()
