# app/steg_modules/exif_metadata.py

import subprocess
import json
import platform

def extract_exif_metadata(filepath: str) -> dict:
    exiftool_cmd = "exiftool"
    if platform.system() == "Windows":
        exiftool_cmd += ".exe"

    try:
        result = subprocess.run(
            [exiftool_cmd, "-json", filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False  # <-- allow errors, we handle them
        )

        # If output is empty or parsing fails
        if result.returncode != 0 or not result.stdout.strip():
            return {"Notice": "No readable EXIF metadata or unsupported file format."}

        metadata = json.loads(result.stdout)[0]
        return metadata

    except Exception as e:
        return {"Error": str(e)}
