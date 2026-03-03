"""
Toast Notification Widget

Provides user-facing toast notifications for errors, warnings, and
informational messages.  Toasts fade in at the top-right corner of
the parent window and automatically dismiss after a timeout.

Used throughout the application to handle API / file-system errors
gracefully.
"""

import logging

from PyQt6.QtWidgets import QLabel, QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import QTimer, QPropertyAnimation, Qt, QEasingCurve
from PyQt6.QtGui import QFont

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity-to-style mapping
# ---------------------------------------------------------------------------
_STYLES = {
    "info": "background-color: #2196F3; color: white; border-radius: 6px; padding: 10px 18px;",
    "success": "background-color: #4CAF50; color: white; border-radius: 6px; padding: 10px 18px;",
    "warning": "background-color: #FF9800; color: white; border-radius: 6px; padding: 10px 18px;",
    "error": "background-color: #F44336; color: white; border-radius: 6px; padding: 10px 18px;",
}


class ToastNotification(QLabel):
    """A lightweight pop-up toast notification."""

    def __init__(
        self,
        parent: QWidget,
        message: str,
        severity: str = "info",
        duration_ms: int = 3000,
    ) -> None:
        """Create and display a toast notification.

        Args:
            parent:      Parent widget (typically the main window).
            message:     Text to display.
            severity:    One of 'info', 'success', 'warning', 'error'.
            duration_ms: How long the toast remains visible (ms).
        """
        super().__init__(parent)

        self.setText(message)
        self.setFont(QFont("Segoe UI", 11))
        self.setStyleSheet(_STYLES.get(severity, _STYLES["info"]))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumWidth(280)
        self.adjustSize()

        # Position: top-right of parent
        parent_rect = parent.rect()
        x = parent_rect.width() - self.width() - 20
        y = 20
        self.move(x, y)

        # Opacity effect for fade-out animation
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        # Show the toast
        self.show()
        self.raise_()

        logger.info("Toast [%s]: %s", severity, message)

        # Auto-dismiss timer
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self._fade_out)
        self._dismiss_timer.start(duration_ms)

    # ------------------------------------------------------------------
    # Animation helpers
    # ------------------------------------------------------------------

    def _fade_out(self) -> None:
        """Animate the toast fading out, then delete it."""
        self._animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._animation.setDuration(400)
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.finished.connect(self._remove)
        self._animation.start()

    def _remove(self) -> None:
        """Remove the widget from the parent layout and delete it."""
        self.hide()
        self.deleteLater()


def show_toast(
    parent: QWidget,
    message: str,
    severity: str = "info",
    duration_ms: int = 3000,
) -> ToastNotification:
    """Convenience function to create and display a toast.

    Args:
        parent:      Parent widget.
        message:     Notification text.
        severity:    'info' | 'success' | 'warning' | 'error'.
        duration_ms: Display duration in milliseconds.

    Returns:
        ToastNotification: The created toast instance.
    """
    return ToastNotification(parent, message, severity, duration_ms)