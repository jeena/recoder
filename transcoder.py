import os
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
