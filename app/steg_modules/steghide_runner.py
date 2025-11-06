import os
import subprocess
import shutil

def run_steghide(file_path: str, output_dir: str, passphrase: str = ""):
    steghide_dir = os.path.join(output_dir, "steghide")
    
    # Clean previous run
    if os.path.exists(steghide_dir):
        shutil.rmtree(steghide_dir)
    os.makedirs(steghide_dir, exist_ok=True)

    # Attempt to extract
    output_file_path = os.path.join(steghide_dir, "extracted.data")
    cmd = [
        "steghide", "extract",
        "-sf", file_path,
        "-xf", output_file_path,
        "-p", passphrase,
        "-f"  # force overwrite
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        if os.path.exists(output_file_path):
            return True, "Data extracted!", "steghide/extracted.data"
        else:
            return False, "Steghide ran, but no output file was saved.", None
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode().strip()
        return False, f"Steghide failed: {error_msg}", None
