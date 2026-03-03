"""
Acoustic Engine

The mathematical core of SAMA.  Combines the Sensor, Drone, and
Environment models to compute:

  - Transmission Loss (TL) = 20 log10(r) + alpha * r
  - Array Gain (AG)
  - Received SNR = SPL_drone - TL - Noise_ambient + AG
  - 3-D detection boundary where SNR = SNR_required

All heavy numerical work lives here so the GUI remains responsive.

Part of the Model layer in the MVC architecture.
"""

import logging
from typing import Tuple

import numpy as np
from scipy.optimize import brentq

from sama.models.sensor_model import SensorModel
from sama.models.drone_model import DroneModel
from sama.models.environment_model import EnvironmentModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MIN_DISTANCE_M = 0.1   # avoid log10(0)
_MAX_DISTANCE_M = 5000.0 # upper search bound for detection range


class AcousticEngine:
    """Core physics engine that computes detection metrics."""

    def __init__(self,
        sensor: SensorModel,
        drone: DroneModel,
        environment: EnvironmentModel,
    ) -> None:
        """Initialise the engine with references to all three models.

        Args:
            sensor:      SensorModel instance.
            drone:       DroneModel instance.
            environment: EnvironmentModel instance.
        """
        self.sensor = sensor
        self.drone = drone
        self.environment = environment

        # Cached results (populated by recalculate)
        self.snr_vs_distance: Tuple[np.ndarray, np.ndarray] = (
            np.array([]), np.array([])
        )
        self.detection_boundary_3d: Tuple[
            np.ndarray, np.ndarray, np.ndarray
        ] = (np.array([]), np.array([]), np.array([]))
        self.beam_pattern: Tuple[np.ndarray, np.ndarray] = (
            np.array([]), np.array([])
        )
        self.freq_axis: np.ndarray = np.array([])
        self.drone_spectrum: np.ndarray = np.array([])
        self.noise_spectrum: np.ndarray = np.array([])

        logger.info("AcousticEngine initialised.")

    # ------------------------------------------------------------------
    # Core equations
    # ------------------------------------------------------------------

    def transmission_loss(self, distance_m: float, alpha_db_m: float) -> float:
        """Compute total transmission loss at a given distance.

        TL = 20 * log10(r) + alpha * r

        Args:
            distance_m:  Distance from source in metres.
            alpha_db_m:  Atmospheric absorption coefficient (dB/m).

        Returns:
            float: Transmission loss in dB.
        """
        r = max(distance_m, _MIN_DISTANCE_M)
        return 20.0 * np.log10(r) + alpha_db_m * r

    def snr_at_distance(
        self,
        distance_m: float,
        theta: float = 0.0,
        phi: float = 0.0,
    ) -> float:
        """Compute the received SNR at a given distance and direction.

        SNR = SPL_drone + DI_drone - TL - Noise_ambient + AG

        Args:
            distance_m: Distance from sensor to drone (m).
            theta:      Azimuth angle (rad).
            phi:        Elevation angle (rad).

        Returns:
            float: Signal-to-Noise Ratio in dB.
        """
        alpha = self.environment.atmospheric_absorption_coefficient(
            self.drone.frequency_peak_hz
        )
        tl = self.transmission_loss(distance_m, alpha)
        drone_di = self.drone.directivity_factor_db(phi)
        ag = self.sensor.array_gain_db

        snr = (
            self.drone.source_level_dba
            + drone_di
            - tl
            - self.environment.ambient_noise_dba
            + ag
        )
        return snr

    # ------------------------------------------------------------------
    # Detection range solver
    # ------------------------------------------------------------------

    def _snr_residual(self, r: float, theta: float, phi: float) -> float:
        """Residual function for root-finding: SNR(r) - SNR_required.

        Args:
            r:     Distance in metres.
            theta: Azimuth angle (rad).
            phi:   Elevation angle (rad).

        Returns:
            float: Residual value (zero at the detection boundary).
        """
        return self.snr_at_distance(r, theta, phi) - self.environment.required_snr_db

    def detection_range(self, theta: float = 0.0, phi: float = 0.0) -> float:
        """Find the maximum detection distance in a given direction.

        Uses Brent's method to solve SNR(r) = SNR_required.

        Args:
            theta: Azimuth angle (rad).
            phi:   Elevation angle (rad).

        Returns:
            float: Detection range in metres (0 if no detection possible).
        """
        # Check if detection is possible at the closest distance
        snr_close = self._snr_residual(_MIN_DISTANCE_M, theta, phi)
        if snr_close < 0:
            return 0.0  # Cannot detect even at closest range

        # Check if the SNR is still above threshold at the maximum distance
        snr_far = self._snr_residual(_MAX_DISTANCE_M, theta, phi)
        if snr_far >= 0:
            return _MAX_DISTANCE_M  # Detectable beyond our search bound

        # Root-find the exact crossing
        try:
            r_boundary = brentq(
                self._snr_residual,
                _MIN_DISTANCE_M,
                _MAX_DISTANCE_M,
                args=(theta, phi),
                xtol=0.1,
            )
            return r_boundary
        except ValueError:
            logger.warning(
                "Root-finding failed for theta=%.2f, phi=%.2f", theta, phi
            )
            return 0.0

    # ------------------------------------------------------------------
    # Bulk recalculation (called by controller on parameter change)
    # ------------------------------------------------------------------

    def recalculate(self) -> None:
        """Recompute all cached results.

        This is the single entry point the Controller calls whenever
        any parameter changes.  It populates every cached array so the
        View can simply read the latest data.
        """
        logger.info("AcousticEngine: full recalculation started.")

        # ---- Plot B: SNR vs Distance ----
        distances = np.linspace(1.0, 2000.0, 500)
        snr_values = np.array(
            [self.snr_at_distance(d) for d in distances], dtype=np.float64
        )
        self.snr_vs_distance = (distances, snr_values)

        # ---- Plot A: 3-D Detection Volume ----
        n_theta = 72   # azimuth resolution (5-degree steps)
        n_phi = 37     # elevation resolution (5-degree steps)
        theta_vals = np.linspace(0, 2 * np.pi, n_theta)
        phi_vals = np.linspace(-np.pi / 2, np.pi / 2, n_phi)

        x_boundary = np.zeros((n_phi, n_theta))
        y_boundary = np.zeros((n_phi, n_theta))
        z_boundary = np.zeros((n_phi, n_theta))

        for i, phi in enumerate(phi_vals):
            for j, theta in enumerate(theta_vals):
                r = self.detection_range(theta, phi)
                x_boundary[i, j] = r * np.cos(phi) * np.cos(theta)
                y_boundary[i, j] = r * np.cos(phi) * np.sin(theta)
                z_boundary[i, j] = r * np.sin(phi)

        self.detection_boundary_3d = (x_boundary, y_boundary, z_boundary)

        # ---- Plot C: Beam Pattern ----
        theta_beam = np.linspace(0, 2 * np.pi, 360)
        pattern = self.sensor.compute_beam_pattern(theta_beam)
        self.beam_pattern = (theta_beam, pattern)

        # ---- Plot D: Frequency Spectrum ----
        self.freq_axis = np.logspace(
            np.log10(20), np.log10(20000), 500
        )
        self.drone_spectrum = self.drone.generate_spectrum(self.freq_axis)
        self.noise_spectrum = self.environment.generate_noise_spectrum(
            self.freq_axis
        )

        logger.info("AcousticEngine: recalculation complete.")

    # ------------------------------------------------------------------
    # Data export helpers
    # ------------------------------------------------------------------

    def get_detection_boundary_csv_rows(self) -> list:
        """Return the 3-D detection boundary as a list of CSV rows.

        Each row is a dict with keys: theta_deg, phi_deg, range_m, x, y, z.

        Returns:
            list[dict]: One dict per (theta, phi) sample.
        """
        x, y, z = self.detection_boundary_3d
        n_phi, n_theta = x.shape
        theta_vals = np.linspace(0, 360, n_theta)
        phi_vals = np.linspace(-90, 90, n_phi)

        rows = []
        for i in range(n_phi):
            for j in range(n_theta):
                r = np.sqrt(
                    x[i, j] ** 2 + y[i, j] ** 2 + z[i, j] ** 2
                )
                rows.append({
                    "theta_deg": round(theta_vals[j], 2),
                    "phi_deg": round(phi_vals[i], 2),
                    "range_m": round(r, 2),
                    "x": round(x[i, j], 2),
                    "y": round(y[i, j], 2),
                    "z": round(z[i, j], 2),
                })
        return rows
