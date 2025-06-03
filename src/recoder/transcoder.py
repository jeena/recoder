import os
import threading
import subprocess
import re
from gi.repository import GLib

from recoder.models import FileStatus, FileItem

class Transcoder:
    TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")

    def __init__(self, file_items, progress_callback=None, done_callback=None, file_done_callback=None):
        self.file_items = file_items
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        self.file_done_callback = file_done_callback
        self.is_processing = False

    def start(self):
        if self.is_processing:
            return
        self.is_processing = True
        thread = threading.Thread(target=self._process_files)
        thread.daemon = True
        thread.start()

    def _process_files(self):
        total = len(self.file_items)
        for idx, file_item in enumerate(self.file_items, start=1):
            filepath = file_item.file.get_path()
            basename = os.path.basename(filepath)
            self._update_progress(f"Starting {basename}", (idx - 1) / total)

            success, output_path = self._transcode_file(
                filepath,
                os.path.join(os.path.dirname(filepath), "transcoded"),
                basename,
                idx,
                total,
            )
            if not success:
                self._update_progress(f"Error transcoding {basename}", idx / total)
            else:
                self._update_progress(f"Finished {basename}", idx / total)

            if self.file_done_callback:
                GLib.idle_add(self.file_done_callback, filepath)

        self.is_processing = False
        self._update_progress("All done!", 1.0)
        self._notify_done()

    def _transcode_file(self, input_path, output_dir, basename, idx, total):
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, basename)

        # Get duration of input file
        duration = self._get_duration(input_path)
        if duration is None:
            duration = 1.0  # fallback to avoid division by zero

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-c:a",
            "aac",
            output_path,
        ]

        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)

        while True:
            line = process.stderr.readline()
            if not line:
                break

            match = self.TIME_RE.search(line)
            if match:
                hours, minutes, seconds, milliseconds = map(int, match.groups())
                elapsed = hours * 3600 + minutes * 60 + seconds + milliseconds / 100
                progress_fraction = min(elapsed / duration, 1.0)
                overall_fraction = (idx - 1 + progress_fraction) / total
                self._update_progress(f"Transcoding {basename}", overall_fraction)

        process.wait()
        success = process.returncode == 0
        return success, output_path

    def _get_duration(self, input_path):
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_path,
        ]
        try:
            output = subprocess.check_output(cmd, universal_newlines=True)
            return float(output.strip())
        except Exception:
            return None

    def _update_progress(self, text, fraction):
        if self.progress_callback:
            GLib.idle_add(self.progress_callback, text, fraction)

    def _notify_done(self):
        if self.done_callback:
            GLib.idle_add(self.done_callback)
