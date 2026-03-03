"""
Environment Panel View

Left-sidebar panel that lets the user configure the environmental
conditions: ambient noise preset, temperature, humidity, pressure, and
required SNR threshold.

Emits signals when any parameter changes so the Controller can trigger a
recalculation.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox,
    QDoubleSpinBox, QComboBox, QFormLayout,
)
from PyQt6.QtCore import pyqtSignal

from sama.models.environment_model import NOISE_PRESETS

logger = logging.getLogger(__name__)


class EnvironmentPanel(QWidget):
    """Parameter panel for the acoustic environment."""

    # Signal emitted whenever any parameter is changed by the user
    parameters_changed = pyqtSignal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # --- Ambient Noise ---
        noise_group = QGroupBox("Ambient Noise")
        noise_form = QFormLayout()

        self.preset_combo = QComboBox()
        for key, preset in NOISE_PRESETS.items():
            self.preset_combo.addItem(preset["label"], key)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_change)
        noise_form.addRow("Preset:", self.preset_combo)

        self.ambient_noise_spin = QDoubleSpinBox()
        self.ambient_noise_spin.setRange(10.0, 100.0)
        self.ambient_noise_spin.setDecimals(1)
        self.ambient_noise_spin.setSuffix(" dBA")
        self.ambient_noise_spin.setValue(45.0)
        self.ambient_noise_spin.valueChanged.connect(self._on_change)
        noise_form.addRow("Ambient Level:", self.ambient_noise_spin)

        noise_group.setLayout(noise_form)
        layout.addWidget(noise_group)

        # --- Atmospheric Conditions ---
        atmos_group = QGroupBox("Atmospheric Conditions")
        atmos_form = QFormLayout()

        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(-40.0, 50.0)
        self.temperature_spin.setDecimals(1)
        self.temperature_spin.setSuffix(" °C")
        self.temperature_spin.setValue(20.0)
        self.temperature_spin.valueChanged.connect(self._on_change)
        atmos_form.addRow("Temperature:", self.temperature_spin)

        self.humidity_spin = QDoubleSpinBox()
        self.humidity_spin.setRange(0.0, 100.0)
        self.humidity_spin.setDecimals(1)
        self.humidity_spin.setSuffix(" %")
        self.humidity_spin.setValue(50.0)
        self.humidity_spin.valueChanged.connect(self._on_change)
        atmos_form.addRow("Humidity:", self.humidity_spin)

        self.pressure_spin = QDoubleSpinBox()
        self.pressure_spin.setRange(800.0, 1100.0)
        self.pressure_spin.setDecimals(2)
        self.pressure_spin.setSuffix(" hPa")
        self.pressure_spin.setValue(1013.25)
        self.pressure_spin.valueChanged.connect(self._on_change)
        atmos_form.addRow("Pressure:", self.pressure_spin)

        atmos_group.setLayout(atmos_form)
        layout.addWidget(atmos_group)

        # --- Detection Threshold ---
        detect_group = QGroupBox("Detection Threshold")
        detect_form = QFormLayout()

        self.required_snr_spin = QDoubleSpinBox()
        self.required_snr_spin.setRange(0.0, 30.0)
        self.required_snr_spin.setDecimals(1)
        self.required_snr_spin.setSuffix(" dB")
        self.required_snr_spin.setValue(10.0)
        self.required_snr_spin.valueChanged.connect(self._on_change)
        detect_form.addRow("Required SNR:", self.required_snr_spin)

        detect_group.setLayout(detect_form)
        layout.addWidget(detect_group)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Parameter access
    # ------------------------------------------------------------------

    def get_parameters(self) -> dict:
        """Collect all current parameter values from the panel.

        Returns:
            dict: Parameter dictionary matching EnvironmentModel fields.
        """
        return {
            "ambient_noise_dba": self.ambient_noise_spin.value(),
            "noise_preset": self.preset_combo.currentData(),
            "temperature_c": self.temperature_spin.value(),
            "humidity_pct": self.humidity_spin.value(),
            "pressure_hpa": self.pressure_spin.value(),
            "required_snr_db": self.required_snr_spin.value(),
        }

    def set_parameters(self, params: dict) -> None:
        """Populate the panel from a parameter dictionary.

        Blocks signals to avoid triggering recalculation during load.

        Args:
            params: Dictionary of environment parameters.
        """
        self.blockSignals(True)
        self.ambient_noise_spin.setValue(params.get("ambient_noise_dba", 45.0))
        self.temperature_spin.setValue(params.get("temperature_c", 20.0))
        self.humidity_spin.setValue(params.get("humidity_pct", 50.0))
        self.pressure_spin.setValue(params.get("pressure_hpa", 1013.25))
        self.required_snr_spin.setValue(params.get("required_snr_db", 10.0))
        preset = params.get("noise_preset", "suburban")
        idx = self.preset_combo.findData(preset)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.blockSignals(False)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_preset_change(self) -> None:
        """Slot called when the noise preset combo changes."""
        preset_key = self.preset_combo.currentData()
        if preset_key and preset_key in NOISE_PRESETS:
            preset = NOISE_PRESETS[preset_key]
            self.ambient_noise_spin.blockSignals(True)
            self.ambient_noise_spin.setValue(preset["ambient_noise_dba"])
            self.ambient_noise_spin.blockSignals(False)
        self.parameters_changed.emit()

    def _on_change(self) -> None:
        """Slot called when any non-preset parameter widget value changes."""
        self.parameters_changed.emit()
