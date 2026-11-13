"""Program launching never invokes a shell to expand the chosen path."""
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from yoroapps import launch

class LaunchTest(unittest.TestCase):
    def test_detects_programs_not_documents(self):
        with tempfile.TemporaryDirectory() as td:
            for name, data, kind in [('a', b'\x7fELFtest', 'native'), ('a.sh', b'echo ok', 'shell'),
                                     ('script', b'#!/bin/sh\n', 'native'), ('a.exe', b'MZtest', 'windows'),
                                     ('note.txt', b'hello', None), ('fake.exe', b'plain', None)]:
                path = Path(td) / name; path.write_bytes(data)
                self.assertEqual(launch.executable_kind(str(path)), kind)

    def test_native_exec_no_shell_and_uses_selected_filename(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'a; touch NOPE'
            path.write_bytes(b'#!/bin/sh\n'); path.chmod(0o600)
            with patch.object(launch.subprocess, 'Popen') as popen:
                launch.start(str(path), 'native')
            self.assertTrue(path.stat().st_mode & stat.S_IXUSR)
            self.assertEqual(popen.call_args.args[0], [str(path)])
            self.assertEqual(popen.call_args.kwargs['cwd'], td)
            self.assertNotIn('shell', popen.call_args.kwargs)

    def test_windows_needs_wine_and_shell_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'demo file.sh'; path.write_text('echo ok')
            with patch.object(launch.subprocess, 'Popen') as popen:
                launch.start(str(path), 'shell')
                self.assertEqual(popen.call_args.args[0], ['/bin/sh', str(path)])
            with patch.object(launch.shutil, 'which', return_value=None):
                with self.assertRaisesRegex(OSError, 'Wine'):
                    launch.start(str(path), 'windows')
