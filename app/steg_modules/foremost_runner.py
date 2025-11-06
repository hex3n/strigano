# app/steg_modules/foremost_runner.py
import subprocess
import os
import shutil

def run_foremost(file_path: str, output_dir: str):
    foremost_dir = os.path.join(output_dir, "foremost")
    
    # Cleanup if exists
    if os.path.exists(foremost_dir):
        shutil.rmtree(foremost_dir)
    
    os.makedirs(foremost_dir, exist_ok=True)

    # Run Foremost
    cmd = ["foremost", "-i", file_path, "-o", foremost_dir]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        return [], f"Foremost failed: {e.stderr.decode()}"

    # Collect recovered files
    recovered_files = []
    for root, dirs, files in os.walk(foremost_dir):
        for f in files:
            if f == "audit.txt":
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, output_dir)
            recovered_files.append(rel_path)

    # Read audit.txt
    audit_path = os.path.join(foremost_dir, "audit.txt")
    audit_log = ""
    if os.path.exists(audit_path):
        with open(audit_path, "r") as f:
            audit_log = f.read()

    return recovered_files, audit_log
