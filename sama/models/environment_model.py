"""
Environment Model

Represents the environmental conditions that affect acoustic propagation:
ambient noise, atmospheric conditions, and detection thresholds.

Implements ISO 9613-1 atmospheric absorption calculation.

Part of the Model layer in the MVC architecture.
"""

import math
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pre-defined ambient noise presets (derived from open datasets)
# ---------------------------------------------------------------------------
NOISE_PRESETS = {
    "quiet_rural": {
        "label": "Quiet Rural",
        "ambient_noise_dba": 30.0,
    },
    "suburban": {
        "label": "Suburban",
        "ambient_noise_dba": 45.0,
    },
    "urban_highway": {
        "label": "Urban Highway",
        "ambient_noise_dba": 70.0,
    },
}


class EnvironmentModel:
    """Data model for environmental / atmospheric parameters."""

    def __init__(self, config: Optional[dict] = None) -> None:
        """Initialise the environment model with optional configuration.

        Args:
            config: Dictionary of environment parameters (from JSON config).
        """
        config = config or {}

        # Ambient noise
        self.ambient_noise_dba: float = config.get("ambient_noise_dba", 45.0)
        self.noise_preset: str = config.get("noise_preset", "suburban")

        # Atmospheric conditions
        self.temperature_c: float = config.get("temperature_c", 20.0)
        self.humidity_pct: float = config.get("humidity_pct", 50.0)
        self.pressure_hpa: float = config.get("pressure_hpa", 1013.25)

        # Detection threshold
        self.required_snr_db: float = config.get("required_snr_db", 10.0)

        logger.info(
            "EnvironmentModel initialised: noise=%.1f dBA, T=%.1f C, "
            "RH=%.0f%%, P=%.1f hPa, SNR_req=%.1f dB",
            self.ambient_noise_dba,
            self.temperature_c,
            self.humidity_pct,
            self.pressure_hpa,
            self.required_snr_db,
        )

    # ------------------------------------------------------------------
    # ISO 9613-1 Atmospheric Absorption
    # ------------------------------------------------------------------

    def atmospheric_absorption_coefficient(self, frequency_hz: float) -> float:
        """Calculate the atmospheric absorption coefficient alpha in dB/m
        according to ISO 9613-1.

        The full standard involves relaxation frequencies of oxygen and
        nitrogen as functions of humidity, temperature, and pressure.

        Args:
            frequency_hz: Sound frequency in Hz.

        Returns:
            float: Absorption coefficient alpha in dB per metre.
        """
        # Reference values
        T_ref = 293.15  # 20 C in Kelvin
        T_01 = 273.16   # Triple point of water (K)
        p_ref = 101.325  # Reference pressure (kPa)

        T_abs = self.temperature_c + 273.15  # Absolute temperature (K)
        p_a = self.pressure_hpa / 10.0       # Atmospheric pressure in kPa
        h = self.humidity_pct                # Relative humidity (%)

        # Molar concentration of water vapour (ISO 9613-1, Eq. 3)
        C = -6.8346 * (T_01 / T_abs) ** 1.261 + 4.6151
        h_molar = h * (10.0 ** C) * (p_ref / p_a)  # %

        # Relaxation frequency of oxygen (Hz)
        fr_O = (p_a / p_ref) * (
            24.0 + 4.04e4 * h_molar * (0.02 + h_molar) / (0.391 + h_molar)
        )

        # Relaxation frequency of nitrogen (Hz)
        fr_N = (p_a / p_ref) * (T_abs / T_ref) ** (-0.5) * (
            9.0 + 280.0 * h_molar * math.exp(
                -4.170 * ((T_abs / T_ref) ** (-1.0 / 3.0) - 1.0)
            )
        )

        f = frequency_hz
        T_ratio = T_abs / T_ref

        # Absorption coefficient (dB/m) -- ISO 9613-1, Eq. 1
        alpha = (
            8.686 * f * f
            * (
                1.84e-11 * (p_ref / p_a) * T_ratio ** 0.5
                + T_ratio ** (-2.5)
                * (
                    0.01275 * math.exp(-2239.1 / T_abs)
                    / (fr_O + f * f / fr_O)
                    + 0.1068 * math.exp(-3352.0 / T_abs)
                    / (fr_N + f * f / fr_N)
                )
            )
        )

        return alpha

    def atmospheric_absorption_spectrum(
        self, freq_axis: np.ndarray
    ) -> np.ndarray:
        """Calculate atmospheric absorption for an array of frequencies.

        Args:
            freq_axis: 1-D array of frequencies in Hz.

        Returns:
            np.ndarray: Array of alpha values (dB/m) aligned to *freq_axis*.
        """
        return np.array(
            [self.atmospheric_absorption_coefficient(f) for f in freq_axis],
            dtype=np.float64,
        )

    # ------------------------------------------------------------------
    # Ambient noise spectrum (simple broadband model)
    # ------------------------------------------------------------------

    def generate_noise_spectrum(
        self, freq_axis: np.ndarray
    ) -> np.ndarray:
        """Generate a simplified ambient noise power spectrum.

        Uses a pink-noise-like roll-off from the broadband ambient level.

        Args:
            freq_axis: 1-D array of frequencies in Hz.

        Returns:
            np.ndarray: Noise amplitude (dB) aligned to *freq_axis*.
        """
        # Pink noise: power proportional to 1/f -> amplitude rolls off
        # approximately -10 log10(f/f0)
        f0 = 100.0  # reference frequency
        spectrum = self.ambient_noise_dba - 10.0 * np.log10(
            np.maximum(freq_axis, 1.0) / f0
        )
        return spectrum

    # ------------------------------------------------------------------
    # Preset helpers
    # ------------------------------------------------------------------

    def apply_preset(self, preset_key: str) -> None:
        """Apply a pre-defined ambient noise preset.

        Args:
            preset_key: One of the keys in NOISE_PRESETS.

        Raises:
            ValueError: If the preset key is not recognised.
        """ 
        if preset_key not in NOISE_PRESETS:
            raise ValueError(
                f"Unknown noise preset '{preset_key}'. "
                f"Available: {list(NOISE_PRESETS.keys())}"
            )
        preset = NOISE_PRESETS[preset_key]
        self.noise_preset = preset_key
        self.ambient_noise_dba = preset["ambient_noise_dba"]
        logger.info(
            "Applied noise preset '%s' (%.0f dBA).",
            preset_key, self.ambient_noise_dba,
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the model state to a plain dictionary.

        Returns:
            dict: JSON-serialisable representation.
        """ 
        return {
            "ambient_noise_dba": self.ambient_noise_dba,
            "noise_preset": self.noise_preset,
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "pressure_hpa": self.pressure_hpa,
            "required_snr_db": self.required_snr_db,
        }  
