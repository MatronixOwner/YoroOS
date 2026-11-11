"""Yoro panel setup: brand & shape the KDE Plasma panel ("Пуск").

Used by a first-login autostart job and by the Settings app.
All changes go through the official Plasma scripting API
(org.kde.PlasmaShell.evaluateScript via qdbus), no config hacking.
"""

import os
import shutil
import subprocess
import sys
import time

LAUNCHERS = [
    "applications:matronix-browser.desktop",
    "applications:yoro-files.desktop",
    "applications:yoro-notepad.desktop",
    "applications:yoro-media.desktop",
    "applications:yoro-paint.desktop",
    "applications:yoro-calculator.desktop",
    "applications:yoro-console.desktop",
    "applications:yoro-computer.desktop",
    "applications:yoro-settings.desktop",
]

WALLPAPER = "/usr/share/wallpapers/YoroOS/gradient-aurora.jpg"


def _qdbus():
    for name in ("qdbus6", "qdbus", "qdbus-qt6"):
        path = shutil.which(name)
        if path:
            return path
    for path in ("/usr/lib/qt6/bin/qdbus",):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def run_plasma_script(script):
    """Evaluate a Plasma JS snippet. Returns True on success."""
    qdbus = _qdbus()
    if not qdbus:
        return False
    try:
        result = subprocess.run(
            [qdbus, "org.kde.plasmashell", "/PlasmaShell",
             "org.kde.PlasmaShell.evaluateScript", script],
            capture_output=True, timeout=15)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _launchers_js():
    items = ",".join(f'"{x}"' for x in LAUNCHERS)
    return f"[{items}]"


def apply_panel_preset(location="bottom", height=46):
    """Brand the existing panel: position, height, start icon, pins."""
    script = f"""
var ps = panels();
for (var i = 0; i < ps.length; i++) {{
    var p = ps[i];
    p.location = "{location}";
    p.height = {int(height)};
    var ws = p.widgets();
    for (var j = 0; j < ws.length; j++) {{
        var w = ws[j];
        if (w.type == "org.kde.plasma.kickoff" ||
            w.type == "org.kde.plasma.kicker") {{
            w.currentConfigGroup = ["General"];
            w.writeConfig("icon", "yoro-logo");
            w.reloadConfig();
        }}
        if (w.type == "org.kde.plasma.icontasks" ||
            w.type == "org.kde.plasma.taskmanager") {{
            w.currentConfigGroup = ["General"];
            w.writeConfig("launchers", {_launchers_js()});
            w.reloadConfig();
        }}
    }}
}}
"""
    return run_plasma_script(script)


def set_wallpaper(path):
    tool = shutil.which("plasma-apply-wallpaperimage")
    if not tool or not os.path.exists(path):
        return False
    try:
        return subprocess.run([tool, path], capture_output=True,
                              timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _marker_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "yoroos", "panel-setup-done")


def main():
    """First-login job: brand panel + set Yoro wallpaper once."""
    marker = _marker_path()
    if os.path.exists(marker):
        return
    ok = False
    # Plasma may not have acquired its D-Bus name at the autostart phase.
    for attempt in range(30):
        if apply_panel_preset():
            ok = True
            break
        if attempt < 29:
            time.sleep(1)
    if ok:
        set_wallpaper(WALLPAPER)
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as f:
            f.write("done\n")


if __name__ == "__main__":
    sys.exit(main())
