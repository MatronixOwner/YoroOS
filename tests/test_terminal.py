"""Exercise the real PTY and GTK terminal under Xvfb."""
import os
import sys
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from gi.repository import GLib, Gtk
from yoroapps.console import Console


def wait_for(predicate, timeout=12):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if predicate():
            return True
        time.sleep(.05)
    return False


class TerminalTest(unittest.TestCase):
    def test_interactive_shell_and_tabs(self):
        w = Console(shell='/bin/bash'); w.show_all()
        term = w.tabs.get_nth_page(0).get_child()
        self.assertTrue(wait_for(lambda: term.get_pty() is not None), 'No PTY')
        term.feed_child(b"printf 'YORO_PTY_TEST:'; test -t 0 && echo YES\n")
        def contents():
            return term.get_text(None, None)[0]
        self.assertTrue(wait_for(lambda: 'YORO_PTY_TEST:YES' in contents()), contents())
        second = w.new_tab()
        self.assertEqual(w.tabs.get_n_pages(), 2)
        self.assertTrue(wait_for(lambda: second.get_pty() is not None))
        second.feed_child(b'exit\n')
        self.assertTrue(wait_for(lambda: w.tabs.get_n_pages() == 1))
        # Ctrl-C must reach a running program, leaving the shell usable.
        term.feed_child(b'sleep 30\n')
        time.sleep(.5)
        term.feed_child(b'\x03')
        term.feed_child(b"printf 'YORO_AFTER_INTERRUPT\\n'\n")
        self.assertTrue(wait_for(lambda: 'YORO_AFTER_INTERRUPT' in contents()))
        w.destroy()

if __name__ == '__main__': unittest.main()
