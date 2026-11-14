#!/usr/bin/env python3
"""Adapt the staged shared applications without changing Debian MatroOS."""
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1])
overrides = Path(sys.argv[2])
shutil.copyfile(overrides / 'panelsetup.py', root / 'panelsetup.py')
replacements = {
    'settings.py': {
        '"/usr/share/wallpapers/YoroOS", "desktop/wallpapers"': '"/usr/share/wallpapers/MatroOSGame"',
        'Меню, индикаторы и часы остаются на верхней панели.': 'Настройте расположение и размер единой панели задач.',
        'В Live-образе настройки и загруженный файл удаляются после выключения. Само приветствие появится снова при следующей загрузке.': 'После установки настройки и загруженный файл сохраняются в вашем профиле.',
    },
    'welcome.py': {
        'Live-сессия: изменения исчезнут после выключения.': 'Ваше пространство для игр и повседневных задач.',
    },
}
for name, changes in replacements.items():
    path = root / name
    data = path.read_text(encoding='utf-8')
    for old, new in changes.items():
        if data.count(old) != 1:
            raise SystemExit(f'{name}: expected text not found exactly once: {old}')
        data = data.replace(old, new)
    path.write_text(data, encoding='utf-8')
