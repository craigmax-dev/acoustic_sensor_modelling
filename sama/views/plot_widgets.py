"""
Plot Widgets

Four Matplotlib-based plot widgets embedded in QWidget containers via
FigureCanvasQTAgg.  Each widget exposes an ``update_plot`` method that
the Controller calls with freshly computed data.

Widgets:
    DetectionVolumePlot  – 3-D detection boundary surface
    SnrDistancePlot      – SNR vs distance line chart
    PolarDirectivityPlot – Polar beam pattern
    SpectrumPlot         – Frequency spectrum overlay
"""

import logging

import numpy as np
import matplotlib.cm as cm
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 – registers 3D projection

from PyQt6.QtWidgets import QWidget, QVBoxLayout

logger = logging.getLogger(__name__)


class DetectionVolumePlot(QWidget):
    """3-D detection boundary surface plot."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._fig = Figure(figsize=(5, 4))
        self.canvas = FigureCanvasQTAgg(self._fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._ax = self._fig.add_subplot(111, projection="3d")

    def update_plot(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
    ) -> None:
        """Render the 3-D detection boundary surface.

        Args:
            x: 2-D array of X coordinates (m).
            y: 2-D array of Y coordinates (m).
            z: 2-D array of Z coordinates (m).
        """
        self._ax.cla()
        r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
        self._ax.plot_surface(
            x, y, z,
            facecolors=cm.viridis(
                (r - r.min()) / (r.max() - r.min() + 1e-9)
            ),
            alpha=0.7,
            linewidth=0,
            antialiased=True,
        )
        self._ax.set_xlabel("X (m)")
        self._ax.set_ylabel("Y (m)")
        self._ax.set_zlabel("Z (m)")
        self._ax.set_title("3-D Detection Volume")
        self._fig.tight_layout()
        self.canvas.draw()


class SnrDistancePlot(QWidget):
    """SNR vs Distance line chart."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._fig = Figure(figsize=(5, 4))
        self.canvas = FigureCanvasQTAgg(self._fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._ax = self._fig.add_subplot(111)

    def update_plot(
        self,
        distances: np.ndarray,
        snr_values: np.ndarray,
        required_snr: float,
    ) -> None:
        """Render the SNR vs distance chart.

        Args:
            distances:    1-D array of distances (m).
            snr_values:   1-D array of SNR values (dB).
            required_snr: Required SNR threshold (dB).
        """
        self._ax.cla()
        self._ax.plot(distances, snr_values, label="SNR")
        self._ax.axhline(
            required_snr, color="red", linestyle="--", label=f"Required SNR ({required_snr:.1f} dB)"
        )
        # Shade detection zone (where SNR >= required_snr)
        self._ax.fill_between(
            distances,
            snr_values,
            required_snr,
            where=(snr_values >= required_snr),
            alpha=0.2,
            color="green",
            label="Detection Zone",
        )
        self._ax.set_xlabel("Distance (m)")
        self._ax.set_ylabel("SNR (dB)")
        self._ax.set_title("SNR vs Distance")
        self._ax.legend()
        self._ax.grid(True)
        self._fig.tight_layout()
        self.canvas.draw()


class PolarDirectivityPlot(QWidget):
    """Polar beam pattern plot."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._fig = Figure(figsize=(5, 4))
        self.canvas = FigureCanvasQTAgg(self._fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._ax = self._fig.add_subplot(111, projection="polar")

    def update_plot(
        self,
        theta: np.ndarray,
        pattern_db: np.ndarray,
    ) -> None:
        """Render the polar beam pattern.

        Args:
            theta:      1-D array of azimuth angles (rad).
            pattern_db: 1-D array of normalised power pattern (linear, 0..1).
        """
        self._ax.cla()
        # Convert linear power to dB, clip to -40 dB floor
        with np.errstate(divide="ignore"):
            db = 10.0 * np.log10(np.maximum(pattern_db, 1e-4))
        db = np.clip(db, -40.0, 0.0)
        self._ax.plot(theta, db)
        self._ax.set_title("Array Beam Pattern")
        self._fig.tight_layout()
        self.canvas.draw()


class SpectrumPlot(QWidget):
    """Frequency spectrum overlay plot."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._fig = Figure(figsize=(5, 4))
        self.canvas = FigureCanvasQTAgg(self._fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._ax = self._fig.add_subplot(111)

    def update_plot(
        self,
        freq_axis: np.ndarray,
        drone_spectrum: np.ndarray,
        noise_spectrum: np.ndarray,
    ) -> None:
        """Render the frequency spectrum overlay.

        Args:
            freq_axis:      1-D array of frequency bins (Hz).
            drone_spectrum: 1-D array of drone emission amplitude (dB).
            noise_spectrum: 1-D array of ambient noise amplitude (dB).
        """
        self._ax.cla()
        self._ax.semilogx(freq_axis, drone_spectrum, label="Drone Emission")
        self._ax.semilogx(freq_axis, noise_spectrum, label="Ambient Noise")
        self._ax.set_xlabel("Frequency (Hz)")
        self._ax.set_ylabel("Amplitude (dB)")
        self._ax.set_title("Frequency Spectrum")
        self._ax.legend()
        self._fig.tight_layout()
        self.canvas.draw()
