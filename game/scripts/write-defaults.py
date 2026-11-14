#!/usr/bin/env python3
"""Merge Plasma defaults without deleting unrelated Bazzite settings."""
import configparser
from pathlib import Path
import sys

root = Path(sys.argv[1])
settings = {
    'kdeglobals': {'KDE': {'LookAndFeelPackage': 'org.kde.breezedark.desktop'},
                   'Icons': {'Theme': 'kora'}},
    'kcminputrc': {'Mouse': {'cursorTheme': 'Bibata-Modern-Ice', 'cursorSize': '24'}},
    'kwinrc': {'org.kde.kdecoration2': {'library': 'org.kde.kwin.aurorae',
                                        'theme': '__aurorae__svg__YoroArc',
                                        'ButtonsOnLeft': '', 'ButtonsOnRight': 'IAX'},
               'Plugins': {'blurEnabled': 'false'}},
}
for name, groups in settings.items():
    path = root / name
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.optionxform = str
    if path.exists():
        config.read(path, encoding='utf-8')
    for group, entries in groups.items():
        if not config.has_section(group):
            config.add_section(group)
        for key, value in entries.items():
            config.set(group, key, value)
    with path.open('w', encoding='utf-8') as dest:
        config.write(dest, space_around_delimiters=False)
