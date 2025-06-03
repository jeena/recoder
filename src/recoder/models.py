from gi.repository import GObject, Gio

class FileStatus(GObject.GEnum):
    __gtype_name__ = 'FileStatus'
    ERROR = 0
    WAITING = 1
    PROCESSING = 2
    DONE = 3

class FileItem(GObject.GObject):
    __gtype_name__ = 'FileItem'

    file = GObject.Property(type=Gio.File)
    progress = GObject.Property(type=int, minimum=0, maximum=100, default=0)
    status = GObject.Property(type=FileStatus, default=FileStatus.WAITING)

    def __init__(self, file: Gio.File):
        super().__init__()
        self.file = file
