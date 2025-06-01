#!/usr/bin/env python3
import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio

Adw.init()

def main():
    from recoder.ui import RecoderWindow  # delayed import

    class RecoderApp(Adw.Application):
        def __init__(self):
            super().__init__(application_id="net.jeena.Recoder",
                             flags=Gio.ApplicationFlags.FLAGS_NONE)
            self.window = None

        def do_activate(self):
            if not self.window:
                self.window = RecoderWindow(application=self)
            self.window.present()

    app = RecoderApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
