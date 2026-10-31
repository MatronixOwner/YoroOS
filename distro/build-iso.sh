#!/bin/bash
# Build the YoroOS Desktop live ISO (Debian 13 + KDE Plasma + Yoro apps).
#
# Runs on a Debian/Ubuntu host with network access:
#     sudo apt install live-build xorriso squashfs-tools syslinux \
#         isolinux grub-pc-bin grub-efi-amd64-bin shim-signed
#     sudo ./distro/build-iso.sh [output-dir]
#
# Result: <output-dir>/yoroos-desktop-amd64.iso (+ .sha256)
# Boots on BIOS and UEFI (incl. Hyper-V Gen2, signed Debian shim).
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
cd "$WORK_DIR"

lb config \
    --mode debian \
    --distribution trixie \
    --binary-images iso-hybrid \
    --bootloaders "grub-efi" \
    --archive-areas "main contrib non-free non-free-firmware" \
    --apt-recommends true \
    --debian-installer false \
    --memtest none \
    --iso-application "YoroOS Desktop" \
    --iso-volume "YOROOS" \
    --bootappend-live "boot=live components username=yoro hostname=yoroos locales=ru_RU.UTF-8,en_US.UTF-8 keyboard-layouts=us,ru"

# ---- package selection -------------------------------------------------
mkdir -p config/package-lists
cat > config/package-lists/yoro.list.chroot <<'EOF'
# KDE Plasma desktop (beautiful & smooth), login manager
kde-plasma-desktop
plasma-discover
dolphin
konsole
ark
okular
gwenview
spectacle
sddm
# Browser
chromium
# Windows programs support
wine
wine64
winetricks
# Yoro apps runtime
python3-pyqt6
python3-pyqt6.qtmultimedia
# System basics
network-manager
plasma-nm
pipewire
wireplumber
sudo
curl
git
nano
htop
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

for app in notepad files media settings console computer trashapp; do
    bin="yoro-$(echo "$app" | sed 's/trashapp/trash/')"
    cat > "$INC/usr/local/bin/$bin" <<EOF
#!/bin/sh
PYTHONPATH="/usr/share/yoroos" exec python3 -m yoroapps.$app "\$@"
EOF
    chmod +x "$INC/usr/local/bin/$bin"
done
cp "$REPO_ROOT/desktop/bin/yoro-browser" "$INC/usr/local/bin/yoro-browser"
chmod +x "$INC/usr/local/bin/yoro-browser"

# Desktop shortcuts for the live user.
mkdir -p "$INC/etc/skel/Desktop"
cp "$REPO_ROOT/desktop/applications/yoro-computer.desktop" "$INC/etc/skel/Desktop/"
cp "$REPO_ROOT/desktop/applications/yoro-browser.desktop" "$INC/etc/skel/Desktop/"
cp "$REPO_ROOT/desktop/applications/yoro-trash.desktop" "$INC/etc/skel/Desktop/"
chmod +x "$INC"/etc/skel/Desktop/*.desktop

# Branding (keep Debian base identity via ID_LIKE for tooling).
cat > "$INC/etc/os-release" <<'EOF'
PRETTY_NAME="YoroOS Desktop 1.0"
NAME="YoroOS Desktop"
VERSION="1.0"
ID=yoroos
ID_LIKE=debian
HOME_URL="https://github.com/MatronixOwner/YoroOS"
EOF

# ---- hooks: 32-bit Wine etc. --------------------------------------------
mkdir -p config/hooks/normal
cat > config/hooks/normal/9100-yoro.hook.chroot <<'EOF'
#!/bin/sh
set -e
update-desktop-database /usr/share/applications || true
# 32-bit Windows support is optional; do not fail the build over it.
if dpkg --add-architecture i386 2>/dev/null; then
    apt-get update || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y wine32 || true
fi
EOF
chmod +x config/hooks/normal/9100-yoro.hook.chroot

# ---- build ---------------------------------------------------------------
lb build

ISO_FILE=$(ls ./*.iso | head -n1)
cp "$ISO_FILE" "$OUT_DIR/yoroos-desktop-amd64.iso"
(cd "$OUT_DIR" && sha256sum yoroos-desktop-amd64.iso > yoroos-desktop-amd64.iso.sha256)
echo "Built: $OUT_DIR/yoroos-desktop-amd64.iso"

# NOTE (roadmap): our native YoroOS Core kernel will be added as a second
# GRUB boot entry (needs a Multiboot header in kernel/entry.S first).
