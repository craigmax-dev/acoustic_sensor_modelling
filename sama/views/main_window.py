"""
Main Window View

Assembles the full SAMA application window: left sidebar with parameter
tabs, right 2×2 plot grid, menu bar, and status bar.

Part of the View layer in the MVC architecture.
"""

import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTabWidget, QStatusBar, QMenuBar,
    QGridLayout,
)
from PyQt6.QtGui import QAction

from sama.views.sensor_panel import SensorPanel
from sama.views.drone_panel import DronePanel
from sama.views.environment_panel import EnvironmentPanel
from sama.views.plot_widgets import (
    DetectionVolumePlot,
    SnrDistancePlot,
    PolarDirectivityPlot,
    SpectrumPlot,
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for SAMA."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SAMA – Sonidome Acoustic Modelling Application")
        self.setMinimumSize(1400, 900)
        self._build_menu()
        self._build_central()
        self._build_status_bar()
        logger.info("MainWindow constructed.")

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        menu_bar: QMenuBar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("File")

        self.action_save = QAction("Save Config", self)
        file_menu.addAction(self.action_save)

        self.action_load = QAction("Load Config", self)
        file_menu.addAction(self.action_load)

        self.action_export_csv = QAction("Export CSV", self)
        file_menu.addAction(self.action_export_csv)

        file_menu.addSeparator()

        self.action_exit = QAction("Exit", self)
        self.action_exit.triggered.connect(self.close)
        file_menu.addAction(self.action_exit)

        # Help menu
        help_menu = menu_bar.addMenu("Help")

        self.action_about = QAction("About", self)
        help_menu.addAction(self.action_about)

    # ------------------------------------------------------------------
    # Central widget
    # ------------------------------------------------------------------

    def _build_central(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(4, 4, 4, 4)
        root_layout.setSpacing(4)

        # --- Left sidebar ---
        sidebar = QWidget()
        sidebar.setFixedWidth(320)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()

        self.sensor_panel = SensorPanel()
        self.drone_panel = DronePanel()
        self.environment_panel = EnvironmentPanel()

        self.tab_widget.addTab(self.sensor_panel, "Sensor")
        self.tab_widget.addTab(self.drone_panel, "Drone")
        self.tab_widget.addTab(self.environment_panel, "Environment")

        sidebar_layout.addWidget(self.tab_widget)
        root_layout.addWidget(sidebar)

        # --- Right plot area (2×2 grid) ---
        plot_area = QWidget()
        plot_layout = QGridLayout(plot_area)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(4)

        self.detection_volume_plot = DetectionVolumePlot()
        self.snr_distance_plot = SnrDistancePlot()
        self.polar_directivity_plot = PolarDirectivityPlot()
        self.spectrum_plot = SpectrumPlot()

        plot_layout.addWidget(self.detection_volume_plot, 0, 0)
        plot_layout.addWidget(self.snr_distance_plot, 0, 1)
        plot_layout.addWidget(self.polar_directivity_plot, 1, 0)
        plot_layout.addWidget(self.spectrum_plot, 1, 1)

        root_layout.addWidget(plot_area, stretch=1)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.")
