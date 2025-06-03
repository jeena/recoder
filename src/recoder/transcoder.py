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

            # Set status PROCESSING and reset progress to 0
            GLib.idle_add(file_item.set_property, "status", FileStatus.PROCESSING)
            GLib.idle_add(file_item.set_property, "progress", 0)
            
            self._update_progress(f"Starting {basename}", (idx - 1) / total)

            success, output_path = self._transcode_file(
                filepath,
                os.path.join(os.path.dirname(filepath), "transcoded"),
                basename,
                idx,
                total,
                file_item,  # Pass file_item to update progress inside _transcode_file
            )

            # Update status DONE or ERROR after processing
            new_status = FileStatus.DONE if success else FileStatus.ERROR
            GLib.idle_add(file_item.set_property, "status", new_status)
            GLib.idle_add(file_item.set_property, "progress", 100 if success else 0)

            if not success:
                self._update_progress(f"Error transcoding {basename}", idx / total)
            else:
                self._update_progress(f"Finished {basename}", idx / total)

            if self.file_done_callback:
                GLib.idle_add(self.file_done_callback, filepath)

        self.is_processing = False
        self._update_progress("All done!", 1.0)
        self._notify_done()

    def _transcode_file(self, input_path, output_dir, basename, idx, total, file_item=None):
        os.makedirs(output_dir, exist_ok=True)
        output_path = self._get_output_path(output_dir, basename)

        duration = self._get_duration(input_path) or 1.0
        width, height, rotate = self._get_video_info(input_path)

        vf = self._build_filters(width, height, rotate)

        cmd = self._build_ffmpeg_command(input_path, output_path, vf)

        return self._run_ffmpeg(cmd, duration, idx, total, basename, file_item, output_path)


    def _get_output_path(self, output_dir, basename):
        name, _ = os.path.splitext(basename)
        return os.path.join(output_dir, f"{name}.mov")


    def _build_filters(self, width, height, rotate):
        filters = []

        # If rotated or vertical, transpose and swap dimensions
        if rotate in [90, 270] or (width and height and height > width):
            filters.append("transpose=1")
            width, height = height, width  # Swap dimensions after transpose

        # Resize only if not 1920x1080
        if (width, height) != (1920, 1080):
            filters.append("scale=1920:1080")

        return ",".join(filters) if filters else None


    def _build_ffmpeg_command(self, input_path, output_path, vf):
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-vcodec", "dnxhd",
            "-acodec", "pcm_s16le",
            "-b:v", "36M",
            "-pix_fmt", "yuv422p",
            "-r", "30000/1001",
            "-f", "mov",
            "-map_metadata", "0",
        ]

        if vf:
            cmd += ["-vf", vf]

        cmd.append(output_path)
        return cmd


    def _run_ffmpeg(self, cmd, duration, idx, total, basename, file_item, output_path):
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)

        while True:
            line = process.stderr.readline()
            if not line:
                break

            match = self.TIME_RE.search(line)
            if match:
                hours, minutes, seconds, milliseconds = map(int, match.groups())
                elapsed = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
                progress_fraction = min(elapsed / duration, 1.0)
                overall_fraction = (idx - 1 + progress_fraction) / total
                self._update_progress(f"Transcoding {basename}", overall_fraction)

                if file_item:
                    percent = int(progress_fraction * 100)
                    GLib.idle_add(file_item.set_property, "progress", percent)

        process.wait()
        success = process.returncode == 0
        return success, output_path





    def _get_duration(self, input_path):
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path,
        ]
        try:
            output = subprocess.check_output(cmd, text=True)
            return float(output.strip())
        except Exception:
            return None

    def _get_video_info(self, input_path):
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height:stream_tags=rotate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path,
        ]
        try:
            output = subprocess.check_output(cmd, text=True).splitlines()
            width = int(output[0])
            height = int(output[1])
            rotate = int(output[2]) if len(output) > 2 else 0
            return width, height, rotate
        except Exception:
            return None, None, 0

    def _update_progress(self, text, fraction):
        if self.progress_callback:
            GLib.idle_add(self.progress_callback, text, fraction)

    def _notify_done(self):
        if self.done_callback:
            GLib.idle_add(self.done_callback)
