# app/steg_modules/zsteg_runner.py

import subprocess

def run_zsteg(image_path: str) -> str:
    try:
        result = subprocess.run(
            ["zsteg", image_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"[!] Zsteg error: {result.stderr.strip()}"
    except Exception as e:
        return f"[!] Zsteg failed to run: {e}"
