#!/bin/sh
# Install Yoro desktop applications into a (Debian/Ubuntu) Linux system.
# Usage: sudo ./install.sh        (DESTDIR=/tmp/stage ./install.sh works too)
set -e
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
D="${DESTDIR:-}"

install -d "$D/usr/share/yoroos" "$D/usr/local/bin" "$D/usr/share/applications"
cp -r "$HERE/yoroapps" "$D/usr/share/yoroos/"

for pair in notepad:yoro-notepad files:yoro-files media:yoro-media \
        settings:yoro-settings console:yoro-console computer:yoro-computer \
        trashapp:yoro-trash calculator:yoro-calculator paint:yoro-paint \
        panelsetup:yoro-panel-setup; do
    app="${pair%%:*}"; bin="${pair##*:}"
    cat > "$D/usr/local/bin/$bin" <<EOF
#!/bin/sh
PYTHONPATH="/usr/share/yoroos\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m yoroapps.$app "\$@"
EOF
    chmod +x "$D/usr/local/bin/$bin"
done

# Matronix Browser (vendored, see matronix-browser/SOURCE.txt)
install -d "$D/usr/share/matronix-browser"
cp "$HERE/matronix-browser/matronix.py" "$D/usr/share/matronix-browser/"
cp -r "$HERE/matronix-browser/assets" "$D/usr/share/matronix-browser/"
cat > "$D/usr/local/bin/matronix-browser" <<'EOFM'
#!/bin/sh
exec python3 /usr/share/matronix-browser/matronix.py "$@"
EOFM
chmod +x "$D/usr/local/bin/matronix-browser"

cp "$HERE"/applications/*.desktop "$D/usr/share/applications/"
install -d "$D/usr/share/icons/hicolor/scalable/apps" "$D/usr/share/wallpapers/YoroOS" "$D/etc/xdg/autostart"
cp "$HERE"/icons/*.svg "$D/usr/share/icons/hicolor/scalable/apps/"
cp "$HERE"/wallpapers/*.jpg "$D/usr/share/wallpapers/YoroOS/"
install -d "$D/usr/share/aurorae/themes" "$D/usr/share/doc/yoroos/themes"
cp -r "$HERE/themes/WhiteSur" "$D/usr/share/aurorae/themes/"
cp "$HERE/themes/SOURCES.txt" "$HERE/themes/LICENSE-WhiteSur.txt" "$D/usr/share/doc/yoroos/themes/"
cat > "$D/etc/xdg/autostart/yoro-panel-setup.desktop" <<'EOF2'
[Desktop Entry]
Type=Application
Name=Yoro Panel Setup
Exec=yoro-panel-setup
OnlyShowIn=KDE;
X-KDE-autostart-phase=2
NoDisplay=true
EOF2
if [ -z "$D" ] && command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications || true
fi
echo "Yoro applications installed (need: python3-pyqt6, python3-pyqt6.qtmultimedia, python3-gi, gir1.2-vte-2.91, python3-pyside6.* for Matronix Browser)."
