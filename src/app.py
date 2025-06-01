import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gio
from ui import RecoderWindow

Adw.init()

class RecoderApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="net.jeena.recoder",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = RecoderWindow(application=self)
        self.window.present()

def main():
    app = RecoderApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
