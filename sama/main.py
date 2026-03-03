"""
SAMA Application Entry Point

Initialises the PyQt6 application, wires up the MVC architecture,
and launches the main window.
"""

import sys
import os
import json
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from sama.controllers.main_controller import MainController
from sama.views.main_window import MainWindow
from sama.models.sensor_model import SensorModel
from sama.models.drone_model import DroneModel
from sama.models.environment_model import EnvironmentModel
from sama.models.acoustic_engine import AcousticEngine

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

def load_default_config() -> dict:
    """Load the default configuration from the bundled JSON file.

    Returns:
        dict: Parsed configuration dictionary.
    """
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "default_config.json")
    config_path = os.path.normpath(config_path)
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            config = json.load(fh)
            logger.info("Default configuration loaded from %s", config_path)
            return config
    except FileNotFoundError:
        logger.warning("Default config not found at %s – using built-in defaults.", config_path)
        return {}
    except json.JSONDecodeError as exc:
        logger.error("Malformed JSON in config file: %s", exc)
        return {}

def main() -> None:
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("SAMA – Sonidome Acoustic Modelling Application")
    app.setOrganizationName("Sonidome")
    app.setApplicationVersion("1.0.0")

    # Load default configuration
    config = load_default_config()

    # Instantiate MVC components (Model layer)
    sensor_model = SensorModel(config.get("sensor", {}))
    drone_model = DroneModel(config.get("drone", {}))
    environment_model = EnvironmentModel(config.get("environment", {}))
    acoustic_engine = AcousticEngine(sensor_model, drone_model, environment_model)

    # Instantiate the View (main window)
    main_window = MainWindow()

    # Instantiate the Controller – wires models ↔ views
    controller = MainController(
        main_window=main_window,
        sensor_model=sensor_model,
        drone_model=drone_model,
        environment_model=environment_model,
        acoustic_engine=acoustic_engine,
    )

    # Initial calculation & render
    controller.recalculate()

    main_window.show()
    logger.info("SAMA application started.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
