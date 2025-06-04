import gi
import signal

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk, Gdk, Gio, Adw, GLib, Notify
from functools import partial

from recoder.transcoder import Transcoder
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


class UIStateManager:
    def __init__(self, window):
        self.window = window

    def reset_ui(self):
        self.window.btn_transcode.set_label("Start Transcoding")
        self.window.btn_transcode.set_sensitive(False)
        self.window.btn_transcode.remove_css_class("suggested-action")
        self.window.btn_cancel.set_visible(False)
        self.window.progress_bar.set_fraction(0.0)
        self.window.progress_bar.set_text("")
        self.window.progress_bar.set_visible(False)
        self.window.drop_hint.set_visible(True)

        if self.window.drop_hint.get_parent() != self.window.overlay:
            self.window.overlay.add_overlay(self.window.drop_hint)

        self.window.clear_listbox()
        self.window.file_rows.clear()
        self.window.file_items_to_process = []
        self.window.is_paused = False


@Gtk.Template(resource_path="/net/jeena/recoder/recoder_window.ui")
class RecoderWindow(Adw.ApplicationWindow):
    __gtype_name__ = "RecoderWindow"

    overlay = Gtk.Template.Child()
    progress_bar = Gtk.Template.Child()
    drop_hint = Gtk.Template.Child()
    listbox = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()
    btn_transcode = Gtk.Template.Child()
    btn_cancel = Gtk.Template.Child()

    def __init__(self, application):
        super().__init__(application=application)

        self.file_items_to_process = []
        self.transcoder = None
        self.file_rows = {}
        self.is_paused = False

        self.ui_manager = UIStateManager(self)
        self.drop_handler = DropHandler(self.overlay, self.drop_hint, self.progress_bar, self.process_drop_value)
        self.add_controller(self.drop_handler.controller())

        self.btn_transcode.connect("clicked", self.on_transcode_clicked)
        self.btn_cancel.connect("clicked", self.on_cancel_clicked)

        self.btn_transcode.set_sensitive(False)
        self.btn_cancel.set_visible(False)
        self.btn_transcode.set_label("Start Transcoding")

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
        self.btn_transcode.set_sensitive(True)
        self.btn_transcode.add_css_class("suggested-action")
        self.btn_transcode.set_label("Start Transcoding")
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
        self.btn_transcode.set_label("Pause")
        self.btn_transcode.set_sensitive(True)
        self.btn_transcode.remove_css_class("suggested-action")
        self.btn_cancel.set_visible(False)
        self.is_paused = False

        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Starting transcoding...")

        self.transcoder = Transcoder(
            self.file_items_to_process,
            progress_callback=self.update_progress,
            done_callback=self._done_callback,
            file_done_callback=self.mark_file_done,
        )
        self.transcoder.start()

    def pause_transcoding(self):
        if self.transcoder:
            self.transcoder.pause()
            self.is_paused = True
            self.btn_transcode.set_label("Resume")
            self.progress_bar.set_text("Paused")
            self.btn_cancel.set_visible(True)

    def resume_transcoding(self):
        if self.transcoder:
            self.transcoder.resume()
            self.is_paused = False
            self.btn_transcode.set_label("Pause")
            self.progress_bar.set_text("Resuming...")
            self.btn_cancel.set_visible(False)

    def on_cancel_clicked(self, button):
        if self.transcoder and self.transcoder.is_processing:
            self.transcoder.stop()
        self.transcoder = None
        self.add_controller(self.drop_handler.controller())
        self.ui_manager.reset_ui()

    def update_progress(self, text, fraction):
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text(text)
        self.progress_bar.set_fraction(fraction)

    def mark_file_done(self, filepath):
        if filepath in self.file_rows:
            row = self.file_rows[filepath]
            GLib.idle_add(row.mark_done)

    def _done_callback(self):
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("Transcoding Complete!")
        play_complete_sound()
        notify_done("Recoder", "Transcoding finished!")
        self.add_controller(self.drop_handler.controller())
        self.btn_transcode.set_label("Start Transcoding")
        self.btn_transcode.set_sensitive(False)
        self.btn_cancel.set_visible(False)
        self.is_paused = False

        self.drop_hint.set_visible(True)
        if self.drop_hint.get_parent() != self.overlay:
            self.overlay.add_overlay(self.drop_hint)
