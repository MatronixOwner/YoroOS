"""File operations used by Yoro Files, isolated for testing."""
import os
import shutil


def valid_name(name):
    return bool(name and name not in ('.', '..') and os.path.basename(name) == name and '\x00' not in name)


def rename(path, name):
    if not valid_name(name):
        raise ValueError('Недопустимое имя')
    dest = os.path.join(os.path.dirname(path), name)
    if os.path.abspath(dest) == os.path.abspath(path):
        return path
    if os.path.lexists(dest):
        raise FileExistsError(dest)
    os.rename(path, dest)
    return dest


def copy_or_move(sources, destination, move=False):
    """Copy/move without intentionally overwriting; return per-item failures."""
    errors = []
    if not os.path.isdir(destination):
        return [(destination, 'Папка назначения недоступна')]
    for src in sources:
        src = os.path.abspath(src)
        dest = os.path.join(destination, os.path.basename(src))
        try:
            if not os.path.lexists(src):
                raise FileNotFoundError(src)
            if os.path.lexists(dest):
                raise FileExistsError('Уже существует: ' + dest)
            if os.path.isdir(src) and not os.path.islink(src):
                if os.path.commonpath([os.path.realpath(src), os.path.realpath(destination)]) == os.path.realpath(src):
                    raise ValueError('Нельзя поместить папку внутрь самой себя')
            if move:
                shutil.move(src, dest)
            elif os.path.islink(src):
                os.symlink(os.readlink(src), dest)
            elif os.path.isdir(src):
                shutil.copytree(src, dest, symlinks=True)
            else:
                shutil.copy2(src, dest)
        except (OSError, ValueError, shutil.Error) as exc:
            errors.append((src, str(exc)))
    return errors
