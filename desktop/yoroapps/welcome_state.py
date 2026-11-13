"""Per-user first-run marker and optional welcome recording."""
import os
import shutil
import tempfile
from pathlib import Path


def config_dir():
    return Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'yoroos'


def data_dir():
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'yoroos'


def is_first_run():
    return not (config_dir() / 'welcome-seen').exists()


def mark_seen():
    config_dir().mkdir(parents=True, exist_ok=True)
    (config_dir() / 'welcome-seen').touch()


def sound_path():
    for p in (data_dir() / 'welcome.mp3', Path('/usr/share/yoroos/sounds/welcome.mp3')):
        if p.is_file():
            return p
    return None


def import_sound(source):
    source = Path(source)
    if source.suffix.lower() != '.mp3' or not source.is_file():
        raise ValueError('Выберите существующий файл MP3.')
    if source.stat().st_size > 20 * 1024 * 1024 or source.stat().st_size == 0:
        raise ValueError('Размер MP3 должен быть от 1 байта до 20 МБ.')
    data_dir().mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.welcome-', dir=data_dir())
    try:
        with os.fdopen(fd, 'wb') as output, source.open('rb') as stream:
            shutil.copyfileobj(stream, output)
        os.replace(name, data_dir() / 'welcome.mp3')
    finally:
        if os.path.exists(name):
            os.unlink(name)
