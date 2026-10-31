"""
Freedesktop Trash implementation (shared by yoro-files and yoro-trash).

Implements the ~/.local/share/Trash layout from the freedesktop.org
Trash specification so files deleted in Yoro apps appear in KDE's
trash (and vice versa).
"""

import datetime
import os
import shutil
import urllib.parse


def trash_root():
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "Trash")


def _dirs():
    root = trash_root()
    files = os.path.join(root, "files")
    info = os.path.join(root, "info")
    os.makedirs(files, exist_ok=True)
    os.makedirs(info, exist_ok=True)
    return files, info


def _unique_name(files_dir, info_dir, name):
    candidate = name
    counter = 2
    while (os.path.exists(os.path.join(files_dir, candidate)) or
           os.path.exists(os.path.join(info_dir, candidate + ".trashinfo"))):
        stem, ext = os.path.splitext(name)
        candidate = f"{stem} ({counter}){ext}"
        counter += 1
    return candidate


def move_to_trash(path):
    """Move a file/directory to the trash. Returns the trash name used."""
    path = os.path.abspath(path)
    files_dir, info_dir = _dirs()
    name = _unique_name(files_dir, info_dir, os.path.basename(path))
    deletion_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    info_text = ("[Trash Info]\n"
                 f"Path={urllib.parse.quote(path, safe='/')}\n"
                 f"DeletionDate={deletion_date}\n")
    with open(os.path.join(info_dir, name + ".trashinfo"), "w",
              encoding="utf-8") as f:
        f.write(info_text)
    shutil.move(path, os.path.join(files_dir, name))
    return name


def list_trash():
    """Return [{name, original_path, deletion_date, trash_path}, ...]."""
    files_dir, info_dir = _dirs()
    items = []
    for info_name in sorted(os.listdir(info_dir)):
        if not info_name.endswith(".trashinfo"):
            continue
        name = info_name[: -len(".trashinfo")]
        original, date = "", ""
        try:
            with open(os.path.join(info_dir, info_name),
                      encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Path="):
                        original = urllib.parse.unquote(line[5:].strip())
                    elif line.startswith("DeletionDate="):
                        date = line[len("DeletionDate="):].strip()
        except OSError:
            continue
        items.append({
            "name": name,
            "original_path": original,
            "deletion_date": date,
            "trash_path": os.path.join(files_dir, name),
        })
    return items


def restore(item):
    """Restore a trashed item to its original location."""
    dest = item["original_path"]
    if not dest or os.path.exists(dest):
        raise FileExistsError(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(item["trash_path"], dest)
    _remove_info(item["name"])


def delete_permanently(item):
    path = item["trash_path"]
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.remove(path)
    _remove_info(item["name"])


def empty_trash():
    for item in list_trash():
        delete_permanently(item)


def _remove_info(name):
    _, info_dir = _dirs()
    info_path = os.path.join(info_dir, name + ".trashinfo")
    if os.path.exists(info_path):
        os.remove(info_path)
