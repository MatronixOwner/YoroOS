"""Explicit local executable launching for the MatroOS file manager.

No shell expansion, privilege escalation, Wine installation, or KIO policy changes.
"""
import os
import shutil
import stat
import subprocess


def executable_kind(path):
    """Identify local program files by content, never execute ordinary documents."""
    try:
        with open(path, 'rb') as f:
            header = f.read(4)
    except OSError:
        return None
    if header.startswith(b'MZ'):
        return 'windows'
    if header == b'\x7fELF':
        return 'native'
    if header.startswith(b'#!'):
        return 'native'
    if path.lower().endswith('.sh') and b'\0' not in header:
        return 'shell'
    return None


def start(path, kind):
    """Launch one approved file as the current user, raising errors to caller."""
    path = os.path.abspath(path)
    if kind == 'windows':
        wine = shutil.which('wine')
        if not wine:
            raise OSError('Это программа Windows (.exe). Для её запуска нужен Wine; он не установлен. Не все программы Windows совместимы с Wine.')
        argv = [wine, path]
    elif kind == 'shell':
        argv = ['/bin/sh', path]
    elif kind == 'native':
        mode = os.stat(path).st_mode
        if not os.access(path, os.X_OK):
            os.chmod(path, mode | stat.S_IXUSR)
        argv = [path]
    else:
        raise ValueError('Неподдерживаемый тип программы')
    subprocess.Popen(argv, cwd=os.path.dirname(path), start_new_session=True, close_fds=True)
