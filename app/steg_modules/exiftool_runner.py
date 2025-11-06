import subprocess

def run_exiftool(image_path: str) -> str:
    try:
        result = subprocess.run(
            ["exiftool", image_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"[!] Failed to run exiftool: {e}"
