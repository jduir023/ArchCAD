"""
ArchCAD — Entry point
Phase 1: Core canvas (grid, rooms, walls, select/move, zoom/pan, save/load)
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import Qt
from mainwindow import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
