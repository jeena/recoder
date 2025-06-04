import gi
import signal
from enum import Enum, auto
from functools import partial

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk, Gdk, Gio, Adw, GLib, Notify

from recoder.transcoder import Transcoder, BatchStatus
from recoder.utils import extract_video_files, notify_done, play_complete_sound
from recoder.file_entry_row import FileEntryRow


class DropHandler:
    def __init__(self, overlay, drop_hint, progress_bar, on_files_dropped):
        self.overlay = overlay
        self.drop_hint = drop_hint
        self.progress_bar = progress_bar
        self.on_files_dropped = on_files_dropped

        self.drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        self.drop_target.connect("enter", self.on_drop_enter)
        self.drop_target.connect("leave", self.on_drop_leave)
        self.drop_target.connect("drop", self.on_drop)

    def controller(self):
        return self.drop_target

    def on_drop_enter(self, *_):
        self.overlay.add_css_class("drop-highlight")
        return True

    def on_drop_leave(self, *_):
        self.overlay.remove_css_class("drop-highlight")
        return True

    def on_drop(self, _, value, __, ___):
        self.overlay.remove_overlay(self.drop_hint)
        self.drop_hint.set_visible(False)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        GLib.idle_add(partial(self.on_files_dropped, value))
        return value


class AppState(Enum):
    IDLE = auto()             # Nothing loaded, waiting for drop
    FILES_LOADED = auto()     # Files dropped, ready to start transcoding
    TRANSCODING = auto()      # Transcoding in progress
    PAUSED = auto()           # Transcoding paused
    DONE = auto()             # Transcoding finished
    STOPPED = auto()          # Transcoding canceled
    ERROR = auto()            # Error occurred


class UIStateManager:
    def __init__(self, window):
        self.window = window
        self.handlers = {
            AppState.IDLE: self._handle_idle,
            AppState.FILES_LOADED: self._handle_files_loaded,
            AppState.TRANSCODING: self._handle_transcoding,
            AppState.PAUSED: self._handle_paused,
            AppState.DONE: self._handle_done,
            AppState.STOPPED: lambda: self.set_state(AppState.IDLE),
            AppState.ERROR: self._handle_error,
        }

    def set_state(self, state: AppState):
        handler = self.handlers.get(state)
        if handler:
            handler()

    def _handle_idle(self):
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
        w.drop_hint.set_visible(False)
        w.progress_bar.set_visible(False)
        w.btn_transcode.set_visible(True)
        w.btn_transcode.set_sensitive(True)
        w.btn_transcode.set_label("Start Transcoding")
        w.btn_transcode.add_css_class("suggested-action")
        w.btn_cancel.set_visible(False)
        w.is_paused = False

    def _handle_transcoding(self):
        w = self.window
        w.drop_hint.set_visible(False)
        w.progress_bar.set_visible(True)
        w.btn_transcode.set_visible(True)
        w.btn_transcode.set_sensitive(True)
        w.btn_transcode.set_label("Pause")
        w.btn_transcode.remove_css_class("suggested-action")
        w.btn_cancel.set_visible(False)
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
        w.drop_hint.set_visible(False)
        w.progress_bar.set_visible(False)
        w.btn_transcode.set_visible(False)
        w.btn_cancel.set_visible(True)
        w.is_paused = False



@Gtk.Template(resource_path="/net/jeena/recoder/recoder_window.ui")
class RecoderWindow(Adw.ApplicationWindow):
    __gtype_name__ = "RecoderWindow"

    overlay = Gtk.Template.Child()
    drop_hint = Gtk.Template.Child()
    listbox = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()
    btn_transcode = Gtk.Template.Child()
    btn_cancel = Gtk.Template.Child()
    progress_bar = Gtk.Template.Child()

    def __init__(self, application):
        super().__init__(application=application)

        self.file_items_to_process = []
        self.transcoder = None
        self.file_rows = {}
        self.is_paused = False

        self.drop_handler = DropHandler(self.overlay, self.drop_hint, self.progress_bar, self.process_drop_value)
        self.add_controller(self.drop_handler.controller())

        self.ui_manager = UIStateManager(self)

        self.btn_transcode.connect("clicked", self.on_transcode_clicked)
        self.btn_cancel.connect("clicked", self.on_cancel_clicked)

        self.ui_manager.set_state(AppState.IDLE)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/net/jeena/recoder/style.css")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        Notify.init("Recoder")

    def process_drop_value(self, value):
        file_items = extract_video_files(value)
        if not file_items:
            return False

        self.clear_listbox()
        self.file_rows.clear()

        for file_item in file_items:
            row = FileEntryRow(file_item)
            self.listbox.append(row)
            self.file_rows[file_item.file] = row

        self.file_items_to_process = file_items
        self.ui_manager.set_state(AppState.FILES_LOADED)
        return False

    def clear_listbox(self):
        child = self.listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.listbox.remove(child)
            child = next_child

    def on_transcode_clicked(self, button):
        if self.transcoder and self.transcoder.is_processing:
            if self.is_paused:
                self.resume_transcoding()
            else:
                self.pause_transcoding()
        else:
            self.start_transcoding()

    def start_transcoding(self):
        if not self.file_items_to_process:
            return

        self.remove_controller(self.drop_handler.controller())

        self.transcoder = Transcoder(self.file_items_to_process)
        self.transcoder.connect("notify::batch-progress", self.on_transcoder_progress)
        self.transcoder.connect("notify::batch-status", self.on_transcoder_status)
        self.transcoder.start()

        self.ui_manager.set_state(AppState.TRANSCODING)

    def pause_transcoding(self):
        if self.transcoder:
            self.transcoder.pause()
            self.is_paused = True
            self.ui_manager.set_state(AppState.PAUSED)

    def resume_transcoding(self):
        if self.transcoder:
            self.transcoder.resume()
            self.is_paused = False
            self.ui_manager.set_state(AppState.TRANSCODING)

    def on_cancel_clicked(self, button):
        if self.transcoder and self.transcoder.is_processing:
            self.transcoder.stop()
        self.transcoder = None
        self.add_controller(self.drop_handler.controller())
        self.ui_manager.set_state(AppState.STOPPED)

    def on_transcoder_progress(self, transcoder, param):
        self.progress_bar.set_fraction(transcoder.batch_progress / 100.0)
        self.progress_bar.set_visible(True)

    def on_transcoder_status(self, transcoder, param):
        if transcoder.batch_status == BatchStatus.DONE:
            play_complete_sound()
            notify_done("Recoder", "Transcoding finished!")
            self.add_controller(self.drop_handler.controller())
            self.ui_manager.set_state(AppState.DONE)

        elif transcoder.batch_status == BatchStatus.STOPPED:
            self.add_controller(self.drop_handler.controller())
            self.ui_manager.set_state(AppState.STOPPED)

        elif transcoder.batch_status == BatchStatus.ERROR:
            notify_done("Recoder", "An error occurred during transcoding.")
            self.add_controller(self.drop_handler.controller())
            self.ui_manager.set_state(AppState.ERROR)
