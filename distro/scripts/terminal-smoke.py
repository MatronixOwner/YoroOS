#!/usr/bin/env python3
"""CI-only: exercise the installed terminal with a real interactive PTY."""
import base64
import sys
sys.path.insert(0, '/usr/share/yoroos')
from yoroapps.console import Console, Gtk, GLib, Vte, Gdk
from gi.repository import GdkPixbuf

window = Console(shell='/bin/bash')
window.show_all()
terminal = window.tabs.get_nth_page(0).get_child()
state = {'sent': False, 'ticks': 0, 'success': False, 'visible_at': None}

def poll():
    state['ticks'] += 1
    if not state['sent'] and terminal.get_pty() is not None:
        state['sent'] = True
        terminal.feed_child(b"printf 'YORO_'; printf 'TERMINAL_OK\\n'\n")
    text = terminal.get_text_format(Vte.Format.TEXT) or ''
    if 'YORO_TERMINAL_OK' in text:
        if state['visible_at'] is None:
            state['visible_at'] = state['ticks']
            return True
        if state['ticks'] < state['visible_at'] + 4:
            return True
        try:
            root = Gdk.get_default_root_window()
            image = Gdk.pixbuf_get_from_window(root, 0, 0, root.get_width(), root.get_height())
            height = max(1, int(image.get_height() * 720 / image.get_width()))
            image = image.scale_simple(720, height, GdkPixbuf.InterpType.BILINEAR)
            success, data = image.save_to_bufferv('jpeg', ['quality'], ['45'])
            if success and len(data) < 32000:
                print('YORO_PREVIEW_BASE64=' + base64.b64encode(data).decode(), flush=True)
        except Exception as exc:
            print('YORO_PREVIEW_ERROR:', exc, flush=True)
        state['success'] = True
        print('YORO_TERMINAL_OK', flush=True)
        window.destroy()
        Gtk.main_quit()
        return False
    if state['ticks'] > 120:
        print('YORO_TERMINAL_FAILED', flush=True)
        window.destroy()
        Gtk.main_quit()
        return False
    return True

GLib.timeout_add(500, poll)
Gtk.main()
sys.exit(0 if state['success'] else 1)
