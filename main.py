from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from src import config as config_mod
from src import single_instance
from src.custom_store import CustomStore
from src.emoji_data import EmojiIndex
from src.hotkeys import HotkeyManager
from src.ui.popup import EmojiPopup
from src.ui.settings import SettingsWindow
from src.ui.tray import TrayController
from src.usage_store import UsageStore


class SmartEmojiApp:
    def __init__(self, qt_app: QApplication):
        self.app = qt_app
        self.app.setQuitOnLastWindowClosed(False)

        self.config = config_mod.load()
        self.customs = CustomStore()
        self.usage = UsageStore()
        self.index = EmojiIndex(self.customs)

        self.popup = EmojiPopup(
            self.index,
            self.usage,
            cols=self.config.grid_cols,
            rows=self.config.grid_rows,
            show_caption=self.config.show_caption,
        )
        self.settings = SettingsWindow(self.config, self.customs)
        self.tray = TrayController()
        self.hotkeys = HotkeyManager(self.config.hotkey_specs())

        self.hotkeys.hotkey.connect(self._on_hotkey)
        self.tray.open_picker.connect(self.popup.show_at_caret)
        self.tray.open_settings.connect(self._show_settings)
        self.tray.quit_requested.connect(self._quit)
        self.settings.changed.connect(self._on_settings_changed)
        self.app.aboutToQuit.connect(self._on_about_to_quit)

        self.hotkeys.start()

    def _on_hotkey(self, name: str) -> None:
        if name == "open_picker":
            self.popup.show_at_caret()

    def _show_settings(self) -> None:
        self.tray.refresh_startup_state()
        self.settings.show()
        self.settings.raise_()
        self.settings.activateWindow()

    def _on_settings_changed(self) -> None:
        self.index.reload()
        self.popup.apply_layout(
            cols=self.config.grid_cols,
            rows=self.config.grid_rows,
            show_caption=self.config.show_caption,
        )
        self.hotkeys.replace(self.config.hotkey_specs())
        self.tray.refresh_startup_state()

    def _on_about_to_quit(self) -> None:
        try:
            self.usage.flush()
        except Exception:
            pass

    def _quit(self) -> None:
        self.hotkeys.stop()
        self.app.quit()


def main() -> int:
    # Bail before Qt starts if another SmartEmoji already owns the hotkey.
    # The mutex lives for the rest of this process's life.
    if not single_instance.try_acquire():
        return 0

    app = QApplication(sys.argv)
    app.setApplicationName("SmartEmoji")
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "SmartEmoji", "System tray not available.")
        return 1

    controller = SmartEmojiApp(app)  # noqa: F841
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
