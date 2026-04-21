APP_STYLE = """
* {
    font-family: "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
    font-size: 13px;
    color: #e6e8ee;
}
QWidget#Root {
    background: #1b1d23;
    border: 1px solid #2c303a;
    border-radius: 14px;
}
QLabel#Title {
    color: #aab1c2;
    font-size: 11px;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    padding: 2px;
}
QLabel#Hint {
    color: #7e8494;
    font-size: 11px;
    padding: 2px;
}
QLabel#Caption {
    color: #cdd3e0;
    font-size: 12px;
    padding: 4px 2px 0;
}
QLabel#CaptionDim {
    color: #7e8494;
    font-size: 11px;
    padding: 4px 2px 0;
}
QLineEdit#Search {
    background: #23262e;
    border: 1px solid #2f333e;
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 14px;
    color: #e9ecf3;
    selection-background-color: #3a5a95;
}
QLineEdit#Search:focus {
    border: 1px solid #6aa3ff;
}
QListWidget#EmojiGrid {
    background: transparent;
    border: none;
    outline: 0;
    padding: 2px;
}
QListWidget#EmojiGrid::item {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    margin: 2px;
}
QListWidget#EmojiGrid::item:selected {
    background: #28334a;
    border: 1px solid #6aa3ff;
    color: #e9ecf3;
}
QListWidget#EmojiGrid::item:hover {
    background: #23262e;
}
QListWidget, QTableWidget, QTreeWidget {
    background: #181a20;
    border: 1px solid #2c303a;
    border-radius: 10px;
    padding: 6px;
    outline: 0;
}
QHeaderView::section {
    background: #23262e;
    color: #aab1c2;
    border: none;
    padding: 6px 10px;
}
QPushButton {
    background: #2a2f3a;
    color: #e6e8ee;
    border: 1px solid #373c48;
    border-radius: 8px;
    padding: 6px 12px;
}
QPushButton:hover { background: #323846; }
QPushButton:pressed { background: #232834; }
QPushButton:default { background: #3a5a95; border: 1px solid #6aa3ff; }
QPushButton:default:hover { background: #456cae; }
QLineEdit, QSpinBox, QComboBox {
    background: #23262e;
    border: 1px solid #2f333e;
    border-radius: 8px;
    padding: 5px 8px;
    color: #e9ecf3;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #6aa3ff;
}
QTabWidget::pane {
    border: 1px solid #2c303a;
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    background: #23262e;
    color: #aab1c2;
    padding: 8px 14px;
    border: 1px solid #2c303a;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1b1d23;
    color: #e6e8ee;
}
QScrollBar:vertical {
    background: transparent; width: 10px; margin: 2px;
}
QScrollBar::handle:vertical {
    background: #373c48; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #4a5162; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: transparent; height: 10px; margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #373c48; border-radius: 4px; min-width: 30px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""
