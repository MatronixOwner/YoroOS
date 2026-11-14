"""Validate live-build staging without root, apt, network or building an ISO."""
import os
import shutil
import subprocess
import tempfile
import tarfile
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
            (fake / 'sha256sum').write_text('#!/bin/sh\nif [ "$1" = -c ]; then cat >/dev/null; exit 0; fi\nexec /usr/bin/sha256sum "$@"\n')
            (fake / 'lb').write_text('#!/bin/sh\n[ "$1" != build ] || touch image.iso\nexit 0\n')
            for p in fake.iterdir(): p.chmod(0o755)
            themes = Path(td) / 'themes'
            kora = themes / 'kora'
            (kora / 'kora/apps/scalable').mkdir(parents=True)
            (kora / 'kora/places/scalable').mkdir(parents=True)
            (kora / 'kora/index.theme').write_text('[Icon Theme]\nName=Kora\nInherits=breeze,hicolor\n')
            for name in ('file-manager', 'utilities-terminal', 'accessories-text-editor', 'preferences-system',
                         'accessories-calculator', 'smplayer', 'gnome-paint', 'preferences-desktop-display'):
                (kora / 'kora/apps/scalable' / (name + '.svg')).write_text('<svg/>')
            (kora / 'kora/places/scalable/user-trash.svg').write_text('<svg/>')
            (kora / 'LICENSE').write_text('Kora license')
            (kora / 'README.md').write_text('Kora upstream sources')
            upstream = themes / 'matronix-launcher-source'
            (upstream / 'program_info').mkdir(parents=True)
            for name in ('LICENSE', 'UPSTREAM_README.md', 'program_info/LICENSE'):
                (upstream / name).write_text('upstream attribution')
            launcher = Path(td) / 'launcher'
            (launcher / 'bin').mkdir(parents=True)
            icon_dir = launcher / 'share/icons/hicolor/256x256/apps'; icon_dir.mkdir(parents=True)
            (icon_dir / 'com.matronixprismlauncher.MatronixPrismLauncher.png').write_bytes(b'PNG fixture')
            for path in (launcher / 'MatronixPrismLauncher', launcher / 'bin/matronixlauncher'):
                path.write_text('#!/bin/sh\nexit 0\n'); path.chmod(0o755)
            (launcher / 'portable.txt').write_text('portable')
            with tarfile.open(themes / 'matronix-launcher.tar.gz', 'w:gz') as tar:
                for path in launcher.iterdir(): tar.add(path, arcname=path.name)
            (themes / 'bibata-license.txt').write_text('Bibata license')
            (themes / 'Bibata-Modern-Ice').mkdir()
            (themes / 'Bibata-Modern-Ice/index.theme').write_text('[Icon Theme]\nName=Bibata\n')
            env = dict(os.environ, PATH=str(fake) + os.pathsep + os.environ['PATH'], YORO_THEME_INPUT_DIR=str(themes))
            subprocess.run(['bash', str(root / 'distro/build-iso.sh'), str(root / 'out')], env=env, check=True, capture_output=True, text=True)
            work = root / 'distro/work/config'
            packages = (work / 'package-lists/yoro.list.chroot').read_text()
            for package in ('linux-image-amd64', 'live-boot', 'user-setup', 'plasma-integration', 'qt6-svg-plugins', 'kwin-x11', 'xserver-xorg-input-libinput', 'python3-pyside6.qtwebenginewidgets', 'kwin-common', 'libgl1-mesa-dri', 'libglx-mesa0', 'libegl-mesa0', 'python3-gi', 'gir1.2-vte-2.91', 'openjdk-21-jre', 'openjdk-25-jre', 'libfuse2t64', 'mesa-utils', 'pipewire-pulse', 'plymouth', 'adwaita-icon-theme'):
                self.assertIn('\n' + package + '\n', packages)
            self.assertNotIn('\nnano\n', packages)
            inc = work / 'includes.chroot'
            self.assertTrue((inc / 'usr/share/icons/kora/index.theme').exists())
            self.assertTrue((inc / 'usr/share/icons/kora/apps/scalable/yoro-console.svg').exists())
            self.assertTrue((inc / 'usr/share/doc/yoroos/themes/kora-license.txt').exists())
            self.assertTrue((inc / 'usr/share/plymouth/themes/yoro/yoro.script').exists())
            self.assertIn('Name=MatroOS', (inc / 'usr/share/plymouth/themes/yoro/yoro.plymouth').read_text())
            self.assertEqual((inc / 'usr/share/icons/hicolor/512x512/apps/matroos-logo.png').read_bytes(),
                             (root / 'desktop/icons/matroos-logo.png').read_bytes())
            os_release = (inc / 'etc/os-release').read_text()
            self.assertIn('PRETTY_NAME="MatroOS Desktop 1.0"', os_release)
            self.assertIn('ID=matroos', os_release)
            self.assertIn('ID_LIKE=debian', os_release)
            self.assertIn('Theme=yoro', (inc / 'etc/plymouth/plymouthd.conf').read_text())
            self.assertTrue((inc / 'usr/share/icons/Bibata-Modern-Ice/index.theme').exists())
            self.assertIn('Theme=kora', (inc / 'etc/skel/.config/kdeglobals').read_text())
            self.assertIn('Bibata-Modern-Ice', (inc / 'etc/skel/.config/kcminputrc').read_text())
            self.assertIn('KWIN_EFFECTS_FORCE_ANIMATIONS', (inc / 'etc/xdg/plasma-workspace/env/yoro-effects.sh').read_text())
            self.assertIn('Exec=yoro-welcome', (inc / 'etc/xdg/autostart/yoro-welcome.desktop').read_text())
            self.assertTrue((inc / 'usr/local/bin/yoro-welcome').exists())
            kwin = (inc / 'etc/skel/.config/kwinrc').read_text()
            self.assertIn('blurEnabled=false', kwin)
            self.assertIn('magiclampEnabled=true', kwin)
            self.assertIn('minimizeanimationEnabled=false', kwin)
            self.assertIn('ButtonsOnLeft=\nButtonsOnRight=IAX', kwin)
            self.assertIn('theme=__aurorae__svg__YoroArc', kwin)
            self.assertTrue((inc / 'usr/share/aurorae/themes/YoroArc/decoration.svg').exists())
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
            self.assertTrue((inc / 'opt/matronixlauncher/MatronixPrismLauncher').exists())
            self.assertFalse((inc / 'opt/matronixlauncher/portable.txt').exists())
            self.assertTrue((inc / 'usr/local/bin/matronix-launcher').exists())
            self.assertTrue((inc / 'usr/share/doc/matronix-launcher/LICENSE').exists())
            self.assertTrue((inc / 'usr/share/applications/matronix-launcher.desktop').exists())
            self.assertTrue((inc / 'usr/share/applications/yoro-files.desktop').exists())
            self.assertTrue((inc / 'usr/lib/yoroos/hide-foreign-menu-items.py').exists())
            audit = work / 'hooks/normal/9100-yoro.hook.chroot'
            subprocess.run(['sh', '-n', str(audit)], check=True)
            self.assertIn('Unexpected antivirus package', audit.read_text())
            self.assertIn('clamav', audit.read_text())
            hook = work / 'hooks/normal/9200-yoro-boot.hook.binary'
            subprocess.run(['sh', '-n', str(hook)], check=True)
            image_dir = Path(td) / 'image'
            (image_dir / 'boot/grub').mkdir(parents=True)
            (image_dir / 'boot/grub/grub.cfg').write_text('source /boot/grub/config.cfg\nmenuentry test {}\n')
            subprocess.run(['sh', str(hook)], cwd=image_dir, check=True)
            self.assertIn('set timeout=5', (image_dir / 'boot/grub/grub.cfg').read_text())
            self.assertTrue((root / 'out/yoroos-desktop-amd64.iso.sha256').exists())

if __name__ == '__main__': unittest.main()
