#!/usr/bin/env python3
import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio
from importlib.resources import files

Adw.init()

def load_resources():
    resource_path = files("recoder").joinpath("resources.gresource")
    resource = Gio.Resource.load(str(resource_path))
    Gio.resources_register(resource)

def main():
    load_resources()

    from recoder.recoder_window import RecoderWindow  # delayed import

    class RecoderApp(Adw.Application):
        def __init__(self):
            super().__init__(
                application_id="net.jeena.Recoder",
                flags=Gio.ApplicationFlags.FLAGS_NONE
            )
            self.window = None

        def do_activate(self):
            if not self.window:
                self.window = RecoderWindow(self)
            self.window.present()

    app = RecoderApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
