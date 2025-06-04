import os
import threading
import subprocess
import re
import signal

from gi.repository import GLib, GObject
from recoder.models import FileStatus, FileItem


class BatchStatus(GObject.GEnum):
    __gtype_name__ = 'BatchStatus'

    IDLE = 0
    RUNNING = 1
    PAUSED = 2
    DONE = 3
    STOPPED = 4
    ERROR = 5


class Transcoder(GObject.GObject):
    TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")

    batch_progress = GObject.Property(type=int, minimum=0, maximum=100, default=0)
    batch_status = GObject.Property(type=BatchStatus, default=BatchStatus.IDLE)

    def __init__(self, file_items):
        super().__init__()
        self.file_items = file_items
        self.is_processing = False
        self._stop_requested = False
        self._paused = threading.Event()
        self._paused.set()
        self._process = None

    def start(self):
        if self.is_processing:
            return
        self.is_processing = True
        self._stop_requested = False
        self._paused.set()
        self.batch_status = BatchStatus.RUNNING
        threading.Thread(target=self._process_files, daemon=True).start()

    def pause(self):
        self._paused.clear()
        self.batch_status = BatchStatus.PAUSED
        if self._process and self._process.poll() is None:
            self._process.send_signal(signal.SIGSTOP)

    def resume(self):
        self._paused.set()
        self.batch_status = BatchStatus.RUNNING
        if self._process and self._process.poll() is None:
            self._process.send_signal(signal.SIGCONT)

    def stop(self):
        self._stop_requested = True
        self._paused.set()
        if self._process and self._process.poll() is None:
            self._process.terminate()
        self.batch_status = BatchStatus.STOPPED

    def _process_files(self):
        total = len(self.file_items)

        for idx, file_item in enumerate(self.file_items, start=1):
            if self._stop_requested:
                GLib.idle_add(file_item.set_property, "status", FileStatus.WAITING)
                continue

            path = file_item.file.get_path()
            base = os.path.basename(path)

            GLib.idle_add(file_item.set_property, "status", FileStatus.PROCESSING)
            GLib.idle_add(file_item.set_property, "progress", 0)

            success, _ = self._transcode_file(path, os.path.join(os.path.dirname(path), "transcoded"),
                                              base, idx, total, file_item)

            new_status = FileStatus.DONE if success else FileStatus.ERROR
            GLib.idle_add(file_item.set_property, "status", new_status)
            GLib.idle_add(file_item.set_property, "progress", 100 if success else 0)

            # Fix: Only set ERROR if not stopped by user
            if not success and not self._stop_requested:
                self.batch_status = BatchStatus.ERROR
                break

            if self._stop_requested:
                break

        self.is_processing = False

        if not self._stop_requested and self.batch_status != BatchStatus.ERROR:
            self.batch_status = BatchStatus.DONE
        elif self._stop_requested:
            self.batch_status = BatchStatus.STOPPED

        GLib.idle_add(self.set_property, "batch_progress", 0)

    def _transcode_file(self, input_path, output_dir, basename, idx, total, file_item):
        os.makedirs(output_dir, exist_ok=True)
        output_path = self._get_output_path(output_dir, basename)

        duration = self._get_duration(input_path) or 1.0
        width, height, rotate = self._get_video_info(input_path)
        vf = self._build_filters(width, height, rotate)
        cmd = self._build_ffmpeg_command(input_path, output_path, vf)

        return self._run_ffmpeg(cmd, duration, idx, total, file_item, output_path)

    def _run_ffmpeg(self, cmd, duration, idx, total, file_item, output_path):
        self._process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)

        while True:
            self._paused.wait()
            if self._stop_requested:
                self._process.terminate()
                return False, output_path

            line = self._process.stderr.readline()
            if not line:
                break

            match = self.TIME_RE.search(line)
            if match:
                h, m, s, ms = map(int, match.groups())
                elapsed = h * 3600 + m * 60 + s + ms / 1000.0
                file_progress = min(elapsed / duration, 1.0)

                file_percent = int(file_progress * 100)
                batch_fraction = (idx - 1 + file_progress) / total
                batch_percent = int(batch_fraction * 100)

                GLib.idle_add(file_item.set_property, "progress", file_percent)
                GLib.idle_add(self.set_property, "batch_progress", batch_percent)

        self._process.wait()
        return self._process.returncode == 0, output_path

    def _get_output_path(self, out_dir, basename):
        name, _ = os.path.splitext(basename)
        return os.path.join(out_dir, f"{name}.mov")

    def _get_duration(self, path):
        try:
            out = subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", path
            ], text=True)
            return float(out.strip())
        except Exception:
            return None

    def _get_video_info(self, path):
        try:
            out = subprocess.check_output([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height:stream_tags=rotate",
                "-of", "default=noprint_wrappers=1:nokey=1", path
            ], text=True).splitlines()
            width = int(out[0])
            height = int(out[1])
            rotate = int(out[2]) if len(out) > 2 else 0
            return width, height, rotate
        except Exception:
            return None, None, 0

    def _build_filters(self, width, height, rotate):
        filters = []
        if rotate in [90, 270] or (width and height and height > width):
            filters.append("transpose=1")
            width, height = height, width
        if (width, height) != (1920, 1080):
            filters.append("scale=1920:1080")
        return ",".join(filters) if filters else None

    def _build_ffmpeg_command(self, in_path, out_path, vf):
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-vcodec", "dnxhd", "-acodec", "pcm_s16le",
            "-b:v", "36M", "-pix_fmt", "yuv422p", "-r", "30000/1001",
            "-f", "mov", "-map_metadata", "0"
        ]
        if vf:
            cmd += ["-vf", vf]
        cmd.append(out_path)
        return cmd
