"""
Drone Panel View

Left-sidebar panel that lets the user configure the drone / UAS acoustic
source: profile preset, source level, peak frequency, directivity, and
harmonic display.

Emits signals when any parameter changes so the Controller can trigger a
recalculation.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel,
    QDoubleSpinBox, QComboBox, QCheckBox, QFormLayout,
)
from PyQt6.QtCore import pyqtSignal

from sama.models.drone_model import DRONE_PRESETS

logger = logging.getLogger(__name__)


class DronePanel(QWidget):
    """Parameter panel for the drone / UAS acoustic source."""

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

        # --- Drone Profile ---
        profile_group = QGroupBox("Drone Profile")
        profile_form = QFormLayout()

        self.preset_combo = QComboBox()
        for key, preset in DRONE_PRESETS.items():
            self.preset_combo.addItem(preset["label"], key)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_change)
        profile_form.addRow("Preset:", self.preset_combo)

        profile_group.setLayout(profile_form)
        layout.addWidget(profile_group)

        # --- Acoustic Parameters ---
        acoustic_group = QGroupBox("Acoustic Parameters")
        acoustic_form = QFormLayout()

        self.source_level_spin = QDoubleSpinBox()
        self.source_level_spin.setRange(40.0, 130.0)
        self.source_level_spin.setDecimals(1)
        self.source_level_spin.setSuffix(" dBA")
        self.source_level_spin.setValue(80.0)
        self.source_level_spin.valueChanged.connect(self._on_change)
        acoustic_form.addRow("Source Level:", self.source_level_spin)

        self.peak_freq_spin = QDoubleSpinBox()
        self.peak_freq_spin.setRange(20.0, 5000.0)
        self.peak_freq_spin.setDecimals(1)
        self.peak_freq_spin.setSuffix(" Hz")
        self.peak_freq_spin.setValue(200.0)
        self.peak_freq_spin.valueChanged.connect(self._on_change)
        acoustic_form.addRow("Peak Frequency:", self.peak_freq_spin)

        self.omnidirectional_check = QCheckBox()
        self.omnidirectional_check.setChecked(True)
        self.omnidirectional_check.stateChanged.connect(self._on_change)
        acoustic_form.addRow("Omnidirectional:", self.omnidirectional_check)

        acoustic_group.setLayout(acoustic_form)
        layout.addWidget(acoustic_group)

        # --- Harmonics Display ---
        harmonics_group = QGroupBox("Harmonic Frequencies")
        harmonics_form = QFormLayout()

        self.harmonics_label = QLabel("--")
        self.harmonics_label.setWordWrap(True)
        harmonics_form.addRow("Harmonics:", self.harmonics_label)

        harmonics_group.setLayout(harmonics_form)
        layout.addWidget(harmonics_group)

        layout.addStretch()

        # Populate harmonics label from default preset
        self._update_harmonics_label()

    # ------------------------------------------------------------------
    # Parameter access
    # ------------------------------------------------------------------

    def get_parameters(self) -> dict:
        """Collect all current parameter values from the panel.

        Returns:
            dict: Parameter dictionary matching DroneModel fields.
        """
        preset_key = self.preset_combo.currentData()
        preset_data = DRONE_PRESETS.get(preset_key, {})
        return {
            "source_level_dba": self.source_level_spin.value(),
            "profile_preset": preset_key,
            "frequency_peak_hz": self.peak_freq_spin.value(),
            "is_omnidirectional": self.omnidirectional_check.isChecked(),
            "harmonics": list(preset_data.get("harmonics", [])),
            "spectrum_amplitudes_db": list(
                preset_data.get("spectrum_amplitudes_db", [])
            ),
        }

    def set_parameters(self, params: dict) -> None:
        """Populate the panel from a parameter dictionary.

        Blocks signals to avoid triggering recalculation during load.

        Args:
            params: Dictionary of drone parameters.
        """
        self.blockSignals(True)
        self.source_level_spin.setValue(params.get("source_level_dba", 80.0))
        self.peak_freq_spin.setValue(params.get("frequency_peak_hz", 200.0))
        self.omnidirectional_check.setChecked(
            params.get("is_omnidirectional", True)
        )
        preset = params.get("profile_preset", "dji_mavic_3")
        idx = self.preset_combo.findData(preset)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.blockSignals(False)
        self._update_harmonics_label()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_preset_change(self) -> None:
        """Slot called when the preset combo changes."""
        preset_key = self.preset_combo.currentData()
        if preset_key and preset_key in DRONE_PRESETS:
            preset = DRONE_PRESETS[preset_key]
            self.source_level_spin.blockSignals(True)
            self.peak_freq_spin.blockSignals(True)
            self.source_level_spin.setValue(preset["source_level_dba"])
            self.peak_freq_spin.setValue(preset["frequency_peak_hz"])
            self.source_level_spin.blockSignals(False)
            self.peak_freq_spin.blockSignals(False)
            self._update_harmonics_label()
        self.parameters_changed.emit()

    def _on_change(self) -> None:
        """Slot called when any non-preset parameter widget value changes."""
        self.parameters_changed.emit()

    def _update_harmonics_label(self) -> None:
        """Refresh the read-only harmonics display from the current preset."""
        preset_key = self.preset_combo.currentData()
        preset = DRONE_PRESETS.get(preset_key, {})
        harmonics = preset.get("harmonics", [])
        if harmonics:
            text = ", ".join(f"{h} Hz" for h in harmonics)
        else:
            text = "--"
        self.harmonics_label.setText(text)
