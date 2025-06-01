import os
import threading
from gi.repository import GLib
import subprocess

def transcode_file(input_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    basename = os.path.basename(input_path)
    output_path = os.path.join(output_dir, basename)

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", output_path
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0, output_path

class TranscoderWorker:
    def __init__(self, files, progress_callback=None, done_callback=None):
        self.files = files
        self.progress_callback = progress_callback
        self.done_callback = done_callback
        self.is_processing = False

    def start(self):
        if self.is_processing:
            return
        self.is_processing = True
        thread = threading.Thread(target=self._process_files)
        thread.daemon = True
        thread.start()

    def _process_files(self):
        total = len(self.files)
        for idx, filepath in enumerate(self.files):
            basename = os.path.basename(filepath)
            self._update_progress(f"Processing {basename} ({idx}/{total})...", idx / total)

            success, output_path = transcode_file(filepath, os.path.join(os.path.dirname(filepath), "transcoded"))
            if not success:
                self._update_progress(f"Error transcoding {basename}", idx + 1 / total)
            else:
                self._update_progress(f"Finished {basename}", idx + 1 / total)

        self.is_processing = False
        self._update_progress("All done!", 1.0)
        self._notify_done()

    def _update_progress(self, text, fraction):
        if self.progress_callback:
            GLib.idle_add(self.progress_callback, text, fraction)

    def _notify_done(self):
        if self.done_callback:
            GLib.idle_add(self.done_callback)
