import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Notify', '0.7')

from gi.repository import Gtk, Gdk, Gio, GLib, Notify
from functools import partial

from recoder.transcoder import Transcoder
from recoder.utils import extract_video_files, notify_done, play_complete_sound
from recoder.models import FileStatus, FileItem

class FileEntryRow(Gtk.ListBoxRow):
    def __init__(self, item):
        super().__init__()
        self.item = item

        self.icon = Gtk.Image.new_from_icon_name("object-select-symbolic")
        self.label = Gtk.Label(xalign=0, hexpand=True)
        self.progress_label = Gtk.Label(xalign=1)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.append(self.icon)
        hbox.append(self.label)
        hbox.append(self.progress_label)
        self.set_child(hbox)

        self.item.connect("notify::status", self.on_status_changed)
        self.item.connect("notify::progress", self.on_progress_changed)

        self.update_display()

    def on_status_changed(self, *_):
        self.update_display()

    def on_progress_changed(self, *_):
        self.update_display()

    def update_display(self):
        basename = self.item.file.get_basename()
        self.label.set_text(basename)

        match self.item.status:
            case FileStatus.WAITING:
                self.icon.set_from_icon_name("media-playback-pause-symbolic")
                self.progress_label.set_text("Waiting")
            case FileStatus.PROCESSING:
                self.icon.set_from_icon_name("view-refresh-symbolic")
                self.progress_label.set_text(f"{self.item.progress}%")
            case FileStatus.DONE:
                self.icon.set_from_icon_name("task-complete-symbolic")
                self.progress_label.set_text("Done")
            case FileStatus.ERROR:
                self.icon.set_from_icon_name("dialog-error-symbolic")
                self.progress_label.set_text("Error")


class RecoderWindow:
    def __init__(self, application, **kwargs):
        self.file_items_to_process = []
        self.transcoder = None
        self.file_rows = {}

        builder = Gtk.Builder()
        builder.add_from_resource("/net/jeena/recoder/recoder.ui")

        self.window = builder.get_object("main_window")
        self.window.set_application(application)

        self.overlay = builder.get_object("overlay")
        self.progress = builder.get_object("progress_bar")
        self.drop_hint = builder.get_object("drop_hint")
        self.listbox = builder.get_object("listbox")
        self.scrolled_window = builder.get_object("scrolled_window")

        self.drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        self.drop_target.connect("drop", self.on_drop)
        self.drop_target.connect("enter", self.on_drop_enter)
        self.drop_target.connect("leave", self.on_drop_leave)
        self.window.add_controller(self.drop_target)

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
        self.progress.set_visible(True)
        self.progress.set_fraction(0.0)
        self.drop_hint.set_visible(False)
        return value

    def process_drop_value(self, value):
        file_items = extract_video_files(value)
        if not file_items:
            return False

        # Clear previous rows
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

        self.window.remove_controller(self.drop_target)

        self.progress.set_fraction(0.0)
        self.progress.set_text("Starting transcoding...")

        self.transcoder = Transcoder(
            self.file_items_to_process,
            progress_callback=self.update_progress,
            done_callback=self._done_callback,
            file_done_callback=self.mark_file_done,
        )
        self.transcoder.start()

    def update_progress(self, text, fraction):
        self.progress.set_show_text(True)
        self.progress.set_text(text)
        self.progress.set_fraction(fraction)

    def mark_file_done(self, filepath):
        if filepath in self.file_rows:
            row = self.file_rows[filepath]
            GLib.idle_add(row.mark_done)

    def _done_callback(self):
        self.progress.set_show_text(True)
        self.progress.set_text("Transcoding Complete!")
        play_complete_sound()
        notify_done("Recoder", "Transcoding finished!")
        self.window.add_controller(self.drop_target)
