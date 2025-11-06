import os
import subprocess
import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram
import plotly.graph_objects as go
from plotly.offline import plot


def analyze_audio(path):
    results = {}
    output_dir = "static/output"
    os.makedirs(output_dir, exist_ok=True)

    # --- Metadata ---
    try:
        metadata = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", path],
            stderr=subprocess.STDOUT
        ).decode(errors="ignore")
        results["Metadata"] = metadata
    except Exception as e:
        results["Metadata"] = f"⚠️ ffprobe not available: {e}"

    # --- Audacity-style spectrogram (dual channel stacked vertically) ---
    try:
        rate, data = wavfile.read(path)
        if data.ndim == 1:
            # Mono → duplicate to mimic stereo layout
            data = np.column_stack((data, data))

        left, right = data[:, 0], data[:, 1]

        # High temporal resolution for visible “text” patterns
        f, t, S_left = spectrogram(left, fs=rate, nperseg=1024, noverlap=900, scaling="density")
        _, _, S_right = spectrogram(right, fs=rate, nperseg=1024, noverlap=900, scaling="density")

        # Convert to dB
        S_left_db = 10 * np.log10(S_left + 1e-10)
        S_right_db = 10 * np.log10(S_right + 1e-10)

        # Normalize dynamic range
        S_left_db = np.clip(S_left_db, np.percentile(S_left_db, 2), np.percentile(S_left_db, 98))
        S_right_db = np.clip(S_right_db, np.percentile(S_right_db, 2), np.percentile(S_right_db, 98))

        # Combine vertically with spacing (so they don’t overlap)
        gap = np.full((50, S_left_db.shape[1]), np.nan)  # visual gap
        combined = np.vstack((S_left_db, gap, S_right_db))
        f_combined = np.linspace(0, 2 * f[-1] + 2000, combined.shape[0])

        fig = go.Figure(
            data=go.Heatmap(
                z=combined,
                x=t,
                y=f_combined,
                colorscale="Inferno",
                zsmooth="best",
                colorbar_title="Power/Frequency (dB/Hz)",
            )
        )

        fig.update_layout(
            title="Audacity-like Dual Channel Spectrogram (Linear Scale)",
            xaxis_title="Time [s]",
            yaxis_title="Frequency [Hz]",
            template="plotly_dark",
            height=850,
            margin=dict(l=50, r=50, t=40, b=40),
        )

        base = os.path.splitext(os.path.basename(path))[0]
        html_path = os.path.join(output_dir, f"{base}_spectrogram.html")
        plot(fig, filename=html_path, auto_open=False, include_plotlyjs="cdn")
        results["SpectrogramPath"] = html_path

    except Exception as e:
        results["SpectrogramPath"] = f"❌ Error generating spectrogram: {e}"

    # --- Extract printable strings ---
    try:
        with open(path, "rb") as f:
            b = f.read()
        strings, cur = [], []
        for byte in b:
            if 32 <= byte < 127:
                cur.append(chr(byte))
            else:
                if len(cur) >= 4:
                    strings.append("".join(cur))
                cur = []
        if len(cur) >= 4:
            strings.append("".join(cur))
        results["Embedded Strings"] = strings[:50] or ["No visible ASCII strings."]
    except Exception as e:
        results["Embedded Strings"] = [f"❌ Error extracting strings: {e}"]

    return results
