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

        # --- Drag & Drop ---
        self.drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        self.drop_target.connect("enter", self.on_drop_enter)
        self.drop_target.connect("leave", self.on_drop_leave)
        self.drop_target.connect("drop", self.on_drop)
        self.w.overlay.add_controller(self.drop_target)

        # --- Clipboard Paste (Ctrl+V) ---
        self.shortcut_ctrl_v = Gtk.ShortcutController()
        self.shortcut_ctrl_v.add_shortcut(
            Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string("<Ctrl>V"),
                Gtk.CallbackAction.new(self.on_paste_clipboard)
            )
        )
        self.w.add_controller(self.shortcut_ctrl_v)

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

    # ---------------- Drag & Drop ----------------
    def on_drop_enter(self, *_):
        if not self._accepting:
            return False
        self.w.drop_hint.add_css_class("drop-highlight")
        return True

    def on_drop_leave(self, *_):
        self.w.drop_hint.remove_css_class("drop-highlight")
        return True

    def on_drop(self, _, value, __, ___):
        if not self._accepting:
            return False
        self._start_processing(value)
        return True

    # ---------------- Clipboard Paste ----------------
    def on_paste_clipboard(self, *_):
        if not self._accepting:
            return True

        clipboard = self.w.get_clipboard()
        clipboard.read_text_async(None, self._on_clipboard_text_ready)
        return True

    def _on_clipboard_text_ready(self, clipboard, res):
        try:
            text = clipboard.read_text_finish(res)
        except GLib.Error:
            return

        if not text:
            return

        # take the first non-empty line only
        uri = next((u.strip() for u in text.splitlines() if u.strip()), None)
        if not uri:
            return

        if uri.startswith("file://"):
            gfile = Gio.File.new_for_uri(uri)
        else:
            gfile = Gio.File.new_for_path(uri)

        self._start_processing(gfile)

    # ---------------- Shared ----------------
    def _start_processing(self, value):
        if self.w.drop_hint.get_parent():
            self.w.overlay.remove_overlay(self.w.drop_hint)
        self.w.drop_hint.set_visible(False)
        self.w.progress_bar.set_visible(True)
        self.w.progress_bar.set_fraction(0.0)
        GLib.idle_add(partial(self.w.process_drop_value, value))

