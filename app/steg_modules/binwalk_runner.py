# app/steg_modules/binwalk_runner.py

import subprocess
import os
import shutil
import platform

def run_binwalk(filepath: str, output_dir: str) -> tuple[list[str], str]:
    """
    Runs binwalk -e to extract embedded content.
    Returns: (list of extracted files, parsed binwalk output)
    """
    base_filename = os.path.basename(filepath)
    extracted_folder = os.path.join(output_dir, f"_{base_filename}.extracted")

    # Clean previous extractions
    if os.path.exists(extracted_folder):
        shutil.rmtree(extracted_folder)

    # Run binwalk
    try:
        result = subprocess.run(
            ["binwalk", "-e", filepath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
    except Exception as e:
        return [], f"Error running binwalk: {e}"

    # Collect extracted files (if any)
    extracted_files = []
    if os.path.exists(extracted_folder):
        for fname in os.listdir(extracted_folder):
            fpath = os.path.join(extracted_folder, fname)
            if os.path.isfile(fpath):
                # Copy to output_dir for download
                dest_path = os.path.join(output_dir, fname)
                shutil.copy(fpath, dest_path)
                extracted_files.append(fname)

    return extracted_files, result.stdout
