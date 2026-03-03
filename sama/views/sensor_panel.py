"""
Sensor Panel View

Left-sidebar panel that lets the user configure the acoustic sensor
array: microphone specs, array geometry preset, and beamforming
parameters.

Emits signals when any parameter changes so the Controller can
trigger a recalculation.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QDoubleSpinBox, QSpinBox, QComboBox, QFormLayout,
)
from PyQt6.QtCore import pyqtSignal

from sama.models.sensor_model import ARRAY_PRESETS

logger = logging.getLogger(__name__)


class SensorPanel(QWidget):
    """Parameter panel for the acoustic sensor / microphone array."""

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

        # --- Microphone Specifications ---
        mic_group = QGroupBox("Microphone Specifications")
        mic_form = QFormLayout()

        self.sensitivity_spin = QDoubleSpinBox()
        self.sensitivity_spin.setRange(-80.0, 0.0)
        self.sensitivity_spin.setDecimals(1)
        self.sensitivity_spin.setSuffix(" dBV/Pa")
        self.sensitivity_spin.setValue(-26.0)
        self.sensitivity_spin.valueChanged.connect(self._on_change)
        mic_form.addRow("Sensitivity:", self.sensitivity_spin)

        self.noise_floor_spin = QDoubleSpinBox()
        self.noise_floor_spin.setRange(0.0, 60.0)
        self.noise_floor_spin.setDecimals(1)
        self.noise_floor_spin.setSuffix(" dBA")
        self.noise_floor_spin.setValue(14.0)
        self.noise_floor_spin.valueChanged.connect(self._on_change)
        mic_form.addRow("Self-Noise Floor:", self.noise_floor_spin)

        mic_group.setLayout(mic_form)
        layout.addWidget(mic_group)

        # --- Array Geometry ---
        array_group = QGroupBox("Array Geometry")
        array_form = QFormLayout()

        self.preset_combo = QComboBox()
        for key, preset in ARRAY_PRESETS.items():
            self.preset_combo.addItem(preset["label"], key)
        self.preset_combo.setCurrentIndex(1)  # default: 3-mic-triangle
        self.preset_combo.currentIndexChanged.connect(self._on_change)
        array_form.addRow("Array Preset:", self.preset_combo)

        self.num_mics_spin = QSpinBox()
        self.num_mics_spin.setRange(1, 64)
        self.num_mics_spin.setValue(3)
        self.num_mics_spin.setEnabled(False)  # driven by preset
        array_form.addRow("Microphones:", self.num_mics_spin)

        array_group.setLayout(array_form)
        layout.addWidget(array_group)

        # --- Beamforming ---
        beam_group = QGroupBox("Beamforming")
        beam_form = QFormLayout()

        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["DAS (Delay-and-Sum)"])
        self.algorithm_combo.currentIndexChanged.connect(self._on_change)
        beam_form.addRow("Algorithm:", self.algorithm_combo)

        self.target_freq_spin = QDoubleSpinBox()
        self.target_freq_spin.setRange(20.0, 20000.0)
        self.target_freq_spin.setDecimals(0)
        self.target_freq_spin.setSuffix(" Hz")
        self.target_freq_spin.setValue(200.0)
        self.target_freq_spin.valueChanged.connect(self._on_change)
        beam_form.addRow("Target Frequency:", self.target_freq_spin)

        # Read-only computed fields
        self.array_gain_label = QLabel("-- dB")
        beam_form.addRow("Array Gain:", self.array_gain_label)

        beam_group.setLayout(beam_form)
        layout.addWidget(beam_group)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Parameter access
    # ------------------------------------------------------------------

    def get_parameters(self) -> dict:
        """Collect all current parameter values from the panel.

        Returns:
            dict: Parameter dictionary matching SensorModel fields.
        """
        preset_key = self.preset_combo.currentData()
        positions = ARRAY_PRESETS.get(preset_key, ARRAY_PRESETS["3-mic-triangle"]) ["positions"]
        return {
            "sensitivity_dbv_pa": self.sensitivity_spin.value(),
            "noise_floor_dba": self.noise_floor_spin.value(),
            "num_microphones": len(positions),
            "array_preset": preset_key,
            "microphone_positions": [list(p) for p in positions],
            "beamforming_algorithm": "das",
            "target_frequency_hz": self.target_freq_spin.value(),
        }

    def set_parameters(self, params: dict) -> None:
        """Populate the panel from a parameter dictionary.

        Blocks signals to avoid triggering recalculation during load.

        Args:
            params: Dictionary of sensor parameters.
        """
        self.blockSignals(True)
        self.sensitivity_spin.setValue(params.get("sensitivity_dbv_pa", -26.0))
        self.noise_floor_spin.setValue(params.get("noise_floor_dba", 14.0))
        self.target_freq_spin.setValue(params.get("target_frequency_hz", 200.0))

        preset = params.get("array_preset", "3-mic-triangle")
        idx = self.preset_combo.findData(preset)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)

        self.num_mics_spin.setValue(params.get("num_microphones", 3))
        self.blockSignals(False)

    def update_computed_fields(self, array_gain_db: float) -> None:
        """Update read-only display fields.

        Args:
            array_gain_db: Current array gain value.
        """
        self.array_gain_label.setText(f"{array_gain_db:.1f} dB")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_change(self) -> None:
        """Slot called when any parameter widget value changes."""
        # Update the mic count display to match the selected preset
        preset_key = self.preset_combo.currentData()
        if preset_key and preset_key in ARRAY_PRESETS:
            n = len(ARRAY_PRESETS[preset_key]["positions"])
            self.num_mics_spin.setValue(n)
        self.parameters_changed.emit()