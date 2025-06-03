import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk, Gdk, Gio, Adw, GLib, Notify
from functools import partial

from recoder.transcoder import Transcoder
from recoder.utils import extract_video_files, notify_done, play_complete_sound
from recoder.file_entry_row import FileEntryRow

@Gtk.Template(resource_path="/net/jeena/recoder/recoder_window.ui")
class RecoderWindow(Adw.ApplicationWindow):
    __gtype_name__ = "RecoderWindow"

    overlay = Gtk.Template.Child()
    progress_bar = Gtk.Template.Child()
    drop_hint = Gtk.Template.Child()
    listbox = Gtk.Template.Child()
    scrolled_window = Gtk.Template.Child()

    def __init__(self, application):
        super().__init__(application=application)

        self.file_items_to_process = []
        self.transcoder = None
        self.file_rows = {}

        self.drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        self.drop_target.connect("drop", self.on_drop)
        self.drop_target.connect("enter", self.on_drop_enter)
        self.drop_target.connect("leave", self.on_drop_leave)
        self.add_controller(self.drop_target)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_resource("/net/jeena/recoder/style.css")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        Notify.init("Recoder")

    def on_drop_enter(self, drop_target, x, y):
        self.overlay.add_css_class("drop-highlight")
        return True

    def on_drop_leave(self, drop_target):
        self.overlay.remove_css_class("drop-highlight")
        return True

    def on_drop(self, drop_target, value, x, y):
        GLib.idle_add(partial(self.process_drop_value, value))
        self.overlay.remove_overlay(self.drop_hint)
        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0.0)
        self.drop_hint.set_visible(False)
        return value

    def process_drop_value(self, value):
        file_items = extract_video_files(value)
        if not file_items:
            return False

        self.clear_listbox()
        self.file_rows.clear()

        for file_item in file_items:
            row = FileEntryRow(file_item)
            self.listbox.append(row)
            self.file_rows[file_item] = row

        self.file_items_to_process = file_items
        self.start_transcoding()
        return False

    def clear_listbox(self):
        child = self.listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.listbox.remove(child)
            child = next_child

    def start_transcoding(self):
        if self.transcoder and self.transcoder.is_processing:
            return

        self.remove_controller(self.drop_target)

        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("Starting transcoding...")

        self.transcoder = Transcoder(
            self.file_items_to_process,
            progress_callback=self.update_progress,
            done_callback=self._done_callback,
            file_done_callback=self.mark_file_done,
        )
        self.transcoder.start()

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
        self.add_controller(self.drop_target)
