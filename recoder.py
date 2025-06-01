#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib, GObject

import os
import sys
import subprocess
import threading
import json
from pathlib import Path
import asyncio

from models import FileItem, FileStatus
from transcoder import transcode_file

Adw.init()

CONFIG_PATH = Path(GLib.get_user_config_dir()) / "recoder" / "config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f)

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}

class RecoderWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Recoder")
        self.set_default_size(700, 400)

        self.config = load_config()
        self.current_dir = self.config.get("last_directory", str(Path.home()))

        # Main Box
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        # Create the header bar
        self.header_bar = Adw.HeaderBar()

        # Create the toolbar view and set the header bar
        self.toolbar_view = Adw.ToolbarView()
        self.toolbar_view.add_top_bar(self.header_bar)
        self.toolbar_view.set_content(self.vbox)

        # Set the toolbar view as the window content
        self.set_content(self.toolbar_view)

        # TextView to list files
        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textbuffer = self.textview.get_buffer()

        # Create a DropTarget for URI list (files)
        self.drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        self.drop_target.connect("enter", self.on_drop_enter)
        self.drop_target.connect("leave", self.on_drop_leave)
        self.drop_target.connect("drop", self.on_drop)
        self.textview.add_controller(self.drop_target)

        # CSS for highlight
        css = b"""
        textview.drop-highlight {
            background-color: @theme_selected_bg_color;
            border: 2px solid @theme_selected_fg_color;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Create label overlay
        self.drop_hint = Gtk.Label(label="📂 Drop files here to get started")
        self.drop_hint.add_css_class("dim-label")

        # Optional: use CSS to style it
        css = b"""
        .dim-label {
            font-size: 16px;
            color: @theme_unfocused_fg_color;
        }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Overlay
        overlay = Gtk.Overlay()
        overlay.set_child(self.textview)
        overlay.add_overlay(self.drop_hint)
        self.drop_hint.set_halign(Gtk.Align.CENTER)
        self.drop_hint.set_valign(Gtk.Align.CENTER)

        # Scroll container for textview
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_child(overlay)
        self.vbox.append(self.scrolled)
        self.scrolled.set_vexpand(True)
        self.scrolled.set_hexpand(True)

        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.vbox.append(self.progress)
        self.progress.set_hexpand(True)

        self.files_to_process = []
        self.is_processing = False


    def load_files_from_directory(self, directory):
        self.files_to_process = []
        self.textbuffer.set_text("")
        for entry in os.scandir(directory):
            if entry.is_file() and entry.name.lower().endswith((".mp4", ".mov", ".mkv", ".avi")):
                self.files_to_process.append(entry.path)
                self.textbuffer.insert_at_cursor(f"{entry.name}\n")
        if self.files_to_process:
            self.start_transcoding()

    def on_drop_enter(self, drop_target, x, y):
        self.textview.add_css_class("drop-highlight")

    def on_drop_leave(self, drop_target):
        self.textview.remove_css_class("drop-highlight")

    def on_drop(self, drop_target, value, x, y):
        # value is a Gio.File or a list of Gio.Files
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
                # Add all supported video files from the dropped folder
                for entry in os.scandir(path):
                    if entry.is_file() and entry.name.lower().endswith((".mp4", ".mov", ".mkv", ".avi")):
                        paths.append(entry.path)
            else:
                paths.append(path)

        if not paths:
            return False

        self.textview.remove_css_class("drop-highlight")
        self.drop_hint.set_visible(False)  # Hide hint

        self.files_to_process = paths
        self.textbuffer.set_text("\n".join(os.path.basename(p) for p in paths) + "\n")
        self.start_transcoding()
        return True

    def start_transcoding(self):
        if self.is_processing:
            return

        self.is_processing = True
        self.progress.set_fraction(0.0)
        self.progress.set_text("Starting transcoding...")

        thread = threading.Thread(target=self.transcode_files)
        thread.daemon = True
        thread.start()

    def transcode_files(self):
        total = len(self.files_to_process)

        for idx, filepath in enumerate(self.files_to_process, start=1):
            basename = os.path.basename(filepath)
            self.update_progress_text(f"Processing {basename} ({idx}/{total})...")
            success, output_path = transcode_file(filepath, os.path.join(os.path.dirname(filepath), "transcoded"))

            if not success:
                self.update_progress_text(f"Error transcoding {basename}")
            else:
                self.update_progress_text(f"Finished {basename}")

            self.update_progress_fraction(idx / total)

        self.is_processing = False
        self.update_progress_text("All done!")
        self.progress.set_fraction(1.0)
        self.notify_done()


    def update_progress_text(self, text):
        GLib.idle_add(self.progress.set_show_text, True)
        GLib.idle_add(self.progress.set_text, text)

    def update_progress_fraction(self, fraction):
        GLib.idle_add(self.progress.set_fraction, fraction)

    def notify_done(self):
        # Visual cue - change progress bar color briefly
        GLib.idle_add(self.progress.set_show_text, True)
        GLib.idle_add(self.progress.set_text, "Transcoding Complete!")
        # Audio cue
        subprocess.Popen(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"])

class RecoderApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="net.jeena.recoder",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = RecoderWindow(application=self)
        self.window.present()

def main():
    app = RecoderApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())

