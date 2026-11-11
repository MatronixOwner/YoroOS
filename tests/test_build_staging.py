"""Validate live-build staging without root, apt, network or building an ISO."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class BuildStagingTest(unittest.TestCase):
    def test_staging_and_boot_configuration(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'repo'
            shutil.copytree(ROOT / 'desktop', root / 'desktop', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT / 'distro', root / 'distro', ignore=shutil.ignore_patterns('work', '__pycache__'))
            fake = Path(td) / 'bin'
            fake.mkdir()
            (fake / 'id').write_text('#!/bin/sh\necho 0\n')
            (fake / 'lb').write_text('#!/bin/sh\n[ "$1" != build ] || touch image.iso\nexit 0\n')
            for p in fake.iterdir(): p.chmod(0o755)
            env = dict(os.environ, PATH=str(fake) + os.pathsep + os.environ['PATH'])
            subprocess.run(['bash', str(root / 'distro/build-iso.sh'), str(root / 'out')], env=env, check=True, capture_output=True, text=True)
            work = root / 'distro/work/config'
            packages = (work / 'package-lists/yoro.list.chroot').read_text()
            for package in ('linux-image-amd64', 'live-boot', 'kwin-x11', 'xserver-xorg-input-libinput', 'python3-pyside6.qtwebengine'):
                self.assertIn('\n' + package + '\n', packages)
            self.assertNotIn('\nnano\n', packages)
            inc = work / 'includes.chroot'
            self.assertIn('Session=plasmax11.desktop', (inc / 'etc/sddm.conf.d/90-yoro-live.conf').read_text())
            modules = (inc / 'etc/initramfs-tools/modules').read_text()
            self.assertIn('hid_hyperv\n', modules)
            self.assertIn('hyperv_keyboard\n', modules)
            self.assertTrue((inc / 'usr/share/matronix-browser/matronix.py').exists())
            self.assertTrue((inc / 'usr/share/applications/yoro-files.desktop').exists())
            self.assertTrue((inc / 'usr/lib/yoroos/hide-foreign-menu-items.py').exists())
            subprocess.run(['sh', '-n', str(work / 'hooks/normal/9100-yoro.hook.chroot')], check=True)
            self.assertTrue((root / 'out/yoroos-desktop-amd64.iso.sha256').exists())

if __name__ == '__main__': unittest.main()
