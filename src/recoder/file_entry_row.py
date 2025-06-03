import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from recoder.models import FileStatus

ICONS = {
    FileStatus.WAITING: "media-playback-pause-symbolic",
    FileStatus.PROCESSING: "view-refresh-symbolic",
    FileStatus.DONE: "task-complete-symbolic",
    FileStatus.ERROR: "dialog-error-symbolic",
}

LABELS = {
    FileStatus.WAITING: "Waiting",
    FileStatus.DONE: "Done",
    FileStatus.ERROR: "Error",
}

@Gtk.Template(resource_path="/net/jeena/recoder/file_entry_row.ui")
class FileEntryRow(Gtk.ListBoxRow):
    __gtype_name__ = "FileEntryRow"

    icon = Gtk.Template.Child()
    label = Gtk.Template.Child()
    progress_label = Gtk.Template.Child()
    level_bar = Gtk.Template.Child()

    def __init__(self, item):
        super().__init__()
        self.item = item
        self.item.connect("notify::status", self.update_display)
        self.item.connect("notify::progress", self.update_display)
        self.update_display()

    def update_display(self, *args):
        basename = self.item.file.get_basename()
        self.label.set_text(basename)

        icon_name = ICONS.get(self.item.status, "object-select-symbolic")
        self.icon.set_from_icon_name(icon_name)

        if self.item.status == FileStatus.PROCESSING:
            self.progress_label.set_text(f"{self.item.progress}%")
            self.level_bar.set_value(self.item.progress)
        else:
            self.progress_label.set_text(LABELS.get(self.item.status, ""))
            self.level_bar.set_value(100 if self.item.status == FileStatus.DONE else 0)
