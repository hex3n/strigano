import subprocess
import os

def run_steghide(file_path, output_dir, password=None):
    """
    Run steghide extraction on the provided file.
    If a password is supplied, it's used in the command.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "steghide_extracted.txt")

    try:
        cmd = ["steghide", "extract", "-sf", file_path, "-xf", output_file, "-f"]
        if password:
            cmd.extend(["-p", password])
        else:
            cmd.extend(["-p", ""])  # blank password if not given

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        success = "wrote extracted data" in result.stdout.lower() or os.path.exists(output_file)

        if success:
            return True, result.stdout.strip(), os.path.basename(output_file)
        else:
            return False, result.stderr.strip() or result.stdout.strip(), None

    except Exception as e:
        return False, f"Error running steghide: {e}", None
