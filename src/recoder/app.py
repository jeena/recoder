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

    # Delay imports until after resources are registered
    from recoder.window import RecoderWindow
    from recoder.preferences import RecoderPreferences

    class RecoderApp(Adw.Application):
        def __init__(self):
            super().__init__(
                application_id="net.jeena.Recoder",
                flags=Gio.ApplicationFlags.FLAGS_NONE
            )
            self.window = None
            self.preferences_window = None

        def do_startup(self):
            Adw.Application.do_startup(self)

            quit_action = Gio.SimpleAction.new("quit", None)
            quit_action.connect("activate", lambda *_: self.quit())
            self.add_action(quit_action)
            self.set_accels_for_action("app.quit", ["<Ctrl>q"])
            self.set_accels_for_action("win.close", ["<Ctrl>w"])

            preferences_action = Gio.SimpleAction.new("preferences", None)
            preferences_action.connect("activate", self.on_preferences_activate)
            self.add_action(preferences_action)
            # Add the accelerator for Preferences (Ctrl+,)
            self.set_accels_for_action("app.preferences", ["<Primary>comma"])

        def do_activate(self):
            if not self.window:
                self.window = RecoderWindow(self)
                self.window.connect("close-request", self.on_window_close)
            self.window.present()

        def on_preferences_activate(self, action, param):
            if not self.preferences_window:
                self.preferences_window = RecoderPreferences()
                self.preferences_window.set_transient_for(self.window)
                self.preferences_window.set_modal(True)
                self.preferences_window.connect("close-request", self.on_preferences_close)

            self.preferences_window.present()

        def on_preferences_close(self, window):
            window.set_visible(False)
            # Don't destroy, just hide
            return True  # stops further handlers, prevents default destruction

        def on_window_close(self, window):
            self.quit()
            return False  # allow default handler to proceed

    app = RecoderApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
