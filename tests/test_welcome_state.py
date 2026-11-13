"""Preference and first-run logic without a graphical session."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from yoroapps import style, welcome_state


class WelcomeStateTest(unittest.TestCase):
    def test_first_run_and_import(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'XDG_CONFIG_HOME': td + '/config', 'XDG_DATA_HOME': td + '/data'}):
            self.assertTrue(welcome_state.is_first_run())
            welcome_state.mark_seen()
            self.assertFalse(welcome_state.is_first_run())
            source = Path(td) / 'greeting.mp3'; source.write_bytes(b'example')
            welcome_state.import_sound(source)
            self.assertEqual(welcome_state.sound_path().read_bytes(), b'example')
            with self.assertRaises(ValueError):
                welcome_state.import_sound(Path(td) / 'bad.wav')
            self.assertEqual(welcome_state.sound_path().read_bytes(), b'example')

    def test_preferences_are_preserved_and_validated(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {'XDG_CONFIG_HOME': td}):
            style.save_mode('dark'); style.save_accent('#168e97'); style.save_preferences(welcome_audio=False)
            self.assertEqual(style.load_mode(), 'dark')
            self.assertEqual(style.load_accent(), '#168e97')
            self.assertFalse(style.load_preferences()['welcome_audio'])
            self.assertIn('#17202d', style.get_stylesheet())
            with self.assertRaises(ValueError): style.save_accent('invalid')
            with self.assertRaises(ValueError): style.save_mode('other')
