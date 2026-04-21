from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import config as config_mod
from .. import startup
from ..config import Config, HotkeyConfig
from ..custom_store import CustomStore, IMAGE_EXTS
from ..hotkeys import HotkeySpec, VK_BY_NAME
from .theme import APP_STYLE


MOD_OPTIONS = ["ctrl", "alt", "shift", "win"]
# Stable, human-ordered list of pickable keys.
KEY_OPTIONS: list[str] = (
    ["semicolon", "comma", "period", "slash", "minus", "equals", "backtick",
     "quote", "lbracket", "rbracket", "backslash", "space", "tab", "enter"]
    + [chr(ord("a") + i) for i in range(26)]
    + [str(i) for i in range(10)]
    + [f"f{i}" for i in range(1, 13)]
)


class HotkeyDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, initial: HotkeyConfig | None = None):
        super().__init__(parent)
        self.setWindowTitle("Hotkey")
        self.setStyleSheet(APP_STYLE)
        self.setModal(True)

        v = QVBoxLayout(self)
        form = QFormLayout()
        self.mod_boxes: dict[str, QCheckBox] = {}
        mod_row = QHBoxLayout()
        for m in MOD_OPTIONS:
            cb = QCheckBox(m.capitalize())
            self.mod_boxes[m] = cb
            mod_row.addWidget(cb)
        mod_row.addStretch(1)
        form.addRow("Modifiers", self._wrap(mod_row))

        self.key_combo = QComboBox()
        for k in KEY_OPTIONS:
            self.key_combo.addItem(k)
        form.addRow("Key", self.key_combo)

        v.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

        if initial:
            for m in initial.mods:
                if m in self.mod_boxes:
                    self.mod_boxes[m].setChecked(True)
            idx = self.key_combo.findText(initial.key)
            if idx >= 0:
                self.key_combo.setCurrentIndex(idx)
        else:
            self.mod_boxes["ctrl"].setChecked(True)
            idx = self.key_combo.findText("semicolon")
            if idx >= 0:
                self.key_combo.setCurrentIndex(idx)

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def result_config(self) -> HotkeyConfig:
        mods = [m for m, cb in self.mod_boxes.items() if cb.isChecked()]
        key = self.key_combo.currentText()
        return HotkeyConfig(mods=mods, key=key, action="open_picker")

    def _accept(self) -> None:
        cfg = self.result_config()
        if not cfg.mods:
            QMessageBox.warning(self, "SmartEmoji", "Pick at least one modifier (Ctrl/Alt/Shift/Win).")
            return
        if cfg.key not in VK_BY_NAME:
            QMessageBox.warning(self, "SmartEmoji", "Pick a key.")
            return
        self.accept()


class AliasDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, initial: tuple[str, str] | None = None):
        super().__init__(parent)
        self.setWindowTitle("Shortcode")
        self.setStyleSheet(APP_STYLE)
        self.setModal(True)

        v = QVBoxLayout(self)
        form = QFormLayout()
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("shrug")
        form.addRow("Shortcode", self.code_edit)
        self.emoji_edit = QLineEdit()
        self.emoji_edit.setPlaceholderText("🤷 (paste the emoji here)")
        form.addRow("Emoji", self.emoji_edit)
        v.addLayout(form)

        hint = QLabel("Tip: typing the shortcode in the picker will insert this emoji.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8a90a2; font-size: 11px;")
        v.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

        if initial:
            self.code_edit.setText(initial[0])
            self.emoji_edit.setText(initial[1])
            self.code_edit.setEnabled(False)

    def result(self) -> tuple[str, str]:
        return self.code_edit.text().strip().lower(), self.emoji_edit.text().strip()

    def _accept(self) -> None:
        code, char = self.result()
        if not code or not char:
            QMessageBox.warning(self, "SmartEmoji", "Shortcode and emoji are both required.")
            return
        self.accept()


class ImageDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, initial: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Image emoji")
        self.setStyleSheet(APP_STYLE)
        self.setModal(True)
        self._picked_path = initial.get("path") if initial else ""

        v = QVBoxLayout(self)
        form = QFormLayout()

        path_row = QHBoxLayout()
        self.path_label = QLabel(self._picked_path or "(no file selected)")
        self.path_label.setWordWrap(True)
        pick = QPushButton("Choose file…")
        pick.clicked.connect(self._pick)
        path_row.addWidget(self.path_label, 1)
        path_row.addWidget(pick)
        form.addRow("Image", self._wrap(path_row))

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("wave")
        form.addRow("Name", self.name_edit)

        self.codes_edit = QLineEdit()
        self.codes_edit.setPlaceholderText("wave, hi, hello")
        form.addRow("Shortcodes", self.codes_edit)

        v.addLayout(form)

        hint = QLabel("Image will paste as an image (clipboard → Ctrl+V). Works in rich-text apps like Word, Outlook, Slack, Discord.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8a90a2; font-size: 11px;")
        v.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

        if initial:
            self.name_edit.setText(initial.get("name", ""))
            self.codes_edit.setText(", ".join(initial.get("codes", [])))

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _pick(self) -> None:
        exts = " ".join(f"*{e}" for e in sorted(IMAGE_EXTS))
        path, _ = QFileDialog.getOpenFileName(self, "Pick image", "", f"Images ({exts})")
        if path:
            self._picked_path = path
            self.path_label.setText(path)

    def result(self) -> dict:
        return {
            "path": self._picked_path,
            "name": self.name_edit.text().strip(),
            "codes": [c.strip() for c in self.codes_edit.text().split(",") if c.strip()],
        }

    def _accept(self) -> None:
        r = self.result()
        if not r["path"]:
            QMessageBox.warning(self, "SmartEmoji", "Pick an image file first.")
            return
        if not r["codes"]:
            QMessageBox.warning(self, "SmartEmoji", "Add at least one shortcode so you can search for it.")
            return
        self.accept()


class SettingsWindow(QDialog):
    changed = Signal()

    def __init__(self, cfg: Config, customs: CustomStore, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("SmartEmoji settings")
        self.setStyleSheet(APP_STYLE)
        self.resize(560, 500)
        self._cfg = cfg
        self._customs = customs

        outer = QVBoxLayout(self)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)

        self.tabs.addTab(self._build_hotkeys_tab(), "Hotkeys")
        self.tabs.addTab(self._build_codes_tab(), "Shortcodes")
        self.tabs.addTab(self._build_images_tab(), "Images")
        self.tabs.addTab(self._build_general_tab(), "General")

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        outer.addLayout(btn_row)

    # ---------- tabs ----------

    def _build_hotkeys_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        intro = QLabel("Keyboard shortcuts that open the emoji picker. You can have several.")
        intro.setStyleSheet("color: #8a90a2;")
        v.addWidget(intro)

        self.hotkey_list = QListWidget()
        self._refresh_hotkey_list()
        v.addWidget(self.hotkey_list, 1)

        row = QHBoxLayout()
        add = QPushButton("Add…")
        add.clicked.connect(self._add_hotkey)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove_hotkey)
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        v.addLayout(row)
        return w

    def _refresh_hotkey_list(self) -> None:
        self.hotkey_list.clear()
        for h in self._cfg.hotkeys:
            try:
                spec = HotkeySpec.from_names(id=1, mod_names=h.mods, key_name=h.key)
                label = spec.display()
            except KeyError:
                label = "+".join(h.mods + [h.key]) + "  (invalid)"
            self.hotkey_list.addItem(label)

    def _add_hotkey(self) -> None:
        dlg = HotkeyDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._cfg.hotkeys.append(dlg.result_config())
            config_mod.save(self._cfg)
            self._refresh_hotkey_list()
            self.changed.emit()

    def _remove_hotkey(self) -> None:
        row = self.hotkey_list.currentRow()
        if row < 0 or row >= len(self._cfg.hotkeys):
            return
        if len(self._cfg.hotkeys) == 1:
            QMessageBox.information(self, "SmartEmoji", "Keep at least one hotkey.")
            return
        del self._cfg.hotkeys[row]
        config_mod.save(self._cfg)
        self._refresh_hotkey_list()
        self.changed.emit()

    # --- shortcodes ---

    def _build_codes_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        intro = QLabel("Map a shortcode to a Unicode emoji. Typing the shortcode in the picker inserts the emoji.")
        intro.setStyleSheet("color: #8a90a2;")
        intro.setWordWrap(True)
        v.addWidget(intro)

        self.codes_table = QTableWidget(0, 2)
        self.codes_table.setHorizontalHeaderLabels(["Shortcode", "Emoji"])
        self.codes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.codes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.codes_table.verticalHeader().setVisible(False)
        self.codes_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.codes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._refresh_codes_table()
        v.addWidget(self.codes_table, 1)

        row = QHBoxLayout()
        add = QPushButton("Add…")
        add.clicked.connect(self._add_alias)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove_alias)
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch(1)
        v.addLayout(row)
        return w

    def _refresh_codes_table(self) -> None:
        aliases = self._customs.aliases()
        self.codes_table.setRowCount(len(aliases))
        for r, (code, char) in enumerate(sorted(aliases.items())):
            self.codes_table.setItem(r, 0, QTableWidgetItem(code))
            self.codes_table.setItem(r, 1, QTableWidgetItem(char))

    def _add_alias(self) -> None:
        dlg = AliasDialog(self)
        if dlg.exec() == QDialog.Accepted:
            code, char = dlg.result()
            self._customs.set_alias(code, char)
            self._refresh_codes_table()
            self.changed.emit()

    def _remove_alias(self) -> None:
        row = self.codes_table.currentRow()
        if row < 0:
            return
        code = self.codes_table.item(row, 0).text()
        self._customs.remove_alias(code)
        self._refresh_codes_table()
        self.changed.emit()

    # --- images ---

    def _build_images_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)

        intro = QLabel("Your own images, pastable as images. Each needs at least one shortcode to be searchable.")
        intro.setStyleSheet("color: #8a90a2;")
        intro.setWordWrap(True)
        v.addWidget(intro)

        self.images_list = QListWidget()
        self.images_list.setIconSize(self.images_list.iconSize() * 1.2)
        self._refresh_images_list()
        v.addWidget(self.images_list, 1)

        row = QHBoxLayout()
        add = QPushButton("Add…")
        add.clicked.connect(self._add_image)
        edit = QPushButton("Edit…")
        edit.clicked.connect(self._edit_image)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove_image)
        row.addWidget(add)
        row.addWidget(edit)
        row.addWidget(remove)
        row.addStretch(1)
        v.addLayout(row)
        return w

    def _refresh_images_list(self) -> None:
        self.images_list.clear()
        for img in self._customs.images():
            item = QListWidgetItem()
            item.setData(Qt.UserRole, img["id"])
            pm = QPixmap(img["path"])
            if not pm.isNull():
                pm = pm.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item.setIcon(QIcon(pm))
            codes = ", ".join(img.get("codes", []))
            item.setText(f"{img.get('name','')}   ({codes})")
            self.images_list.addItem(item)

    def _add_image(self) -> None:
        dlg = ImageDialog(self)
        if dlg.exec() == QDialog.Accepted:
            r = dlg.result()
            try:
                self._customs.add_image(r["path"], r["name"], r["codes"])
            except Exception as e:
                QMessageBox.warning(self, "SmartEmoji", f"Failed to add image: {e}")
                return
            self._refresh_images_list()
            self.changed.emit()

    def _edit_image(self) -> None:
        item = self.images_list.currentItem()
        if item is None:
            return
        image_id = item.data(Qt.UserRole)
        imgs = self._customs.images()
        current = next((i for i in imgs if i["id"] == image_id), None)
        if current is None:
            return
        dlg = ImageDialog(self, initial=current)
        if dlg.exec() == QDialog.Accepted:
            r = dlg.result()
            self._customs.update_image(image_id, name=r["name"], codes=r["codes"])
            self._refresh_images_list()
            self.changed.emit()

    def _remove_image(self) -> None:
        item = self.images_list.currentItem()
        if item is None:
            return
        image_id = item.data(Qt.UserRole)
        self._customs.remove_image(image_id)
        self._refresh_images_list()
        self.changed.emit()

    # --- general ---

    def _build_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self.startup_cb = QCheckBox("Launch at Windows startup")
        self.startup_cb.setChecked(startup.is_enabled())
        self.startup_cb.toggled.connect(self._on_startup_toggled)
        form.addRow(self.startup_cb)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(4, 20)
        self.cols_spin.setValue(self._cfg.grid_cols)
        self.cols_spin.valueChanged.connect(self._on_grid_changed)
        form.addRow("Grid columns", self.cols_spin)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 12)
        self.rows_spin.setValue(self._cfg.grid_rows)
        self.rows_spin.valueChanged.connect(self._on_grid_changed)
        form.addRow("Grid rows", self.rows_spin)

        self.caption_cb = QCheckBox("Show caption (name + shortcode under the grid)")
        self.caption_cb.setChecked(self._cfg.show_caption)
        self.caption_cb.toggled.connect(self._on_grid_changed)
        form.addRow(self.caption_cb)

        data_dir_label = QLabel(str(config_mod.app_data_dir()))
        data_dir_label.setWordWrap(True)
        data_dir_label.setStyleSheet("color: #8a90a2; font-size: 11px;")
        form.addRow("Data folder", data_dir_label)
        return w

    def _on_startup_toggled(self, checked: bool) -> None:
        try:
            if checked:
                startup.enable()
            else:
                startup.disable()
        except Exception as e:
            QMessageBox.warning(self, "SmartEmoji", f"Startup change failed: {e}")

    def _on_grid_changed(self, _=None) -> None:
        self._cfg.grid_cols = self.cols_spin.value()
        self._cfg.grid_rows = self.rows_spin.value()
        self._cfg.show_caption = self.caption_cb.isChecked()
        config_mod.save(self._cfg)
        self.changed.emit()
