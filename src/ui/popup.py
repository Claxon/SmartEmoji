from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QEvent, QMimeData, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QKeyEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from ..emoji_data import Emoji, EmojiIndex
from ..foreground import anchor_screen_pos, get_foreground_hwnd, set_foreground_hwnd
from ..paste import send_ctrl_v, send_unicode_text
from ..usage_store import UsageStore
from .theme import APP_STYLE


TILE_SIZE = 42
EMOJI_POINT_SIZE = 22
MAX_RESULTS = 500
PASTE_DELAY_MS = 60
CLIPBOARD_RESTORE_DELAY_MS = 400


def _clone_clipboard_mime() -> QMimeData | None:
    """Snapshot the current clipboard contents so we can restore them later.

    Copies every advertised MIME format into a new QMimeData instance that we
    own. Returns None if the clipboard is empty (nothing to restore).
    """
    src = QGuiApplication.clipboard().mimeData()
    if src is None:
        return None
    formats = src.formats()
    if not formats:
        return None
    copy = QMimeData()
    for fmt in formats:
        data = src.data(fmt)
        if not data.isEmpty():
            copy.setData(fmt, data)
    return copy if copy.formats() else None


def _restore_clipboard(saved: QMimeData | None) -> None:
    cb = QGuiApplication.clipboard()
    if saved is None:
        cb.clear()
        return
    cb.setMimeData(saved)


class EmojiDelegate(QStyledItemDelegate):
    """Paints the emoji character (or user image) centered in the cell,
    bypassing Qt's text-elision logic that was turning glyphs into '...'.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._font = QFont("Segoe UI Emoji")
        self._font.setPointSize(EMOJI_POINT_SIZE)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        rect: QRect = option.rect
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        pad = 2
        tile = rect.adjusted(pad, pad, -pad, -pad)

        if selected:
            painter.setPen(QPen(QColor("#6aa3ff"), 1))
            painter.setBrush(QColor("#28334a"))
            painter.drawRoundedRect(tile, 8, 8)
        elif hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#23262e"))
            painter.drawRoundedRect(tile, 8, 8)

        image_path = index.data(Qt.UserRole + 1)
        char = index.data(Qt.UserRole + 2)
        if image_path:
            pm = QPixmap(image_path)
            if not pm.isNull():
                target = tile.adjusted(4, 4, -4, -4)
                scaled = pm.scaled(target.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = target.x() + (target.width() - scaled.width()) // 2
                y = target.y() + (target.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
        elif char:
            painter.setFont(self._font)
            painter.setPen(QColor("#e9ecf3"))
            painter.drawText(tile, Qt.AlignCenter, char)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        return QSize(TILE_SIZE, TILE_SIZE)


class EmojiPopup(QWidget):
    picked = Signal(str)   # emoji_id

    def __init__(
        self,
        index: EmojiIndex,
        usage: UsageStore,
        cols: int = 10,
        rows: int = 5,
        show_caption: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._index = index
        self._usage = usage
        self._cols = cols
        self._rows = rows
        self._show_caption = show_caption
        self._prev_hwnd = 0
        self._results: list[Emoji] = []

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet(APP_STYLE)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        root = QFrame()
        root.setObjectName("Root")
        outer.addWidget(root)

        self._root_layout = QVBoxLayout(root)
        self._root_layout.setContentsMargins(8, 8, 8, 6)
        self._root_layout.setSpacing(6)

        self.search = QLineEdit()
        self.search.setObjectName("Search")
        self.search.setPlaceholderText("Search emoji…")
        self.search.setClearButtonEnabled(False)
        self.search.textChanged.connect(self._on_query_changed)
        self.search.installEventFilter(self)
        self._root_layout.addWidget(self.search)

        self.grid = QListWidget()
        self.grid.setObjectName("EmojiGrid")
        self.grid.setViewMode(QListView.IconMode)
        self.grid.setFlow(QListView.LeftToRight)
        self.grid.setWrapping(True)
        self.grid.setResizeMode(QListView.Adjust)
        self.grid.setMovement(QListView.Static)
        self.grid.setSelectionMode(QListWidget.SingleSelection)
        self.grid.setUniformItemSizes(True)
        self.grid.setMouseTracking(True)
        self.grid.setGridSize(QSize(TILE_SIZE, TILE_SIZE))
        self.grid.setSpacing(0)
        self.grid.setTextElideMode(Qt.ElideNone)
        self.grid.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.grid.setItemDelegate(EmojiDelegate(self.grid))
        self.grid.itemActivated.connect(self._confirm_item)
        self.grid.itemClicked.connect(self._confirm_item)
        self.grid.currentItemChanged.connect(self._on_current_changed)
        self.grid.setFocusPolicy(Qt.NoFocus)  # keep focus on search
        self._root_layout.addWidget(self.grid)

        self.caption_row = QWidget()
        cap_row = QHBoxLayout(self.caption_row)
        cap_row.setContentsMargins(0, 0, 0, 0)
        cap_row.setSpacing(8)
        self.caption = QLabel("")
        self.caption.setObjectName("Caption")
        cap_row.addWidget(self.caption, 1)
        self.caption_hint = QLabel("↵ paste · Esc cancel")
        self.caption_hint.setObjectName("CaptionDim")
        cap_row.addWidget(self.caption_hint, 0, Qt.AlignRight)
        self._root_layout.addWidget(self.caption_row)

        self.apply_layout(cols=cols, rows=rows, show_caption=show_caption)

    # ---------- layout ----------

    def apply_layout(self, cols: int, rows: int, show_caption: bool) -> None:
        self._cols = max(1, int(cols))
        self._rows = max(1, int(rows))
        self._show_caption = bool(show_caption)
        self.caption_row.setVisible(self._show_caption)
        self.grid.setFixedHeight(self._grid_height())

        # Release any prior fixed size so the window can shrink.
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.updateGeometry()
        self.layout().activate()
        hint = self.sizeHint()
        w = self._ideal_width()
        h = hint.height()
        self.resize(w, h)
        self.setFixedSize(w, h)

    def _grid_height(self) -> int:
        # Qt's list view adds ~2px frame padding; cover that with a little margin.
        return TILE_SIZE * self._rows + 4

    def _ideal_width(self) -> int:
        # TILE_SIZE per column + list-view padding (2px * 2) + root frame margins (8 * 2) + 1px border * 2.
        return TILE_SIZE * self._cols + 2 * 2 + 2 * 8 + 2

    # ---------- show / place ----------

    def show_at_caret(self) -> None:
        self._prev_hwnd = get_foreground_hwnd()
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self._populate("")
        self._place_at(anchor_screen_pos())
        self.show()
        self.raise_()
        self.activateWindow()
        self.search.setFocus(Qt.ActiveWindowFocusReason)

    def _place_at(self, anchor: Optional[tuple[int, int]]) -> None:
        self.adjustSize()
        w, h = self.width(), self.height()
        if anchor is None:
            screen = QGuiApplication.primaryScreen()
            geo = screen.availableGeometry()
            self.move(geo.x() + (geo.width() - w) // 2, geo.y() + int(geo.height() * 0.25))
            return
        ax, ay = anchor
        screen = QGuiApplication.screenAt(QPoint(ax, ay)) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = ax - 24
        y = ay + 18
        if y + h > geo.y() + geo.height() - 8:
            y = ay - h - 8
        x = max(geo.x() + 8, min(x, geo.x() + geo.width() - w - 8))
        y = max(geo.y() + 8, min(y, geo.y() + geo.height() - h - 8))
        self.move(x, y)

    # ---------- populate ----------

    def _populate(self, query: str) -> None:
        if query:
            results = self._index.search(query, limit=MAX_RESULTS)
        else:
            results = sorted(
                self._index.all(),
                key=lambda e: (self._usage.sort_key(e.id), e.rank),
            )[:MAX_RESULTS]
        self._results = results

        self.grid.blockSignals(True)
        self.grid.clear()
        for e in results:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, e.id)
            item.setData(Qt.UserRole + 1, e.image_path if e.is_image else None)
            item.setData(Qt.UserRole + 2, e.char)
            item.setSizeHint(QSize(TILE_SIZE, TILE_SIZE))
            item.setToolTip(self._tooltip(e))
            self.grid.addItem(item)
        self.grid.blockSignals(False)

        if self.grid.count():
            self.grid.setCurrentRow(0)
            self._update_caption(results[0])
        else:
            self._update_caption(None)

    def _tooltip(self, e: Emoji) -> str:
        parts = [e.name]
        if e.codes:
            parts.append(":" + e.codes[0] + ":")
        return "  ".join(parts)

    def _update_caption(self, e: Optional[Emoji]) -> None:
        if not self._show_caption:
            return
        if e is None:
            self.caption.setText("No matches")
            return
        code = f"  ·  :{e.codes[0]}:" if e.codes else ""
        self.caption.setText(f"{e.name}{code}")

    # ---------- slots ----------

    def _on_query_changed(self, text: str) -> None:
        self._populate(text)

    def _on_current_changed(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            self._update_caption(None)
            return
        eid = current.data(Qt.UserRole)
        e = self._index.by_id(eid)
        self._update_caption(e)

    # ---------- confirm ----------

    def _confirm_item(self, item: QListWidgetItem) -> None:
        eid = item.data(Qt.UserRole)
        e = self._index.by_id(eid)
        if e is None:
            return
        self._confirm(e)

    def _confirm_current(self) -> None:
        item = self.grid.currentItem()
        if item is None:
            return
        self._confirm_item(item)

    def _confirm(self, e: Emoji) -> None:
        self._usage.record(e.id)
        self._usage.flush()
        self.hide()
        prev = self._prev_hwnd
        self.picked.emit(e.id)

        if e.is_image and e.image_path:
            # Images still need the clipboard + Ctrl+V path.
            img = QImage(e.image_path)
            if img.isNull():
                return
            saved = _clone_clipboard_mime()
            QGuiApplication.clipboard().setImage(img)

            def _paste_image() -> None:
                if prev:
                    set_foreground_hwnd(prev)
                send_ctrl_v()
                # Give the target app time to read the image off the clipboard
                # before we swap the user's original contents back in.
                QTimer.singleShot(
                    CLIPBOARD_RESTORE_DELAY_MS,
                    lambda: _restore_clipboard(saved),
                )
            QTimer.singleShot(PASTE_DELAY_MS, _paste_image)
            return

        if e.char:
            char = e.char

            def _type_unicode() -> None:
                if prev:
                    set_foreground_hwnd(prev)
                send_unicode_text(char)
            QTimer.singleShot(PASTE_DELAY_MS, _type_unicode)

    def _cancel(self) -> None:
        self.hide()
        prev = self._prev_hwnd
        if prev:
            QTimer.singleShot(10, lambda: set_foreground_hwnd(prev))

    # ---------- event handling ----------

    def eventFilter(self, obj, event):  # type: ignore[override]
        if obj is self.search and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()
            if key == Qt.Key_Escape:
                self._cancel()
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._confirm_current()
                return True
            if key == Qt.Key_Down:
                self._move_selection(self._cols)
                return True
            if key == Qt.Key_Up:
                self._move_selection(-self._cols)
                return True
            if key == Qt.Key_Right:
                self._move_selection(1)
                return True
            if key == Qt.Key_Left:
                self._move_selection(-1)
                return True
            if key == Qt.Key_Tab:
                self._move_selection(1)
                return True
            if key == Qt.Key_Backtab:
                self._move_selection(-1)
                return True
            if key == Qt.Key_PageDown:
                self._move_selection(self._cols * self._rows)
                return True
            if key == Qt.Key_PageUp:
                self._move_selection(-self._cols * self._rows)
                return True
            if key == Qt.Key_Home and (mods & Qt.ControlModifier):
                self.grid.setCurrentRow(0)
                return True
            if key == Qt.Key_End and (mods & Qt.ControlModifier):
                if self.grid.count():
                    self.grid.setCurrentRow(self.grid.count() - 1)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self._cancel()
            return
        super().keyPressEvent(event)

    def changeEvent(self, event):  # type: ignore[override]
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow() and self.isVisible():
            self._cancel()
        super().changeEvent(event)

    def _move_selection(self, delta: int) -> None:
        count = self.grid.count()
        if not count:
            return
        cur = self.grid.currentRow()
        if cur < 0:
            cur = 0
        new = max(0, min(count - 1, cur + delta))
        self.grid.setCurrentRow(new)
        self.grid.scrollToItem(self.grid.currentItem())
