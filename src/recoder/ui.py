import os
import gi
import shutil
import subprocess
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib, Notify
from functools import partial

from recoder.transcoder_worker import TranscoderWorker

class FileEntryRow(Gtk.ListBoxRow):
    def __init__(self, path):
        super().__init__()
        self.path = path
        self.icon = Gtk.Image.new_from_icon_name("media-playback-pause-symbolic")
        self.label = Gtk.Label(label=os.path.basename(path), xalign=0)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.append(self.icon)
        hbox.append(self.label)
        self.set_child(hbox)

    def mark_done(self):
        self.icon.set_from_icon_name("emblem-ok-symbolic")
        self.label.set_text(f"{os.path.basename(self.path)} - Done")

class RecoderWindow():

    def __init__(self, application, **kwargs):

        self.files_to_process = []
        self.transcoder = None
        self.file_rows = {}

        # Load UI from resource
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
        self.progress.set_fraction(0.0)  # optionally reset
        self.drop_hint.set_visible(False)
        return value

    def process_drop_value(self, value):
        if isinstance(value, Gio.File):
            uris = [value]
        elif isinstance(value, list):
            uris = value
        else:
            return False

        paths = []
        for file in uris:
            path = file.get_path()
            if os.path.isdir(path):
                for entry in os.scandir(path):
                    if entry.is_file() and entry.name.lower().endswith((".mp4", ".mov", ".mkv", ".avi")):
                        paths.append(entry.path)
            else:
                paths.append(path)

        if not paths:
            return False

        # Clear previous listbox rows
        children = self.listbox.get_first_child()
        while children:
            next_child = children.get_next_sibling()
            self.listbox.remove(children)
            children = next_child
        self.file_rows.clear()

        # Add new files to listbox with custom FileEntryRow
        for path in paths:
            row = FileEntryRow(path)
            self.listbox.append(row)
            self.file_rows[path] = row

        self.files_to_process = paths
        self.start_transcoding()
        return False

    def start_transcoding(self):
        if self.transcoder and self.transcoder.is_processing:
            return

        self.progress.set_fraction(0.0)
        self.progress.set_text("Starting transcoding...")

        self.transcoder = TranscoderWorker(
            self.files_to_process,
            progress_callback=self.update_progress,
            done_callback=self.notify_done,
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

    def notify_done(self):
        self.progress.set_show_text(True)
        self.progress.set_text("Transcoding Complete!")
        self.play_complete_sound()
        notification = Notify.Notification.new(
            "Recoder",
            "Transcoding finished!",
            "net.jeena.Recoder"
        )
        notification.show()

    def play_complete_sound(self):
        if shutil.which("canberra-gtk-play"):
            subprocess.Popen(["canberra-gtk-play", "--id", "complete"])
        else:
            print("canberra-gtk-play not found.")
