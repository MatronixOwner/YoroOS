#!/bin/bash
# Build the YoroOS Desktop live ISO (Debian 13 + KDE Plasma + Yoro apps).
#
# Runs on a Debian/Ubuntu host with network access:
#     sudo apt install live-build xorriso squashfs-tools syslinux \
#         isolinux grub-pc-bin grub-efi-amd64-bin shim-signed
#     sudo ./distro/build-iso.sh [output-dir]
#
# Result: <output-dir>/yoroos-desktop-amd64.iso (+ .sha256)
# UEFI Live image for Hyper-V Gen2. Secure Boot behavior is not yet verified.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root (live-build needs chroot)." >&2
    exit 1
fi

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
OUT_DIR="${1:-$REPO_ROOT/out}"
WORK_DIR="$REPO_ROOT/distro/work"

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR" "$OUT_DIR"
# OUT_DIR may be relative (e.g. "out" from CI): make it absolute BEFORE
# changing into WORK_DIR, or the final copy of the ISO will fail.
OUT_DIR=$(CDPATH= cd -- "$OUT_DIR" && pwd)
cd "$WORK_DIR"

lb config \
    --mode debian \
    --distribution trixie \
    --binary-images iso-hybrid \
    --bootloaders "grub-efi" \
    --archive-areas "main contrib non-free non-free-firmware" \
    --apt-recommends false \
    --debian-installer false \
    --memtest none \
    --iso-application "YoroOS Desktop" \
    --iso-volume "YOROOS" \
    --bootappend-live "boot=live components username=yoro hostname=yoroos locales=ru_RU.UTF-8,en_US.UTF-8 keyboard-layouts=us,ru console=tty0 console=ttyS0,115200n8"

# ---- package selection -------------------------------------------------
mkdir -p config/package-lists
cat > config/package-lists/yoro.list.chroot <<'EOF'
# Minimal Debian Live plus Plasma shell. The kernel/userspace are Linux.
linux-image-amd64
live-boot
live-config
live-config-systemd
# live-config only recommends this: without it the live user is not created.
user-setup
initramfs-tools
kmod
# Plasma shell, X11 session and Hyper-V-friendly graphics/input.
plasma-desktop
plasma-workspace
plasma-integration
kwin-x11
# In trixie Aurorae is in kwin-common, not a separate package.
kwin-common
plasma-nm
plasma-pa
powerdevil
kscreen
systemsettings
polkit-kde-agent-1
xdg-desktop-portal
xdg-desktop-portal-kde
sddm
sddm-theme-breeze
breeze-icon-theme
qt6-svg-plugins
qt6-translations-l10n
xorg
# Mesa software rendering keeps compositing available on Hyper-V without 3D.
libgl1-mesa-dri
libglx-mesa0
libegl-mesa0
xserver-xorg-video-fbdev
xserver-xorg-input-libinput
dbus-x11
upower
udisks2
qdbus-qt6
# Yoro apps runtime (incl. Matronix Browser engine)
python3-pyqt6
python3-pyqt6.qtmultimedia
python3-gi
gir1.2-gtk-3.0
gir1.2-vte-2.91
# Matronix Browser runtime (author's own browser, PySide6)
python3-pyside6.qtcore
python3-pyside6.qtgui
python3-pyside6.qtwidgets
python3-pyside6.qtsvg
python3-pyside6.qtwebchannel
python3-pyside6.qtwebenginecore
python3-pyside6.qtwebenginewidgets
python3-cryptography
# System basics
network-manager
pipewire
pipewire-pulse
wireplumber
sudo
xdg-utils
fonts-noto
fonts-noto-color-emoji
fonts-liberation
locales
keyboard-configuration
console-setup
EOF

# ---- Yoro apps & branding into the image --------------------------------
INC=config/includes.chroot
mkdir -p "$INC/usr/share/yoroos" "$INC/usr/local/bin" "$INC/usr/share/applications"
cp -r "$REPO_ROOT/desktop/yoroapps" "$INC/usr/share/yoroos/"
cp "$REPO_ROOT"/desktop/applications/*.desktop "$INC/usr/share/applications/"
mkdir -p "$INC/usr/share/icons/hicolor/scalable/apps" "$INC/usr/share/wallpapers/YoroOS" "$INC/etc/xdg/autostart"
cp "$REPO_ROOT"/desktop/icons/*.svg "$INC/usr/share/icons/hicolor/scalable/apps/"
cp "$REPO_ROOT"/desktop/wallpapers/*.jpg "$INC/usr/share/wallpapers/YoroOS/"
# Optional, separately licensed recording. Never download voices at build/login.
if [ -f "$REPO_ROOT/desktop/sounds/welcome.mp3" ]; then
    mkdir -p "$INC/usr/share/yoroos/sounds"
    cp "$REPO_ROOT/desktop/sounds/welcome.mp3" "$INC/usr/share/yoroos/sounds/welcome.mp3"
fi
# Window decorations and license are included even when external themes are absent.
mkdir -p "$INC/usr/share/aurorae/themes" "$INC/usr/share/doc/yoroos/themes" "$INC/etc/skel/.config"
cp -r "$REPO_ROOT/desktop/themes/WhiteSur" "$INC/usr/share/aurorae/themes/"
cp "$REPO_ROOT/desktop/themes/"{SOURCES.txt,LICENSE-WhiteSur.txt} "$INC/usr/share/doc/yoroos/themes/"
# KWin normally disables animations on llvmpipe, the common VM renderer.
# Allow a user-supplied 0 to disable them again on slower machines.
mkdir -p "$INC/etc/xdg/plasma-workspace/env"
cat > "$INC/etc/xdg/plasma-workspace/env/yoro-effects.sh" <<'EOENV'
export KWIN_EFFECTS_FORCE_ANIMATIONS="${KWIN_EFFECTS_FORCE_ANIMATIONS:-1}"
EOENV
cat > "$INC/etc/skel/.config/kwinrc" <<'EOKWIN'
[org.kde.kdecoration2]
library=org.kde.kwin.aurorae
theme=__aurorae__svg__WhiteSur
ButtonsOnLeft=XIA
ButtonsOnRight=
[Plugins]
magiclampEnabled=true
minimizeanimationEnabled=false
scaleEnabled=true
[Effect-magiclamp]
AnimationDuration=420
EOKWIN
cat > "$INC/etc/xdg/autostart/yoro-panel-setup.desktop" <<'EOS'
[Desktop Entry]
Type=Application
Name=Yoro Panel Setup
Exec=yoro-panel-setup
OnlyShowIn=KDE;
X-KDE-autostart-phase=2
NoDisplay=true
EOS

cat > "$INC/etc/xdg/autostart/yoro-welcome.desktop" <<'EOS'
[Desktop Entry]
Type=Application
Name=Yoro Welcome
Exec=yoro-welcome
OnlyShowIn=KDE;
X-KDE-autostart-phase=2
NoDisplay=true
EOS

for pair in notepad:yoro-notepad files:yoro-files media:yoro-media \
        settings:yoro-settings console:yoro-console computer:yoro-computer \
        trashapp:yoro-trash calculator:yoro-calculator paint:yoro-paint \
        panelsetup:yoro-panel-setup welcome:yoro-welcome; do
    app="${pair%%:*}"; bin="${pair##*:}"
    cat > "$INC/usr/local/bin/$bin" <<EOF
#!/bin/sh
PYTHONPATH="/usr/share/yoroos" exec python3 -m yoroapps.$app "\$@"
EOF
    chmod +x "$INC/usr/local/bin/$bin"
done

# Matronix Browser (vendored, see desktop/matronix-browser/SOURCE.txt)
mkdir -p "$INC/usr/share/matronix-browser"
cp "$REPO_ROOT/desktop/matronix-browser/matronix.py" "$INC/usr/share/matronix-browser/"
cp -r "$REPO_ROOT/desktop/matronix-browser/assets" "$INC/usr/share/matronix-browser/"
cat > "$INC/usr/local/bin/matronix-browser" <<'EOFM'
#!/bin/sh
exec python3 /usr/share/matronix-browser/matronix.py "$@"
EOFM
chmod +x "$INC/usr/local/bin/matronix-browser"

# The image is live-only; auto-login into the Plasma X11 session in the VM.
# X11 is selected explicitly and kwin-x11 is installed (not a recommends).
mkdir -p "$INC/etc/sddm.conf.d" "$INC/etc/initramfs-tools" "$INC/usr/lib/yoroos" "$INC/usr/lib/live/config"
cp "$REPO_ROOT/distro/live-config/9999-yoro-sddm" "$INC/usr/lib/live/config/9999-yoro-sddm"
chmod +x "$INC/usr/lib/live/config/9999-yoro-sddm"
cat > "$INC/etc/sddm.conf.d/90-yoro-live.conf" <<'EOSDDM'
[Autologin]
User=yoro
Session=plasmax11.desktop
Relogin=false
EOSDDM
# Modules required to see Hyper-V Gen2 synthetic storage, mouse and keyboard.
cat > "$INC/etc/initramfs-tools/modules" <<'EOHV'
hv_vmbus
hv_storvsc
hv_netvsc
hid_hyperv
hyperv_keyboard
hyperv_fb
EOHV
cp "$REPO_ROOT/distro/scripts/hide-foreign-menu-items.py" "$INC/usr/lib/yoroos/"

# Optional licensed themes supplied by the CI fetch step (also usable locally).
# Keep upstream licensing inside the image. Without them, Plasma uses Breeze.
if [ -n "${YORO_THEME_INPUT_DIR:-}" ]; then
    THEME_INPUT=$(CDPATH= cd -- "$YORO_THEME_INPUT_DIR" && pwd)
    mkdir -p "$INC/usr/share/icons" "$INC/usr/share/doc/yoroos/themes"
    bash "$THEME_INPUT/colloid/install.sh" --dest "$PWD/$INC/usr/share/icons" --theme default
    cp -a "$THEME_INPUT/Bibata-Modern-Ice" "$INC/usr/share/icons/"
    cp "$THEME_INPUT/colloid/LICENSE" "$INC/usr/share/doc/yoroos/themes/colloid-license.txt"
    cp "$THEME_INPUT/bibata-license.txt" "$INC/usr/share/doc/yoroos/themes/bibata-license.txt"
    cat > "$INC/usr/share/doc/yoroos/themes/SOURCES.txt" <<'EOTHEME'
Colloid: https://github.com/vinceliuice/Colloid-icon-theme
commit ceac6608ecd0e40025cbc2ebbd32bf0e0f4ebc6a (GPL-3.0)
Bibata Modern Ice: https://github.com/ful1e5/Bibata_Cursor
release v2.0.7 (GPL-3.0)
EOTHEME
    mkdir -p "$INC/etc/skel/.config" "$INC/usr/share/icons/default"
    printf '[General]\nColorScheme=BreezeLight\n[Icons]\nTheme=Colloid\n' > "$INC/etc/skel/.config/kdeglobals"
    printf '[Theme]\nname=breeze-light\n' > "$INC/etc/skel/.config/plasmarc"
    printf '[Mouse]\ncursorTheme=Bibata-Modern-Ice\ncursorSize=24\n' > "$INC/etc/skel/.config/kcminputrc"
    printf '[Icon Theme]\nInherits=Bibata-Modern-Ice\n' > "$INC/usr/share/icons/default/index.theme"
fi

# Desktop shortcuts for the live user.
mkdir -p "$INC/etc/skel/Desktop"
cp "$REPO_ROOT/desktop/applications/yoro-computer.desktop" "$INC/etc/skel/Desktop/"
cp "$REPO_ROOT/desktop/applications/matronix-browser.desktop" "$INC/etc/skel/Desktop/"
cp "$REPO_ROOT/desktop/applications/yoro-trash.desktop" "$INC/etc/skel/Desktop/"
chmod +x "$INC"/etc/skel/Desktop/*.desktop

# Matronix Browser is the default web browser.
mkdir -p "$INC/etc/skel/.config"
cat > "$INC/etc/skel/.config/mimeapps.list" <<'EOS2'
[Default Applications]
text/html=matronix-browser.desktop
x-scheme-handler/http=matronix-browser.desktop
x-scheme-handler/https=matronix-browser.desktop
EOS2

# Branding (keep Debian base identity via ID_LIKE for tooling).
cat > "$INC/etc/os-release" <<'EOF'
PRETTY_NAME="YoroOS Desktop 1.0"
NAME="YoroOS Desktop"
VERSION="1.0"
ID=yoroos
ID_LIKE=debian
HOME_URL="https://github.com/MatronixOwner/YoroOS"
EOF

# ---- hooks: configuration and package inventory -------------------------
mkdir -p config/hooks/normal
cat > config/hooks/normal/9100-yoro.hook.chroot <<'EOF'
#!/bin/sh
set -e
# Verify imports in the actual Debian image; Qt WebEngine bindings are split
# across packages and APT recommends are disabled.
python3 -c 'from PySide6.QtSvg import QSvgRenderer; from PySide6.QtWebChannel import QWebChannel; from PySide6.QtWebEngineCore import QWebEnginePage; from PySide6.QtWebEngineWidgets import QWebEngineView'
update-desktop-database /usr/share/applications || true
gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
# Hide launchers for dependency-provided tools without removing components
# required by Plasma, hardware, MIME handlers, or user-installed apps later.
python3 /usr/lib/yoroos/hide-foreign-menu-items.py
# These operations change only the live image being built in the chroot.
systemctl set-default graphical.target
update-initramfs -u -k all
mkdir -p /usr/share/doc/yoroos
dpkg-query -W -f='${Package}\t${Version}\n' > /usr/share/doc/yoroos/packages.tsv
EOF
chmod +x config/hooks/normal/9100-yoro.hook.chroot

# Debian Live defaults to an indefinitely waiting boot menu. Start the Live
# entry automatically while leaving a short window for firmware/utility choice.
cat > config/hooks/normal/9200-yoro-boot.hook.binary <<'EOBOOT'
#!/bin/sh
set -e
[ -f boot/grub/grub.cfg ]
sed -i '/^source \/boot\/grub\/config.cfg/a set default=0\nset timeout=5' boot/grub/grub.cfg
grep -q '^set timeout=5$' boot/grub/grub.cfg
EOBOOT
chmod +x config/hooks/normal/9200-yoro-boot.hook.binary

# ---- build ---------------------------------------------------------------
lb build

ISO_FILE=$(ls ./*.iso | head -n1)
cp "$ISO_FILE" "$OUT_DIR/yoroos-desktop-amd64.iso"
(cd "$OUT_DIR" && sha256sum yoroos-desktop-amd64.iso > yoroos-desktop-amd64.iso.sha256)
echo "Built: $OUT_DIR/yoroos-desktop-amd64.iso"

# The separately developed native kernel is not part of this Linux Live ISO.
