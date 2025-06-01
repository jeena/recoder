import os
import gi
import shutil
import subprocess
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, Gdk, GLib
from functools import partial

from config import load_config, save_config
from transcoder_worker import TranscoderWorker

class RecoderWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Recoder")
        self.set_default_size(700, 400)

        self.config = load_config()
        self.current_dir = self.config.get("last_directory", str(os.path.expanduser("~")))

        self.files_to_process = []
        self.transcoder = None

        # UI setup
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.header_bar = Adw.HeaderBar()
        self.toolbar_view = Adw.ToolbarView()
        self.toolbar_view.add_top_bar(self.header_bar)
        self.toolbar_view.set_content(self.vbox)
        self.set_content(self.toolbar_view)

        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textbuffer = self.textview.get_buffer()

        self.drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        self.drop_target.connect("enter", self.on_drop_enter)
        self.drop_target.connect("leave", self.on_drop_leave)
        self.drop_target.connect("drop", self.on_drop)
        self.textview.add_controller(self.drop_target)

        # CSS
        self._setup_css()

        self.drop_hint = Gtk.Label(label="📂 Drop files here to get started")
        self.drop_hint.add_css_class("dim-label")
        self._setup_dim_label_css()

        overlay = Gtk.Overlay()
        overlay.set_child(self.textview)
        overlay.add_overlay(self.drop_hint)
        self.drop_hint.set_halign(Gtk.Align.CENTER)
        self.drop_hint.set_valign(Gtk.Align.CENTER)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_child(overlay)
        self.vbox.append(self.scrolled)
        self.scrolled.set_vexpand(True)
        self.scrolled.set_hexpand(True)

        self.progress = Gtk.ProgressBar()
        self.vbox.append(self.progress)
        self.progress.set_hexpand(True)

    def _setup_css(self):
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

    def _setup_dim_label_css(self):
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

    def on_drop_enter(self, drop_target, x, y):
        self.textview.add_css_class("drop-highlight")
        return True

    def on_drop_leave(self, drop_target):
        self.textview.remove_css_class("drop-highlight")
        return True

    def on_drop(self, drop_target, value, x, y):
        GLib.idle_add(partial(self.process_drop_value, value))
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

        self.textview.remove_css_class("drop-highlight")
        self.drop_hint.set_visible(False)
        self.files_to_process = paths
        self.textbuffer.set_text("\n".join(os.path.basename(p) for p in paths) + "\n")
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
        )
        self.transcoder.start()

    def update_progress(self, text, fraction):
        self.progress.set_show_text(True)
        self.progress.set_text(text)
        self.progress.set_fraction(fraction)

    def notify_done(self):
        self.progress.set_show_text(True)
        self.progress.set_text("Transcoding Complete!")
        self.play_complete_sound()

    def play_complete_sound(self):
        if shutil.which("canberra-gtk-play"):
            subprocess.Popen(["canberra-gtk-play", "--id", "complete"])
        else:
            print("canberra-gtk-play not found.")
