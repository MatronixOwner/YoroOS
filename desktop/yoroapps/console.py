"""Yoro Terminal — a real interactive terminal, powered by the VTE library."""
import os
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Vte', '2.91')
from gi.repository import Gdk, GLib, Gtk, Pango, Vte

CSS = b'''
window { background: #111a29; color: #e7edf7; }
.header { background: #1b2637; border-bottom: 1px solid #344054; padding: 10px 15px; }
.title { color: #f3f6fc; font-weight: 700; font-size: 13px; }
.subtitle { color: #94a7c1; font-size: 11px; }
.header button { background: #28374c; border: 1px solid #40516a; border-radius: 7px; color: #f3f6fc; padding: 4px 10px; box-shadow: none; }
.header button:hover { background: #364d68; }
notebook > header { background: #172232; border: 0; }
notebook > header tab { background: #172232; color: #96a9c2; border: 0; padding: 9px 16px; }
notebook > header tab:checked { background: #25354a; color: #f5f8ff; box-shadow: inset 0 -2px #7db3ff; }
notebook > stack { background: #111a29; }
terminal { padding: 18px; }
'''


def color(value):
    rgba = Gdk.RGBA()
    if not rgba.parse(value):
        raise ValueError(value)
    return rgba


class Console(Gtk.Window):
    def __init__(self, shell=None):
        super().__init__(title='Терминал')
        self.set_default_size(920, 600)
        self.set_size_request(500, 320)
        self.set_icon_name('yoro-console')
        self.shell = shell or os.environ.get('SHELL') or '/bin/bash'
        self.serial = 0
        self.connect('destroy', self._destroy)
        self.connect('key-press-event', self._key_press)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(root)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.get_style_context().add_class('header')
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label='Терминал', xalign=0)
        title.get_style_context().add_class('title')
        subtitle = Gtk.Label(label='YORO  /  КОМАНДНАЯ СТРОКА', xalign=0)
        subtitle.get_style_context().add_class('subtitle')
        labels.pack_start(title, False, False, 0)
        labels.pack_start(subtitle, False, False, 0)
        header.pack_start(labels, True, True, 0)
        new = Gtk.Button(label='＋  Новая вкладка')
        new.set_tooltip_text('Новая вкладка · Ctrl+Shift+T')
        new.connect('clicked', lambda *_: self.new_tab())
        header.pack_end(new, False, False, 0)
        root.pack_start(header, False, False, 0)
        self.tabs = Gtk.Notebook()
        self.tabs.set_scrollable(True)
        self.tabs.connect('switch-page', self._switch_page)
        root.pack_start(self.tabs, True, True, 0)
        self.new_tab()

    def new_tab(self):
        self.serial += 1
        term = Vte.Terminal()
        term.set_font(Pango.FontDescription('Noto Sans Mono 11'))
        term.set_colors(color('#e4edf9'), color('#111a29'), [])
        term.set_scrollback_lines(10000)
        term.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        term.set_mouse_autohide(True)
        term.set_scroll_on_keystroke(True)
        term.connect('child-exited', self._child_exited)
        term.connect('window-title-changed', self._title_changed)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(term)
        label = Gtk.Label(label=f'Сеанс {self.serial}')
        self.tabs.append_page(scroller, label)
        self.tabs.set_current_page(self.tabs.page_num(scroller))
        scroller.show_all()
        term.grab_focus()
        term.spawn_async(Vte.PtyFlags.DEFAULT, os.path.expanduser('~'), [self.shell],
                         None, GLib.SpawnFlags.DEFAULT, None, None, -1, None,
                         self._spawn_finished, None)
        return term

    def _spawn_finished(self, terminal, pid, error, _data):
        if error:
            terminal.feed(('Не удалось запустить оболочку: ' + str(error) + '\r\n').encode())

    def _child_exited(self, term, _status):
        page = term.get_parent()
        index = self.tabs.page_num(page)
        if index >= 0:
            self.tabs.remove_page(index)
        if self.tabs.get_n_pages() == 0:
            self.destroy()

    def _title_changed(self, term):
        page = term.get_parent()
        label = self.tabs.get_tab_label(page)
        if label:
            name = term.get_window_title() or 'Терминал'
            label.set_text(name[:32])

    def _switch_page(self, _notebook, page, _index):
        term = page.get_child()
        if term:
            term.grab_focus()

    def _key_press(self, _window, event):
        mods = event.state & Gtk.accelerator_get_default_mod_mask()
        required = Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK
        if mods != required:
            return False
        key = Gdk.keyval_to_lower(event.keyval)
        page = self.tabs.get_nth_page(self.tabs.get_current_page())
        term = page.get_child() if page else None
        if key == Gdk.KEY_t:
            self.new_tab()
        elif key == Gdk.KEY_w and page:
            # Destroying VTE closes the PTY; the shell receives SIGHUP.
            self.tabs.remove_page(self.tabs.page_num(page))
            page.destroy()
            if not self.tabs.get_n_pages():
                self.destroy()
        elif key == Gdk.KEY_c and term:
            term.copy_clipboard_format(Vte.Format.TEXT)
        elif key == Gdk.KEY_v and term:
            term.paste_clipboard()
        else:
            return False
        return True

    def _destroy(self, *_args):
        if Gtk.main_level():
            Gtk.main_quit()


def main():
    win = Console()
    win.show_all()
    win.tabs.get_nth_page(win.tabs.get_current_page()).get_child().grab_focus()
    Gtk.main()


if __name__ == '__main__':
    main()
