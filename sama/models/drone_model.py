"""
Drone (Target) Model

Represents the acoustic emitter -- the drone / UAS whose sound
signature the sensor array is trying to detect.

Part of the Model layer in the MVC architecture.
"""

import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-defined drone acoustic profiles
# ---------------------------------------------------------------------------
DRONE_PRESETS = {
    "dji_mavic_3": {
        "label": "DJI Mavic 3",
        "source_level_dba": 80.0,
        "frequency_peak_hz": 200.0,
        "harmonics": [200, 400, 600, 800, 1000],
        "spectrum_amplitudes_db": [80, 72, 65, 58, 50],
    },
    "heavy_hexacopter": {
        "label": "Heavy-lift Hexacopter",
        "source_level_dba": 90.0,
        "frequency_peak_hz": 150.0,
        "harmonics": [150, 300, 450, 600, 750, 900],
        "spectrum_amplitudes_db": [90, 83, 76, 70, 63, 55],
    },
    "fpv_racer": {
        "label": "FPV Racing Drone",
        "source_level_dba": 95.0,
        "frequency_peak_hz": 300.0,
        "harmonics": [300, 600, 900, 1200],
        "spectrum_amplitudes_db": [95, 86, 78, 68],
    },
}


class DroneModel:
    """Data model for the target UAS acoustic source."""

    def __init__(self, config: Optional[dict] = None) -> None:
        """Initialise the drone model with optional configuration.

        Args:
            config: Dictionary of drone parameters (from JSON config).
        """
        config = config or {}

        # Source level at 1 m reference distance
        self.source_level_dba: float = config.get("source_level_dba", 80.0)

        # Profile preset identifier
        self.profile_preset: str = config.get("profile_preset", "dji_mavic_3")

        # Primary rotor frequency
        self.frequency_peak_hz: float = config.get("frequency_peak_hz", 200.0)

        # Directivity flag (True = omnidirectional)
        self.is_omnidirectional: bool = config.get("is_omnidirectional", True)

        # Harmonic frequencies and their amplitudes
        self.harmonics: List[float] = config.get("harmonics", [200, 400, 600, 800, 1000])
        self.spectrum_amplitudes_db: List[float] = config.get(
            "spectrum_amplitudes_db", [80, 72, 65, 58, 50]
        )

        logger.info(
            "DroneModel initialised: preset='%s', SPL=%.1f dBA, peak=%.0f Hz",
            self.profile_preset,
            self.source_level_dba,
            self.frequency_peak_hz,
        )

    # ------------------------------------------------------------------
    # Directivity helpers
    # ------------------------------------------------------------------

    def directivity_factor(self, elevation_rad: float) -> float:
        """Return a directivity weighting factor for a given elevation angle.

        When the drone is set to omnidirectional the factor is always 1.0.
        When directional, sound is louder directly below (elevation = -pi/2)
        following a simple cosine-squared pattern.

        Args:
            elevation_rad: Elevation angle in radians (0 = horizon,
                           -pi/2 = directly below).

        Returns:
            float: Multiplicative factor (linear scale, 0..1).
        """
        if self.is_omnidirectional:
            return 1.0
        # Directional model: peak directly beneath the drone
        return float(np.cos(elevation_rad + np.pi / 2) ** 2)

    def directivity_factor_db(self, elevation_rad: float) -> float:
        """Directivity factor expressed in dB.

        Args:
            elevation_rad: Elevation angle in radians.

        Returns:
            float: Directivity adjustment in dB (always <= 0).
        """
        factor = self.directivity_factor(elevation_rad)
        if factor <= 0:
            return -100.0  # effectively silent
        return 10.0 * np.log10(factor)

    # ------------------------------------------------------------------
    # Spectrum generation
    # ------------------------------------------------------------------

    def generate_spectrum(
        self, freq_axis: np.ndarray, bandwidth_hz: float = 20.0
    ) -> np.ndarray:
        """Generate a synthetic emission spectrum by placing Gaussian
        peaks at each harmonic frequency.

        Args:
            freq_axis:    1-D array of frequency bins (Hz).
            bandwidth_hz: Width of each harmonic peak (Hz).

        Returns:
            np.ndarray: Spectrum amplitude array (dB) aligned to *freq_axis*.
        """
        spectrum = np.full_like(freq_axis, -120.0, dtype=np.float64)  # floor

        for harmonic_hz, amp_db in zip(self.harmonics, self.spectrum_amplitudes_db):
            peak = amp_db * np.exp(
                -0.5 * ((freq_axis - harmonic_hz) / bandwidth_hz) ** 2
            )
            spectrum = np.maximum(spectrum, peak)

        return spectrum

    # ------------------------------------------------------------------
    # Preset helpers
    # ------------------------------------------------------------------

    def apply_preset(self, preset_key: str) -> None:
        """Apply a pre-defined drone acoustic profile.

        Args:
            preset_key: One of the keys in DRONE_PRESETS.

        Raises:
            ValueError: If the preset key is not recognised.
        """
        if preset_key not in DRONE_PRESETS:
            raise ValueError(
                f"Unknown drone preset '{preset_key}'. "
                f"Available: {list(DRONE_PRESETS.keys())}"
            )
        preset = DRONE_PRESETS[preset_key]
        self.profile_preset = preset_key
        self.source_level_dba = preset["source_level_dba"]
        self.frequency_peak_hz = preset["frequency_peak_hz"]
        self.harmonics = list(preset["harmonics"])
        self.spectrum_amplitudes_db = list(preset["spectrum_amplitudes_db"])
        logger.info("Applied drone preset '%s'.", preset_key)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the model state to a plain dictionary.

        Returns:
            dict: JSON-serialisable representation.
        """
        return {
            "source_level_dba": self.source_level_dba,
            "profile_preset": self.profile_preset,
            "frequency_peak_hz": self.frequency_peak_hz,
            "is_omnidirectional": self.is_omnidirectional,
            "harmonics": self.harmonics,
            "spectrum_amplitudes_db": self.spectrum_amplitudes_db,
        }
