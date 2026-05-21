"""
ArchCAD — Ruler widgets (HRuler + VRuler)

Placed in a QGridLayout around the CADCanvas.
Scene unit = 1 inch.  Rulers display real-world feet.
"""

import math

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore    import QPointF
from PyQt6.QtGui     import QPainter, QPen, QColor, QFont

RULER_W = 20   # ruler strip width / height in pixels

# "Nice" real-foot intervals for tick labels
_NICE_FT = [1, 2, 5, 10, 25, 50, 100, 200, 500]


def _nice_step(px_per_ft: float) -> float:
    """Return the smallest 'nice' step that puts major ticks ≥ 40 px apart."""
    for s in _NICE_FT:
        if px_per_ft * s >= 40:
            return float(s)
    return float(_NICE_FT[-1])


class HRuler(QWidget):
    """Horizontal ruler that mirrors the canvas viewport's X axis."""

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.setFixedHeight(RULER_W)
        self._view = view
        view.viewport_changed.connect(self.update)

    def paintEvent(self, event):
        v    = self._view
        vp   = v.viewport()
        vpw  = vp.width()
        vph  = vp.height()

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#ebebea'))

        # Bottom border
        painter.setPen(QPen(QColor('#aaaaaa'), 1))
        painter.drawLine(0, RULER_W - 1, self.width(), RULER_W - 1)

        # Visible scene range
        scene_l = v.mapToScene(0,   0).x()
        scene_r = v.mapToScene(vpw, 0).x()
        if scene_r <= scene_l:
            return

        px_per_scene_in = vpw / (scene_r - scene_l)
        px_per_ft       = px_per_scene_in * 12   # 12 scene inches = 1 real foot

        step = _nice_step(px_per_ft)
        half = step / 2

        font = QFont('Segoe UI', 7)
        painter.setFont(font)

        # Major ticks + labels
        start = math.floor(scene_l / 12 / step) * step
        ft    = start
        while ft * 12 <= scene_r + step * 12:
            px = int(v.mapFromScene(QPointF(ft * 12, 0)).x())
            if -2 <= px <= self.width() + 2:
                painter.setPen(QPen(QColor('#555555'), 1))
                painter.drawLine(px, RULER_W // 2, px, RULER_W)
                painter.setPen(QPen(QColor('#333333'), 1))
                painter.drawText(px + 2, RULER_W - 4, f"{int(ft)}'")
            ft += step

        # Minor ticks (half step)
        ft = math.floor(scene_l / 12 / half) * half
        painter.setPen(QPen(QColor('#aaaaaa'), 1))
        while ft * 12 <= scene_r + half * 12:
            px = int(v.mapFromScene(QPointF(ft * 12, 0)).x())
            if 0 <= px <= self.width():
                painter.drawLine(px, RULER_W * 3 // 4, px, RULER_W)
            ft += half


class VRuler(QWidget):
    """Vertical ruler that mirrors the canvas viewport's Y axis."""

    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.setFixedWidth(RULER_W)
        self._view = view
        view.viewport_changed.connect(self.update)

    def paintEvent(self, event):
        v    = self._view
        vp   = v.viewport()
        vpw  = vp.width()
        vph  = vp.height()

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#ebebea'))

        # Right border
        painter.setPen(QPen(QColor('#aaaaaa'), 1))
        painter.drawLine(RULER_W - 1, 0, RULER_W - 1, self.height())

        scene_t = v.mapToScene(0, 0).y()
        scene_b = v.mapToScene(0, vph).y()
        if scene_b <= scene_t:
            return

        px_per_scene_in = vph / (scene_b - scene_t)
        px_per_ft       = px_per_scene_in * 12

        step = _nice_step(px_per_ft)
        half = step / 2

        font = QFont('Segoe UI', 7)
        painter.setFont(font)

        # Major ticks + labels
        start = math.floor(scene_t / 12 / step) * step
        ft    = start
        while ft * 12 <= scene_b + step * 12:
            py = int(v.mapFromScene(QPointF(0, ft * 12)).y())
            if -2 <= py <= self.height() + 2:
                painter.setPen(QPen(QColor('#555555'), 1))
                painter.drawLine(RULER_W // 2, py, RULER_W, py)
                painter.save()
                painter.setPen(QPen(QColor('#333333'), 1))
                painter.translate(RULER_W - 4, py - 2)
                painter.rotate(-90)
                painter.drawText(0, 0, f"{int(ft)}'")
                painter.restore()
            ft += step

        # Minor ticks
        ft = math.floor(scene_t / 12 / half) * half
        painter.setPen(QPen(QColor('#aaaaaa'), 1))
        while ft * 12 <= scene_b + half * 12:
            py = int(v.mapFromScene(QPointF(0, ft * 12)).y())
            if 0 <= py <= self.height():
                painter.drawLine(RULER_W * 3 // 4, py, RULER_W, py)
            ft += half
