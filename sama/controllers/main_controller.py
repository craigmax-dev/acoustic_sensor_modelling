"""
Main Controller

Wires together the View and Model layers of SAMA.  Connects panel
signals to recalculation logic, handles menu actions, and keeps the
status bar up to date.

Part of the Controller layer in the MVC architecture.
"""

import csv
import json
import logging

import numpy as np
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from sama.views.main_window import MainWindow
from sama.views.toast_notification import show_toast
from sama.models.sensor_model import SensorModel
from sama.models.drone_model import DroneModel
from sama.models.environment_model import EnvironmentModel
from sama.models.acoustic_engine import AcousticEngine

logger = logging.getLogger(__name__)


class MainController:
    """Controller that coordinates the SAMA MVC components."""

    def __init__(
        self,
        main_window: MainWindow,
        sensor_model: SensorModel,
        drone_model: DroneModel,
        environment_model: EnvironmentModel,
        acoustic_engine: AcousticEngine,
    ) -> None:
        """Initialise the controller and connect all signals.

        Args:
            main_window:       The main application window (View).
            sensor_model:      Sensor / microphone array model.
            drone_model:       Drone acoustic source model.
            environment_model: Environmental conditions model.
            acoustic_engine:   Core physics / computation engine.
        """
        self._window = main_window
        self._sensor = sensor_model
        self._drone = drone_model
        self._env = environment_model
        self._engine = acoustic_engine

        self._connect_signals()
        logger.info("MainController initialised.")

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """Connect panel and menu signals to controller slots."""
        win = self._window

        # Parameter panels
        win.sensor_panel.parameters_changed.connect(self.recalculate)
        win.drone_panel.parameters_changed.connect(self.recalculate)
        win.environment_panel.parameters_changed.connect(self.recalculate)

        # Menu actions
        win.action_save.triggered.connect(self._on_save_config)
        win.action_load.triggered.connect(self._on_load_config)
        win.action_export_csv.triggered.connect(self._on_export_csv)
        win.action_about.triggered.connect(self._on_about)

    # ------------------------------------------------------------------
    # Recalculation
    # ------------------------------------------------------------------

    def recalculate(self) -> None:
        """Read panel parameters, update models, recompute, refresh plots."""
        try:
            # 1. Read parameters from each panel
            sensor_params = self._window.sensor_panel.get_parameters()
            drone_params = self._window.drone_panel.get_parameters()
            env_params = self._window.environment_panel.get_parameters()

            # 2. Update model attributes
            for key, value in sensor_params.items():
                setattr(self._sensor, key, value)
            for key, value in drone_params.items():
                setattr(self._drone, key, value)
            for key, value in env_params.items():
                setattr(self._env, key, value)

            # 3. Run acoustic engine
            self._engine.recalculate()

            # 4. Update plot widgets with cached engine results
            x, y, z = self._engine.detection_boundary_3d
            self._window.detection_volume_plot.update_plot(x, y, z)

            distances, snr_values = self._engine.snr_vs_distance
            self._window.snr_distance_plot.update_plot(
                distances, snr_values, self._env.required_snr_db
            )

            theta, pattern = self._engine.beam_pattern
            self._window.polar_directivity_plot.update_plot(theta, pattern)

            self._window.spectrum_plot.update_plot(
                self._engine.freq_axis,
                self._engine.drone_spectrum,
                self._engine.noise_spectrum,
            )

            # 5. Update sensor panel computed fields
            self._window.sensor_panel.update_computed_fields(
                self._sensor.array_gain_db
            )

            # 6. Update status bar
            # Estimate detection range as the maximum radial distance on the
            # horizontal plane (phi = 0, midpoint elevation index)
            x_arr, y_arr, z_arr = self._engine.detection_boundary_3d
            if x_arr.size > 0:
                mid_phi = x_arr.shape[0] // 2
                ranges = np.sqrt(
                    x_arr[mid_phi] ** 2 + y_arr[mid_phi] ** 2 + z_arr[mid_phi] ** 2
                )
                max_range = float(ranges.max())
                self._window.status_bar.showMessage(
                    f"Max detection range: {max_range:.0f} m"
                )
            else:
                self._window.status_bar.showMessage("Recalculation complete.")

        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Recalculation error: %s", exc)
            show_toast(self._window, f"Calculation error: {exc}", severity="error")

    # ------------------------------------------------------------------
    # Menu action handlers
    # ------------------------------------------------------------------

    def _on_save_config(self) -> None:
        """Save the current model state to a JSON file."""
        path, _ = QFileDialog.getSaveFileName(
            self._window,
            "Save Configuration",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            config = {
                "sensor": self._sensor.to_dict(),
                "drone": self._drone.to_dict(),
                "environment": self._env.to_dict(),
            }
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(config, fh, indent=4)
            show_toast(self._window, "Configuration saved.", severity="success")
            logger.info("Configuration saved to %s", path)
        except OSError as exc:
            show_toast(self._window, f"Save failed: {exc}", severity="error")
            logger.error("Failed to save config: %s", exc)

    def _on_load_config(self) -> None:
        """Load model state from a JSON file and refresh the UI."""
        path, _ = QFileDialog.getOpenFileName(
            self._window,
            "Load Configuration",
            "",
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                config = json.load(fh)

            sensor_cfg = config.get("sensor", {})
            drone_cfg = config.get("drone", {})
            env_cfg = config.get("environment", {})

            # Update models
            for key, value in sensor_cfg.items():
                setattr(self._sensor, key, value)
            for key, value in drone_cfg.items():
                setattr(self._drone, key, value)
            for key, value in env_cfg.items():
                setattr(self._env, key, value)

            # Update panels (without triggering recalculate for each)
            self._window.sensor_panel.set_parameters(sensor_cfg)
            self._window.drone_panel.set_parameters(drone_cfg)
            self._window.environment_panel.set_parameters(env_cfg)

            self.recalculate()
            show_toast(self._window, "Configuration loaded.", severity="success")
            logger.info("Configuration loaded from %s", path)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            show_toast(self._window, f"Load failed: {exc}", severity="error")
            logger.error("Failed to load config: %s", exc)

    def _on_export_csv(self) -> None:
        """Export the detection boundary data as a CSV file."""
        path, _ = QFileDialog.getSaveFileName(
            self._window,
            "Export Detection Boundary CSV",
            "",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return
        try:
            rows = self._engine.get_detection_boundary_csv_rows()
            if not rows:
                show_toast(
                    self._window,
                    "No data to export. Run a calculation first.",
                    severity="warning",
                )
                return
            fieldnames = list(rows[0].keys())
            with open(path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            show_toast(self._window, "CSV exported.", severity="success")
            logger.info("Detection boundary exported to %s", path)
        except OSError as exc:
            show_toast(self._window, f"Export failed: {exc}", severity="error")
            logger.error("Failed to export CSV: %s", exc)

    def _on_about(self) -> None:
        """Show an about dialog."""
        QMessageBox.about(
            self._window,
            "About SAMA",
            "<b>SAMA – Sonidome Acoustic Modelling Application</b><br>"
            "Version 1.0.0<br><br>"
            "A physics-based acoustic sensor modelling tool for UAS detection.<br>"
            "Built with PyQt6 and Matplotlib.",
        )
