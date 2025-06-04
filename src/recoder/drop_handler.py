import gi
from gi.repository import Gtk, Gdk, Gio, GLib
from functools import partial
from recoder.app_state import AppState

class DropHandler:
    def __init__(self, w, app_state_manager):
        self.w = w
        self.app_state_manager = app_state_manager
        self._accepting = self._compute_accept()
        self.app_state_manager.connect("notify::state", self.on_state_changed)

        self.drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        self.drop_target.connect("enter", self.on_drop_enter)
        self.drop_target.connect("leave", self.on_drop_leave)
        self.drop_target.connect("drop", self.on_drop)

        self.w.overlay.add_controller(self.drop_target)

    def _compute_accept(self):
        return self.app_state_manager.state not in {
            AppState.TRANSCODING,
            AppState.PAUSED,
            AppState.FILES_LOADED,
        }

    def on_state_changed(self, *_):
        accepting = self._compute_accept()
        if accepting != self._accepting:
            self._accepting = accepting
            if accepting:
                self.w.overlay.add_controller(self.drop_target)
            else:
                self.w.overlay.remove_controller(self.drop_target)


    def on_drop_enter(self, *_):
        if not self._accepting:
            return False
        self.w.overlay.add_css_class("drop-highlight")
        return True

    def on_drop_leave(self, *_):
        self.w.overlay.remove_css_class("drop-highlight")
        return True

    def on_drop(self, _, value, __, ___):
        if not self._accepting:
            return False
        if self.w.drop_hint.get_parent():
            self.w.overlay.remove_overlay(self.w.drop_hint)
        self.w.drop_hint.set_visible(False)
        self.w.progress_bar.set_visible(True)
        self.w.progress_bar.set_fraction(0.0)
        GLib.idle_add(partial(self.w.process_drop_value, value))
        return True
