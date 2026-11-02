# SPDX-License-Identifier: GPL-3.0-only
# English publication counterpart; the private SP7 test profile uses Swedish prompts.
#!/usr/bin/env python3
"""SP7 presence window. This program never starts a sensor or invokes sudo."""
import argparse
import json
import os
from pathlib import Path
import time

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gio

import presence as p


class Dialog(Gtk.Application):
    def __init__(self, folder):
        super().__init__(application_id='local.sp7.IRPresence', flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.store = p.Store(folder)
        self.connect('activate', self.activate)
        self.phase = 'preparing'
        self.window = None

    def activate(self, app):
        self.window = Gtk.ApplicationWindow(application=self, title="SP7 — RGB/IR capture")
        self.window.set_default_size(580, 300)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        for side in ('top', 'bottom', 'start', 'end'):
            getattr(box, 'set_margin_'+side)(28)
        self.heading = Gtk.Label(label="IR capture")
        self.heading.add_css_class('title-1')
        self.message = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER)
        self.message.set_vexpand(True)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14, homogeneous=True)
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect('clicked', self.cancel)
        self.ready_button = Gtk.Button(label="Ready")
        self.ready_button.add_css_class('suggested-action')
        self.ready_button.connect('clicked', self.ready)
        row.append(self.cancel_button); row.append(self.ready_button)
        for child in (self.heading, self.message, row): box.append(child)
        self.window.set_child(box)
        self.window.connect('close-request', self.close_requested)
        self.window.connect('map', self.mapped)
        self.refresh()
        self.window.present()
        GLib.timeout_add(250, self.refresh)

    def mapped(self, *_):
        (self.store.folder/'ui-status.json').write_text(json.dumps({
            'window_mapped':True, 'pid':os.getpid(), 'boot_id':p.boot_id(),
            'mapped_at_monotonic':time.monotonic(), 'initial_phase':self.phase,
            'camera_started_by_dialog':False},indent=2)+'\n')

    def show_error(self, exc):
        self.phase = 'needs_check'
        self.heading.set_text("Check needed")
        self.message.set_text("The trial is blocked.\n"+str(exc))
        self.ready_button.set_label("Close"); self.ready_button.set_sensitive(True)
        self.cancel_button.set_sensitive(False)

    def refresh(self):
        try:
            state = self.store.update(lambda s: p.expire(s, p.boot_id(), time.monotonic()))
            self.phase = state['phase']
            title, message, button, enabled = p.presentation(state)
            self.heading.set_text(title); self.message.set_text(message)
            self.ready_button.set_label(button); self.ready_button.set_sensitive(enabled)
            self.cancel_button.set_sensitive(self.phase in ('preparing','awaiting_presence','ready','running'))
        except Exception as exc:
            self.show_error(exc)
        return GLib.SOURCE_CONTINUE

    def ready(self, *_):
        if self.phase in ('finished', 'cancelled', 'needs_check'):
            self.quit(); return
        try:
            self.store.update(lambda s: p.ready(s, p.boot_id(), time.monotonic()))
            self.refresh()
        except Exception as exc: self.show_error(exc)

    def cancel(self, *_):
        try:
            self.store.update(lambda s: p.cancel(s, p.boot_id()))
            self.refresh()
        except Exception as exc: self.show_error(exc)

    def close_requested(self, *_):
        if self.phase in ('running', 'stopping'):
            self.cancel()
            return True
        if self.phase in ('preparing', 'awaiting_presence', 'ready'):
            self.cancel()
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    args = parser.parse_args()
    Dialog(args.session).run([])


if __name__ == '__main__': main()
