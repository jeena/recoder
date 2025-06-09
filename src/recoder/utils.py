import os
import shutil
import subprocess
from typing import Union, List
from gi.repository import Gio, Notify

from recoder.models import FileItem

SUPPORTED_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi")

def extract_video_files(value: Union[Gio.File, List[Gio.File]]) -> List[FileItem]:
    if isinstance(value, Gio.File):
        uris = [value]
    elif isinstance(value, list):
        uris = value
    else:
        return []

    files = []
    for file in uris:
        path = file.get_path()
        if os.path.isdir(path):
            for entry in os.scandir(path):
                if entry.is_file() and entry.name.lower().endswith(SUPPORTED_EXTENSIONS):
                    files.append(FileItem(Gio.File.new_for_path(entry.path)))
        elif os.path.isfile(path) and path.lower().endswith(SUPPORTED_EXTENSIONS):
            files.append(FileItem(file))

    return files

def notify_done(title, body):
    notification = Notify.Notification.new(title, body, "net.jeena.Recoder")
    notification.show()

def play_complete_sound():
    if shutil.which("canberra-gtk-play"):
        subprocess.Popen(["canberra-gtk-play", "--id", "complete"])
        return

    sound_paths = [
        os.path.expanduser("~/.local/share/sounds/recoder/complete.oga"),
        "/usr/share/sounds/freedesktop/stereo/complete.oga",
        "/usr/share/sounds/recoder/complete.oga",
        "/app/share/sounds/complete.oga",
    ]

    players = ["paplay", "play"]

    for player in players:
        if shutil.which(player):
            for path in sound_paths:
                if os.path.isfile(path) and os.access(path, os.R_OK):
                    subprocess.Popen([player, path])
                    return