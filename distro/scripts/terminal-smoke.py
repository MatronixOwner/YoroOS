#!/usr/bin/env python3
"""CI-only: exercise the installed terminal with a real interactive PTY."""
import sys
sys.path.insert(0, '/usr/share/yoroos')
from yoroapps.console import Console, Gtk, GLib, Vte

window = Console(shell='/bin/bash')
window.show_all()
terminal = window.tabs.get_nth_page(0).get_child()
state = {'sent': False, 'ticks': 0, 'success': False}

def poll():
    state['ticks'] += 1
    if not state['sent'] and terminal.get_pty() is not None:
        state['sent'] = True
        terminal.feed_child(b"printf 'YORO_'; printf 'TERMINAL_OK\\n'\n")
    text = terminal.get_text_format(Vte.Format.TEXT) or ''
    if 'YORO_TERMINAL_OK' in text:
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
