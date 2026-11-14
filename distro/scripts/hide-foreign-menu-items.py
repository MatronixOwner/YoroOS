#!/usr/bin/env python3
"""Hide non-Yoro application launchers from menus without removing packages.

XDG searches /usr/local/share before /usr/share; these overrides retain the
original entry's other fields so MIME handlers may still be launched. Only
/usr/share/applications/*.desktop is scanned; services and autostarts untouched.
"""
import argparse
from pathlib import Path


def transform(text):
    lines = text.splitlines(keepends=True)
    output, in_entry, found = [], False, False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('[') and stripped.endswith(']'):
            in_entry = stripped == '[Desktop Entry]'
            output.append(line if line.endswith('\n') else line + '\n')
            if in_entry:
                found = True
                output.append('NoDisplay=true\n')
            continue
        if in_entry and stripped.startswith('NoDisplay='):
            continue
        output.append(line)
    return ''.join(output) if found else None


def run(source, dest):
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(source.glob('*.desktop')):
        if path.name.startswith('yoro-') or path.name in ('matronix-browser.desktop', 'matronix-launcher.desktop'):
            continue
        text = transform(path.read_text(encoding='utf-8', errors='replace'))
        if text is not None:
            (dest / path.name).write_text(text, encoding='utf-8')
            count += 1
    return count


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=Path('/usr/share/applications'))
    p.add_argument('--dest', type=Path, default=Path('/usr/local/share/applications'))
    args = p.parse_args()
    print(f'YoroOS: hid {run(args.source, args.dest)} non-Yoro application launchers')

if __name__ == '__main__':
    main()
