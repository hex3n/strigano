"""Audio forensics: metadata, a dual-channel spectrogram, and strings.

Unlike the original (WAV only), this loads WAV/FLAC/OGG via soundfile and
falls back to an ffmpeg transcode for MP3 and anything else, so the formats
the upload form accepts actually work.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy.signal import spectrogram

from .. import config, tools
from .images import extract_strings

try:  # soundfile is optional but strongly preferred
    import soundfile as sf

    _HAVE_SOUNDFILE = True
except Exception:  # pragma: no cover
    sf = None
    _HAVE_SOUNDFILE = False


def _load_samples(path: str) -> tuple[int, np.ndarray]:
    """Return (sample_rate, samples) as a 1-D or 2-D float array.

    Tries soundfile, then scipy for WAV, then an ffmpeg transcode to WAV.
    Raises RuntimeError with a readable message if none can decode the file.
    """
    if _HAVE_SOUNDFILE:
        try:
            data, rate = sf.read(path, always_2d=False)
            return rate, np.asarray(data, dtype=float)
        except Exception:
            pass

    if Path(path).suffix.lower() == ".wav":
        try:
            from scipy.io import wavfile

            rate, data = wavfile.read(path)
            return rate, np.asarray(data, dtype=float)
        except Exception:
            pass

    # Last resort: transcode to a temp WAV with ffmpeg, then read that.
    if tools.is_available("ffmpeg"):
        with tempfile.TemporaryDirectory() as tmp:
            wav = str(Path(tmp) / "decoded.wav")
            res = tools.run_tool("ffmpeg", ["-y", "-i", path, wav], timeout=120)
            if res.ok and Path(wav).exists():
                from scipy.io import wavfile

                rate, data = wavfile.read(wav)
                return rate, np.asarray(data, dtype=float)

    raise RuntimeError(
        "Could not decode audio. Install soundfile (pip) for WAV/FLAC/OGG, "
        "or ffmpeg for MP3 and other formats."
    )


def ffprobe_metadata(path: str) -> str:
    res = tools.run_tool(
        "ffprobe", ["-v", "error", "-show_streams", "-show_format", path]
    )
    if not res.available:
        return "ffprobe is not installed; container metadata skipped."
    return (res.stdout or res.stderr).strip() or "No metadata reported."


def _maxpool_cols(mat: np.ndarray, max_cols: int) -> np.ndarray:
    """Downsample a matrix along time (columns) into max_cols max-pooled bins.

    Max-pooling keeps the bright spectrogram features where hidden text lives,
    rather than averaging them away, and bounds the output size for long clips.
    """
    cols = mat.shape[1]
    if cols <= max_cols:
        return mat
    edges = np.linspace(0, cols, max_cols + 1).astype(int)
    out = np.empty((mat.shape[0], max_cols), dtype=mat.dtype)
    for i in range(max_cols):
        a = edges[i]
        b = edges[i + 1] if edges[i + 1] > a else a + 1
        out[:, i] = mat[:, a:b].max(axis=1)
    return out


def build_spectrogram_html(path: str, out_dir: str | Path) -> str:
    """Write an interactive dual-channel spectrogram HTML and return its name."""
    import plotly.graph_objects as go
    from plotly.offline import plot

    rate, data = _load_samples(path)
    if data.ndim == 1:
        data = np.column_stack((data, data))
    left, right = data[:, 0], data[:, 1]

    f, t, s_left = spectrogram(left, fs=rate, nperseg=1024, noverlap=900,
                               scaling="density")
    _, _, s_right = spectrogram(right, fs=rate, nperseg=1024, noverlap=900,
                                scaling="density")

    s_left = 10 * np.log10(s_left + 1e-10)
    s_right = 10 * np.log10(s_right + 1e-10)

    # Cap time resolution so the HTML stays small regardless of clip length.
    max_cols = config.SPECTRO_MAX_COLS
    s_left = _maxpool_cols(s_left, max_cols)
    s_right = _maxpool_cols(s_right, max_cols)

    s_left = np.clip(s_left, np.percentile(s_left, 2), np.percentile(s_left, 98))
    s_right = np.clip(s_right, np.percentile(s_right, 2), np.percentile(s_right, 98))

    gap = np.full((50, s_left.shape[1]), np.nan)
    # Round to one decimal: dB precision is plenty for a heatmap and it roughly
    # halves the serialised size.
    combined = np.round(np.vstack((s_left, gap, s_right)), 1)
    y = np.linspace(0, 2 * f[-1] + 2000, combined.shape[0])
    x = np.linspace(float(t[0]), float(t[-1]), combined.shape[1])

    fig = go.Figure(
        go.Heatmap(z=combined, x=x, y=y, colorscale="Inferno", zsmooth="best",
                   colorbar_title="dB/Hz")
    )
    fig.update_layout(
        title="Dual-channel spectrogram",
        xaxis_title="Time [s]", yaxis_title="Frequency [Hz]",
        template="plotly_dark", height=850,
        margin=dict(l=50, r=50, t=40, b=40),
        # Drag pans instead of zooming, so an accidental drag never loses the
        # view. Zoom is on the scroll wheel, double-click resets.
        dragmode="pan",
    )

    # A visible modebar with an always-present reset ("autoscale") button, and
    # the lasso/box-select tools removed since they do not apply to a heatmap.
    plot_config = {
        "displayModeBar": True,
        "displaylogo": False,
        "scrollZoom": True,
        "doubleClick": "reset",
        "responsive": True,
        "modeBarButtonsToRemove": ["select2d", "lasso2d"],
    }

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = f"{Path(path).stem}_spectrogram.html"
    # Inline plotly.js so the spectrogram renders with no internet access,
    # which matters on a CTF box behind a restrictive VPN.
    plot(fig, filename=str(out / name), auto_open=False,
         include_plotlyjs=True, config=plot_config)
    return name


def audio_strings(path: str, limit: int = 100) -> list[str]:
    ascii_found, _ = extract_strings(path)
    return ascii_found[:limit] or ["No visible ASCII strings."]
