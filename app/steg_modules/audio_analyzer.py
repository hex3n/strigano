import subprocess, os
import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile

def analyze_audio(filepath):
    output = {}

    # --- Metadata (using ffprobe if available)
    try:
        cmd = ["ffprobe", "-hide_banner", "-show_format", "-show_streams", filepath]
        meta = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8")
        output["Metadata"] = meta
    except Exception as e:
        output["Metadata"] = f"ffprobe not available: {e}"

    # --- Generate spectrogram (for WAV/MP3)
    try:
        if filepath.lower().endswith((".wav", ".mp3", ".flac", ".ogg")):
            spectrogram_path = os.path.join("static", "output", "spectrogram.png")

            # Load audio for spectrogram
            rate, data = wavfile.read(filepath)
            plt.figure(figsize=(10, 4))
            plt.specgram(data[:, 0] if len(data.shape) > 1 else data, Fs=rate, cmap="inferno")
            plt.xlabel("Time (s)")
            plt.ylabel("Frequency (Hz)")
            plt.title("Spectrogram")
            plt.colorbar(label="Intensity (dB)")
            plt.tight_layout()
            plt.savefig(spectrogram_path)
            plt.close()
            output["spectrogram"] = spectrogram_path
        else:
            output["Spectrogram"] = "Unsupported format"
    except Exception as e:
        output["Spectrogram"] = str(e)

    # --- Strings extraction
    try:
        result = subprocess.check_output(["strings", filepath]).decode("utf-8").splitlines()
        output["Embedded Strings"] = result[:50]
    except Exception as e:
        output["Embedded Strings"] = [f"Error running strings: {e}"]

    # --- Binwalk analysis
    try:
        binwalk_result = subprocess.check_output(["binwalk", filepath]).decode("utf-8")
        output["Binwalk Analysis"] = binwalk_result
    except Exception as e:
        output["Binwalk Analysis"] = f"Binwalk not available: {e}"

    return output
