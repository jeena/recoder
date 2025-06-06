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
from recoder.drop_handler import DropHandler
from recoder.app_state import AppState, AppStateManager, UIStateManager
from recoder.preferences import RecoderPreferences


@Gtk.Template(resource_path="/net/jeena/recoder/window.ui")
class RecoderWindow(Adw.ApplicationWindow):
    __gtype_name__ = "RecoderWindow"

    overlay = Gtk.Template.Child()
    drop_hint = Gtk.Template.Child()
    listbox = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()
    btn_transcode = Gtk.Template.Child()
    btn_clear = Gtk.Template.Child()
    progress_bar = Gtk.Template.Child()
    folder_label = Gtk.Template.Child()

    def __init__(self, application):
        super().__init__(application=application)
        
        self.state_settings = Gio.Settings.new("net.jeena.recoder.state")

        # Bind window size and state to your window properties
        self.state_settings.bind("width", self, "default-width", Gio.SettingsBindFlags.DEFAULT)
        self.state_settings.bind("height", self, "default-height", Gio.SettingsBindFlags.DEFAULT)
        self.state_settings.bind("is-maximized", self, "maximized", Gio.SettingsBindFlags.DEFAULT)
        self.state_settings.bind("is-fullscreen", self, "fullscreened", Gio.SettingsBindFlags.DEFAULT)

        close_action = Gio.SimpleAction.new("close", None)
        close_action.connect("activate", lambda *a: self.close())
        self.add_action(close_action)

        self.file_items_to_process = []
        self.current_folder_name = None
        self.transcoder = None
        self.file_rows = {}
        self.is_paused = False

        self.app_state_manager = AppStateManager()
        self.drop_handler = DropHandler(self, self.app_state_manager)
        self.ui_manager = UIStateManager(self, self.app_state_manager)

        self.btn_transcode.connect("clicked", self.on_transcode_clicked)
        self.btn_clear.connect("clicked", self.on_clear_clicked)

        self.app_state_manager.state = AppState.IDLE

        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/net/jeena/recoder/style.css")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        Notify.init("Recoder")


    def process_drop_value(self, value):
        folder_file = None
        if isinstance(value, list) and len(value) > 0:
            folder_file = value[0]
        elif hasattr(value, 'get_path'):
            folder_file = value

        if folder_file:
            self.current_folder_name = folder_file.get_basename()

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
        self.app_state_manager.state = AppState.FILES_LOADED
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

        self.transcoder = Transcoder(self.file_items_to_process)
        self.transcoder.connect("notify::batch-progress", self.on_transcoder_progress)
        self.transcoder.connect("notify::batch-status", self.on_transcoder_status)
        self.transcoder.start()

        self.app_state_manager.state = AppState.TRANSCODING

    def pause_transcoding(self):
        if self.transcoder:
            self.transcoder.pause()
            self.is_paused = True
            self.app_state_manager.state = AppState.PAUSED

    def resume_transcoding(self):
        if self.transcoder:
            self.transcoder.resume()
            self.is_paused = False
            self.app_state_manager.state = AppState.TRANSCODING

    def on_clear_clicked(self, button):
        if self.transcoder and self.transcoder.is_processing:
            self.transcoder.stop()
        self.transcoder = None
        self.app_state_manager.state = AppState.STOPPED

    def on_transcoder_progress(self, transcoder, param):
        self.progress_bar.set_fraction(transcoder.batch_progress / 100.0)

    def on_transcoder_status(self, transcoder, param):
        if transcoder.batch_status == BatchStatus.DONE:
            play_complete_sound()
            notify_done("Recoder", "Transcoding finished!")
            self.app_state_manager.state = AppState.DONE

        elif transcoder.batch_status == BatchStatus.STOPPED:
            self.app_state_manager.state = AppState.STOPPED

        elif transcoder.batch_status == BatchStatus.ERROR:
            notify_done("Recoder", "An error occurred during transcoding.")
            self.app_state_manager.state = AppState.ERROR
