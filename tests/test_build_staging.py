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
            themes = Path(td) / 'themes'
            (themes / 'colloid').mkdir(parents=True)
            (themes / 'colloid/install.sh').write_text('#!/bin/sh\nmkdir -p "$2/Colloid"\necho "[Icon Theme]" > "$2/Colloid/index.theme"\n')
            (themes / 'colloid/LICENSE').write_text('Colloid license')
            (themes / 'bibata-license.txt').write_text('Bibata license')
            (themes / 'Bibata-Modern-Ice').mkdir()
            (themes / 'Bibata-Modern-Ice/index.theme').write_text('[Icon Theme]\nName=Bibata\n')
            env = dict(os.environ, PATH=str(fake) + os.pathsep + os.environ['PATH'], YORO_THEME_INPUT_DIR=str(themes))
            subprocess.run(['bash', str(root / 'distro/build-iso.sh'), str(root / 'out')], env=env, check=True, capture_output=True, text=True)
            work = root / 'distro/work/config'
            packages = (work / 'package-lists/yoro.list.chroot').read_text()
            for package in ('linux-image-amd64', 'live-boot', 'user-setup', 'plasma-integration', 'qt6-svg-plugins', 'kwin-x11', 'xserver-xorg-input-libinput', 'python3-pyside6.qtwebenginewidgets', 'kwin-common', 'libgl1-mesa-dri', 'libglx-mesa0', 'libegl-mesa0', 'python3-gi', 'gir1.2-vte-2.91'):
                self.assertIn('\n' + package + '\n', packages)
            self.assertNotIn('\nnano\n', packages)
            inc = work / 'includes.chroot'
            self.assertTrue((inc / 'usr/share/icons/Colloid/index.theme').exists())
            self.assertTrue((inc / 'usr/share/icons/Bibata-Modern-Ice/index.theme').exists())
            self.assertIn('Theme=Colloid', (inc / 'etc/skel/.config/kdeglobals').read_text())
            self.assertIn('Bibata-Modern-Ice', (inc / 'etc/skel/.config/kcminputrc').read_text())
            self.assertIn('KWIN_EFFECTS_FORCE_ANIMATIONS', (inc / 'etc/xdg/plasma-workspace/env/yoro-effects.sh').read_text())
            kwin = (inc / 'etc/skel/.config/kwinrc').read_text()
            self.assertIn('magiclampEnabled=true', kwin)
            self.assertIn('minimizeanimationEnabled=false', kwin)
            self.assertIn('ButtonsOnLeft=XIA', kwin)
            self.assertTrue((inc / 'usr/share/aurorae/themes/WhiteSur/decoration.svg').exists())
            self.assertTrue((inc / 'usr/share/wallpapers/YoroOS/yoro-horizon.jpg').exists())
            self.assertIn('Session=plasmax11.desktop', (inc / 'etc/sddm.conf.d/90-yoro-live.conf').read_text())
            hook_live = inc / 'usr/lib/live/config/9999-yoro-sddm'
            self.assertTrue(hook_live.exists())
            self.assertTrue(os.access(hook_live, os.X_OK))
            subprocess.run(['sh', '-n', str(hook_live)], check=True)
            self.assertIn('Session=plasmax11.desktop', hook_live.read_text())
            self.assertIn('> /etc/sddm.conf', hook_live.read_text())
            modules = (inc / 'etc/initramfs-tools/modules').read_text()
            self.assertIn('hid_hyperv\n', modules)
            self.assertIn('hyperv_keyboard\n', modules)
            self.assertTrue((inc / 'usr/share/matronix-browser/matronix.py').exists())
            self.assertTrue((inc / 'usr/share/applications/yoro-files.desktop').exists())
            self.assertTrue((inc / 'usr/lib/yoroos/hide-foreign-menu-items.py').exists())
            subprocess.run(['sh', '-n', str(work / 'hooks/normal/9100-yoro.hook.chroot')], check=True)
            hook = work / 'hooks/normal/9200-yoro-boot.hook.binary'
            subprocess.run(['sh', '-n', str(hook)], check=True)
            image_dir = Path(td) / 'image'
            (image_dir / 'boot/grub').mkdir(parents=True)
            (image_dir / 'boot/grub/grub.cfg').write_text('source /boot/grub/config.cfg\nmenuentry test {}\n')
            subprocess.run(['sh', str(hook)], cwd=image_dir, check=True)
            self.assertIn('set timeout=5', (image_dir / 'boot/grub/grub.cfg').read_text())
            self.assertTrue((root / 'out/yoroos-desktop-amd64.iso.sha256').exists())

if __name__ == '__main__': unittest.main()
