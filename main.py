"""
ArchCAD — Entry point
Phase 1: Core canvas (grid, rooms, walls, select/move, zoom/pan, save/load)
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui     import QPalette, QColor, QFont, QIcon
from mainwindow import MainWindow

_ICON_PATH = Path(__file__).resolve().with_name('icon.ico')


# Near-black Fusion palette + stylesheet.  Accent = orange selection (#ff6600).
_APP_QSS = """
QWidget {
    background-color: #0a0a0a;
    color: #e6e6e6;
    font-family: 'Segoe UI';
    font-size: 9pt;
}
QMainWindow, QDialog, QMessageBox {
    background-color: #0a0a0a;
    color: #e6e6e6;
}
QMenuBar {
    background: #050505;
    color: #e6e6e6;
    border-bottom: 1px solid #222;
    padding: 2px 0;
}
QMenuBar::item { background: transparent; padding: 4px 10px; }
QMenuBar::item:selected { background: #1a1a1a; color: #ff8833; }
QMenu {
    background: #111;
    color: #e6e6e6;
    border: 1px solid #333;
}
QMenu::item:selected { background: #2a2a2a; color: #ff8833; }
QMenu::separator { height: 1px; background: #2a2a2a; margin: 4px 8px; }

QDockWidget {
    color: #cccccc;
    titlebar-close-icon: none;
}
QDockWidget::title {
    background: #111;
    color: #dddddd;
    padding: 4px 8px;
    border-bottom: 1px solid #222;
    font-weight: bold;
}
QDockWidget > QWidget { background: #0d0d0d; }

QStatusBar {
    background: #050505;
    color: #888;
    border-top: 1px solid #222;
}
QStatusBar QLabel { background: transparent; color: #888; }

QScrollArea, QAbstractScrollArea {
    background: #0d0d0d;
    border: none;
}
QScrollBar:vertical {
    background: #0a0a0a; width: 12px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #333; min-height: 24px; border-radius: 4px;
}
QScrollBar::handle:vertical:hover { background: #4a4a4a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #0a0a0a; height: 12px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #333; min-width: 24px; border-radius: 4px;
}
QScrollBar::handle:horizontal:hover { background: #4a4a4a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background: #141414;
    color: #e6e6e6;
    border: 1px solid #333;
    border-radius: 3px;
    padding: 3px 6px;
    selection-background-color: #c85a14;
}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #555;
}
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: #111;
    color: #e6e6e6;
    selection-background-color: #c85a14;
    border: 1px solid #333;
    outline: none;
}

QPushButton {
    background: #1a1a1a;
    color: #e6e6e6;
    border: 1px solid #333;
    border-radius: 3px;
    padding: 4px 10px;
}
QPushButton:hover { background: #242424; border-color: #555; }
QPushButton:pressed { background: #111; }
QPushButton:disabled { color: #555; border-color: #222; }

QToolButton {
    background: transparent;
    color: #e6e6e6;
    border: 1px solid transparent;
    border-radius: 3px;
}
QToolButton:hover { background: #222; border-color: #444; }
QToolButton:checked { background: #2a1a0e; border-color: #c85a14; }

QCheckBox { color: #e6e6e6; spacing: 6px; }
QCheckBox::indicator {
    width: 14px; height: 14px;
    border: 1px solid #444; border-radius: 2px; background: #141414;
}
QCheckBox::indicator:checked { background: #c85a14; border-color: #e07020; }

QHeaderView::section {
    background: #111;
    color: #ccc;
    border: none;
    border-right: 1px solid #222;
    border-bottom: 1px solid #222;
    padding: 4px 6px;
}
QTableWidget, QTableView, QTreeWidget {
    background: #0d0d0d;
    alternate-background-color: #141414;
    color: #e6e6e6;
    gridline-color: #222;
    selection-background-color: #c85a14;
    selection-color: #fff;
    border: 1px solid #222;
}
QTableWidget::item:selected, QTreeWidget::item:selected {
    background: #c85a14; color: #fff;
}

QTabWidget::pane { border: 1px solid #222; background: #0d0d0d; }
QToolTip {
    background: #111; color: #eee;
    border: 1px solid #444; padding: 4px;
}
QInputDialog, QFileDialog { background: #0a0a0a; color: #e6e6e6; }
"""


def _dark_palette() -> QPalette:
    p = QPalette()
    bg, alt, txt, btn = QColor('#0a0a0a'), QColor('#141414'), QColor('#e6e6e6'), QColor('#1a1a1a')
    p.setColor(QPalette.ColorRole.Window,          bg)
    p.setColor(QPalette.ColorRole.WindowText,      txt)
    p.setColor(QPalette.ColorRole.Base,            QColor('#0d0d0d'))
    p.setColor(QPalette.ColorRole.AlternateBase,   alt)
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor('#111111'))
    p.setColor(QPalette.ColorRole.ToolTipText,     txt)
    p.setColor(QPalette.ColorRole.Text,            txt)
    p.setColor(QPalette.ColorRole.Button,          btn)
    p.setColor(QPalette.ColorRole.ButtonText,      txt)
    p.setColor(QPalette.ColorRole.BrightText,      QColor('#ff5050'))
    p.setColor(QPalette.ColorRole.Highlight,       QColor('#c85a14'))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor('#ffffff'))
    p.setColor(QPalette.ColorRole.Link,            QColor('#5aa0ff'))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor('#777777'))
    p.setColor(QPalette.ColorRole.Light,           QColor('#2a2a2a'))
    p.setColor(QPalette.ColorRole.Mid,             QColor('#1a1a1a'))
    p.setColor(QPalette.ColorRole.Dark,            QColor('#050505'))
    p.setColor(QPalette.ColorRole.Shadow,          QColor('#000000'))
    return p


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setPalette(_dark_palette())
    app.setStyleSheet(_APP_QSS)
    app.setFont(QFont('Segoe UI', 9))
    if _ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(_ICON_PATH)))

    w = MainWindow()
    if _ICON_PATH.exists():
        w.setWindowIcon(QIcon(str(_ICON_PATH)))
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
