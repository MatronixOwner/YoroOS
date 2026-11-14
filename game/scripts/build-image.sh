#!/usr/bin/bash
# Runs only during OCI image construction, not on an installed user machine.
set -euo pipefail
input=${1:?missing build context}

# Keep Bazzite's gaming stack intact. Fedora's packages provide our own apps'
# runtime; missing bindings are fatal in the subsequent Containerfile test.
dnf5 install -y python3-pyqt6 python3-pyside6 python3-gobject gtk3 vte291

a="$input/desktop"
install -d /usr/share/yoroos /usr/share/matronix-browser /usr/share/applications
cp -a "$a/yoroapps" /usr/share/yoroos/
cp -a "$a/matronix-browser/matronix.py" "$a/matronix-browser/assets" /usr/share/matronix-browser/
for pair in notepad:yoro-notepad files:yoro-files media:yoro-media \
    settings:yoro-settings console:yoro-console computer:yoro-computer \
    trashapp:yoro-trash calculator:yoro-calculator paint:yoro-paint; do
    module=${pair%%:*}; binary=${pair##*:}
    printf '#!/bin/sh\nPYTHONPATH="/usr/share/yoroos${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m yoroapps.%s "$@"\n' "$module" > "/usr/bin/$binary"
    chmod 0755 "/usr/bin/$binary"
done
cat > /usr/bin/matronix-browser <<'BROWSER'
#!/bin/sh
exec python3 /usr/share/matronix-browser/matronix.py "$@"
BROWSER
chmod 0755 /usr/bin/matronix-browser
cp "$a"/applications/*.desktop /usr/share/applications/
install -d /usr/share/icons/hicolor/scalable/apps /usr/share/icons/hicolor/512x512/apps
cp "$a"/icons/*.svg /usr/share/icons/hicolor/scalable/apps/
install -m 0644 "$a/icons/matroos-logo.png" /usr/share/icons/hicolor/512x512/apps/matroos-logo.png

# Keep the selected Kora and Bibata artwork and their licenses.
install -d /usr/share/icons /usr/share/doc/matroos-game/themes
cp -a "$input/themes/kora/kora" /usr/share/icons/
cp -a "$input/themes/Bibata-Modern-Ice" /usr/share/icons/
install -m 0644 "$input/themes/kora/LICENSE" /usr/share/doc/matroos-game/themes/kora-license.txt
install -m 0644 "$input/themes/bibata-license.txt" /usr/share/doc/matroos-game/themes/bibata-license.txt
install -d /usr/share/aurorae/themes
cp -a "$a/themes/YoroArc" /usr/share/aurorae/themes/
install -m 0644 "$a/themes/SOURCES.txt" "$a/themes/LICENSE-WhiteSur.txt" /usr/share/doc/matroos-game/themes/
install -d /usr/share/wallpapers/MatroOSGame
install -m 0644 "$input/game/assets/matroos-game-wallpaper.png" /usr/share/wallpapers/MatroOSGame/matroos-game.png

# Change the upstream default-panel template, not existing user configurations.
install -m 0644 "$input/game/plasma/default-panel.js" /usr/share/plasma/layout-templates/org.kde.plasma.desktop.defaultPanel/contents/layout.js
for theme in org.kde.breeze.desktop org.kde.breezedark.desktop org.kde.breezetwilight.desktop; do
    layout="/usr/share/plasma/look-and-feel/$theme/contents/layouts/org.kde.plasma.desktop-layout.js"
    if [[ -f "$layout" ]]; then
        install -m 0644 "$input/game/plasma/desktop-layout.js" "$layout"
    fi
done

# Defaults only; user settings remain free to override these after installation.
install -d /etc/xdg
/usr/bin/python3 "$input/game/scripts/write-defaults.py" /etc/xdg

dnf5 clean all
