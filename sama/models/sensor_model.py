"""
Sensor Model

Represents the acoustic sensor array configuration including microphone
specifications, array geometry, and beamforming parameters.

Part of the Model layer in the MVC architecture.
"""

import math
import logging
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-defined array geometry presets
# ---------------------------------------------------------------------------
ARRAY_PRESETS = {
    "single": {
        "label": "Single Microphone",
        "positions": [[0.0, 0.0, 0.0]],
    },
    "3-mic-triangle": {
        "label": "3-Mic Triangle (MVP)",
        "positions": [
            [0.0, 0.0, 0.0],
            [0.1, 0.0, 0.0],
            [0.05, 0.087, 0.0],
        ],
    },
    "uca-6": {
        "label": "Uniform Circular Array (6 mics)",
        "positions": [
            [0.1 * math.cos(2 * math.pi * i / 6),
             0.1 * math.sin(2 * math.pi * i / 6),
             0.0]
            for i in range(6)
        ],
    },
    "linear-4": {
        "label": "Linear Array (4 mics)",
        "positions": [
            [-0.15, 0.0, 0.0],
            [-0.05, 0.0, 0.0],
            [0.05, 0.0, 0.0],
            [0.15, 0.0, 0.0],
        ],
    },
}


class SensorModel:
    """Data model for the acoustic sensor / microphone array."""

    def __init__(self, config: Optional[dict] = None) -> None:
        """Initialise the sensor model with optional configuration.

        Args:
            config: Dictionary of sensor parameters (from JSON config).
        """
        config = config or {}

        # Microphone specifications
        self.sensitivity_dbv_pa: float = config.get("sensitivity_dbv_pa", -26.0)
        self.noise_floor_dba: float = config.get("noise_floor_dba", 14.0)
        self.frequency_response: str = config.get("frequency_response", "flat")

        # Array geometry
        self.num_microphones: int = config.get("num_microphones", 3)
        self.array_preset: str = config.get("array_preset", "3-mic-triangle")
        self.microphone_positions: List[List[float]] = config.get(
            "microphone_positions",
            ARRAY_PRESETS["3-mic-triangle"]["positions"],
        )

        # Beamforming parameters
        self.beamforming_algorithm: str = config.get("beamforming_algorithm", "das")
        self.target_frequency_hz: float = config.get("target_frequency_hz", 200.0)

        logger.info(
            "SensorModel initialised: %d mic(s), preset='%s', algorithm='%s'",
            self.num_microphones,
            self.array_preset,
            self.beamforming_algorithm,
        )

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def array_gain_db(self) -> float:
        """Theoretical array gain for an ideal DAS beamformer.

        AG = 10 * log10(N)

        Returns:
            float: Array gain in dB.
        """
        if self.num_microphones <= 0:
            return 0.0
        return 10.0 * math.log10(self.num_microphones)

    @property
    def directivity_index(self) -> float:
        """Directivity index (DI) -- equivalent to array gain for
        spatially uncorrelated noise.

        Returns:
            float: Directivity index in dB.
        """
        return self.array_gain_db

    @property
    def positions_array(self) -> np.ndarray:
        """Return microphone positions as a NumPy array of shape (N, 3).

        Returns:
            np.ndarray: Microphone coordinates.
        """
        return np.array(self.microphone_positions, dtype=np.float64)

    # ------------------------------------------------------------------
    # Preset helpers
    # ------------------------------------------------------------------

    def apply_preset(self, preset_key: str) -> None:
        """Apply a pre-defined array geometry preset.

        Args:
            preset_key: One of the keys in ARRAY_PRESETS.

        Raises:
            ValueError: If the preset key is not recognised.
        """
        if preset_key not in ARRAY_PRESETS:
            raise ValueError(
                f"Unknown array preset '{preset_key}'. "
                f"Available: {list(ARRAY_PRESETS.keys())}"
            )
        preset = ARRAY_PRESETS[preset_key]
        self.array_preset = preset_key
        self.microphone_positions = [list(p) for p in preset["positions"]]
        self.num_microphones = len(self.microphone_positions)
        logger.info("Applied array preset '%s' (%d mics).", preset_key, self.num_microphones)

    # ------------------------------------------------------------------
    # Beamforming computation
    # ------------------------------------------------------------------

    def compute_steering_vector(
        self, theta: float, phi: float, frequency_hz: float, speed_of_sound: float = 343.0
    ) -> np.ndarray:
        """Compute the steering vector for a plane wave arriving from
        direction (theta, phi).

        Args:
            theta: Azimuth angle in radians.
            phi:   Elevation angle in radians.
            frequency_hz: Signal frequency in Hz.
            speed_of_sound: Speed of sound in m/s.

        Returns:
            np.ndarray: Complex steering vector of length N.
        """
        wavelength = speed_of_sound / frequency_hz
        k = 2.0 * np.pi / wavelength  # wave number

        # Unit direction vector
        d = np.array([
            np.cos(phi) * np.cos(theta),
            np.cos(phi) * np.sin(theta),
            np.sin(phi),
        ])

        positions = self.positions_array  # (N, 3)
        delays = positions @ d  # dot product for each mic
        steering = np.exp(1j * k * delays)
        return steering

    def compute_beam_pattern(
        self,
        theta_range: np.ndarray,
        frequency_hz: Optional[float] = None,
        phi: float = 0.0,
        speed_of_sound: float = 343.0,
    ) -> np.ndarray:
        """Compute the normalised beam pattern (power) across azimuth angles.

        Used to render the polar directivity plot.

        Args:
            theta_range:    1-D array of azimuth angles in radians.
            frequency_hz:   Signal frequency (defaults to target_frequency_hz).
            phi:            Elevation angle in radians (default 0 -- horizontal).
            speed_of_sound: Speed of sound in m/s.

        Returns:
            np.ndarray: Normalised power pattern (linear) same length as
                        *theta_range*.
        """
        if frequency_hz is None:
            frequency_hz = self.target_frequency_hz

        n_mics = self.num_microphones
        pattern = np.zeros(len(theta_range), dtype=np.float64)

        for idx, theta in enumerate(theta_range):
            sv = self.compute_steering_vector(theta, phi, frequency_hz, speed_of_sound)
            # DAS weights: uniform
            weights = np.ones(n_mics, dtype=np.complex128) / n_mics
            response = np.abs(np.dot(weights.conj(), sv)) ** 2
            pattern[idx] = response

        # Normalise to peak
        peak = pattern.max()
        if peak > 0:
            pattern /= peak

        return pattern

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the model state to a plain dictionary.

        Returns:
            dict: JSON-serialisable representation.
        """
        return {
            "sensitivity_dbv_pa": self.sensitivity_dbv_pa,
            "noise_floor_dba": self.noise_floor_dba,
            "frequency_response": self.frequency_response,
            "num_microphones": self.num_microphones,
            "array_preset": self.array_preset,
            "microphone_positions": self.microphone_positions,
            "beamforming_algorithm": self.beamforming_algorithm,
            "target_frequency_hz": self.target_frequency_hz,
        }