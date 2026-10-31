#!/bin/sh
# Install Yoro desktop applications into a (Debian/Ubuntu) Linux system.
# Usage: sudo ./install.sh        (DESTDIR=/tmp/stage ./install.sh works too)
set -e
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
D="${DESTDIR:-}"

install -d "$D/usr/share/yoroos" "$D/usr/local/bin" "$D/usr/share/applications"
cp -r "$HERE/yoroapps" "$D/usr/share/yoroos/"

for app in notepad files media settings console computer trashapp; do
    bin="yoro-$(echo "$app" | sed 's/trashapp/trash/')"
    cat > "$D/usr/local/bin/$bin" <<EOF
#!/bin/sh
PYTHONPATH="/usr/share/yoroos\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m yoroapps.$app "\$@"
EOF
    chmod +x "$D/usr/local/bin/$bin"
done

cp "$HERE/bin/yoro-browser" "$D/usr/local/bin/yoro-browser"
chmod +x "$D/usr/local/bin/yoro-browser"

cp "$HERE"/applications/*.desktop "$D/usr/share/applications/"
if [ -z "$D" ] && command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications || true
fi
echo "Yoro applications installed (need: python3-pyqt6, python3-pyqt6.qtmultimedia)."
