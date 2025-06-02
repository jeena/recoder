#!/usr/bin/env python3
import sys
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio

Adw.init()

def load_resources():
    resource_path = os.path.join(os.path.dirname(__file__), "../resources/resources.gresource")
    resource = Gio.Resource.load(resource_path)
    Gio.resources_register(resource)

def main():
    load_resources()

    from recoder.ui import RecoderWindow  # delayed import

    class RecoderApp(Adw.Application):
        def __init__(self):
            super().__init__(application_id="net.jeena.Recoder",
                             flags=Gio.ApplicationFlags.FLAGS_NONE)
            self.window = None

        def do_activate(self):
            if not self.window:
                self.window = RecoderWindow(application=self)
            self.window.window.present()

    app = RecoderApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
