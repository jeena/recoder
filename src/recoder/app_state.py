import gi
gi.require_version("GObject", "2.0")
from gi.repository import GObject


class AppState(GObject.GEnum):
    IDLE = 0
    FILES_LOADED = 1
    TRANSCODING = 2
    PAUSED = 3
    DONE = 4
    STOPPED = 5
    ERROR = 6


class AppStateManager(GObject.GObject):
    state = GObject.Property(type=AppState, default=AppState.IDLE)


class UIStateManager:
    def __init__(self, window, app_state_manager):
        self.window = window
        self.app_state_manager = app_state_manager
        self.app_state_manager.connect("notify::state", self.on_state_changed)

        self.handlers = {
            AppState.IDLE: self._handle_idle,
            AppState.FILES_LOADED: self._handle_files_loaded,
            AppState.TRANSCODING: self._handle_transcoding,
            AppState.PAUSED: self._handle_paused,
            AppState.DONE: self._handle_done,
            AppState.STOPPED: self._handle_idle,
            AppState.ERROR: self._handle_error,
        }

    def on_state_changed(self, obj, pspec):
        self.set_state(self.app_state_manager.state)

    def set_state(self, state: AppState):
        handler = self.handlers.get(state)
        if handler:
            handler()

    def _update_title(self, folder_name=None):
        w = self.window
        base = "Recoder"
        if folder_name:
            w.folder_label.set_text(f"{base} — {folder_name}")
        else:
            w.folder_label.set_text(base)

    def _handle_idle(self):
        self._update_title(None)
        w = self.window
        w.clear_listbox()
        w.file_rows.clear()
        w.file_items_to_process = []
        w.is_paused = False
        w.progress_bar.set_visible(False)
        w.progress_bar.set_fraction(0.0)
        w.progress_bar.set_text("")
        w.drop_hint.set_visible(True)
        if w.drop_hint.get_parent() != w.overlay:
            w.overlay.add_overlay(w.drop_hint)
        w.btn_transcode.set_visible(False)
        w.btn_cancel.set_visible(False)

    def _handle_files_loaded(self):
        w = self.window
        self._update_title(w.current_folder_name)
        w.drop_hint.set_visible(False)
        w.progress_bar.set_visible(False)
        w.btn_transcode.set_visible(True)
        w.btn_transcode.set_sensitive(True)
        w.btn_transcode.set_label("Transcode")
        w.btn_transcode.add_css_class("suggested-action")
        w.btn_cancel.set_visible(True)
        w.is_paused = False

    def _handle_transcoding(self):
        w = self.window
        w.drop_hint.set_visible(False)
        w.progress_bar.set_visible(True)
        w.btn_transcode.set_visible(True)
        w.btn_transcode.set_sensitive(True)
        w.btn_transcode.set_label("Pause")
        w.btn_transcode.remove_css_class("suggested-action")
        w.btn_cancel.set_visible(True)
        w.is_paused = False

    def _handle_paused(self):
        w = self.window
        w.drop_hint.set_visible(False)
        w.progress_bar.set_visible(True)
        w.btn_transcode.set_visible(True)
        w.btn_transcode.set_sensitive(True)
        w.btn_transcode.set_label("Resume")
        w.btn_cancel.set_visible(True)
        w.is_paused = True

    def _handle_done(self):
        w = self.window
        w.drop_hint.set_visible(False)
        w.progress_bar.set_visible(True)
        w.progress_bar.set_fraction(1.0)
        w.btn_transcode.set_visible(False)
        w.btn_transcode.remove_css_class("suggested-action")
        w.btn_cancel.set_visible(True)
        w.is_paused = False

    def _handle_error(self):
        w = self.window
        self._update_title(w.current_folder_name)
        w.drop_hint.set_visible(False)
        w.progress_bar.set_visible(False)
        w.btn_transcode.set_visible(False)
        w.btn_cancel.set_visible(True)
        w.is_paused = False
