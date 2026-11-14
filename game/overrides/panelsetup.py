"""Game-edition panel controls: retain the single taskbar and user pins."""
import os
import shutil
import subprocess


def _qdbus():
    for command in ('qdbus6', 'qdbus-qt6', 'qdbus'):
        path = shutil.which(command)
        if path:
            return path
    for path in ('/usr/lib64/qt6/bin/qdbus', '/usr/lib/qt6/bin/qdbus'):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def apply_panel_preset(location='bottom', height=54):
    if location not in ('bottom', 'left', 'right'):
        return False
    try:
        height = max(40, min(80, int(height)))
    except (TypeError, ValueError):
        return False
    tool = _qdbus()
    if not tool:
        return False
    # Only adjust existing task panels; leave launchers and user widgets intact.
    script = f'''
var ps = panels();
for (var i = 0; i < ps.length; ++i) {{
    var widgets = ps[i].widgets();
    var tasks = false;
    for (var j = 0; j < widgets.length; ++j) {{
        if (widgets[j].type == "org.kde.plasma.icontasks" ||
            widgets[j].type == "org.kde.plasma.taskmanager") tasks = true;
    }}
    if (tasks) {{
        ps[i].location = "{location}";
        ps[i].height = {height};
        ps[i].lengthMode = "fill";
        ps[i].floating = false;
        ps[i].opacity = "opaque";
    }}
}}
'''
    try:
        return subprocess.run([tool, 'org.kde.plasmashell', '/PlasmaShell',
                               'org.kde.PlasmaShell.evaluateScript', script],
                              capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def set_wallpaper(path):
    tool = shutil.which('plasma-apply-wallpaperimage')
    if not tool or not os.path.isfile(path):
        return False
    try:
        return subprocess.run([tool, path], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
