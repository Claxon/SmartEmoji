from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .. import startup


def _make_icon() -> QIcon:
    pm = QPixmap(32, 32)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(QBrush(QColor("#f7c843")))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(2, 2, 28, 28, 8, 8)
    p.setPen(QColor("#1b1d23"))
    font = QFont("Segoe UI Emoji", 16)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, "🙂")
    p.end()
    return QIcon(pm)


class TrayController(QObject):
    open_picker = Signal()
    open_settings = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.tray = QSystemTrayIcon(_make_icon(), parent)
        self.tray.setToolTip("SmartEmoji")

        menu = QMenu()
        act_picker = QAction("Open picker", menu)
        act_picker.triggered.connect(self.open_picker)
        menu.addAction(act_picker)

        act_settings = QAction("Settings…", menu)
        act_settings.triggered.connect(self.open_settings)
        menu.addAction(act_settings)

        menu.addSeparator()

        self.act_startup = QAction("Run at startup", menu)
        self.act_startup.setCheckable(True)
        self.act_startup.setChecked(startup.is_enabled())
        self.act_startup.toggled.connect(self._on_startup_toggled)
        menu.addAction(self.act_startup)

        menu.addSeparator()
        act_quit = QAction("Quit", menu)
        act_quit.triggered.connect(self.quit_requested)
        menu.addAction(act_quit)

        self._menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.open_picker.emit()

    def _on_startup_toggled(self, checked: bool) -> None:
        try:
            if checked:
                startup.enable()
            else:
                startup.disable()
        except Exception as e:
            self.tray.showMessage("SmartEmoji", f"Startup change failed: {e}")

    def refresh_startup_state(self) -> None:
        self.act_startup.setChecked(startup.is_enabled())

    def notify(self, title: str, message: str) -> None:
        self.tray.showMessage(title, message, QSystemTrayIcon.Information, 2000)
