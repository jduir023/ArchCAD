"""
auto_draw.py — AutoDrawEngine
Reads a CodeReport and draws missing structural elements onto the CADCanvas.

All auto-drawn items are wrapped in a single QUndoCommand so that one
Ctrl+Z removes them all.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from canvas import CADCanvas
    from estimator import CodeReport, EstimatorSettings


# ── Minimal undo command for a batch of new items ─────────────────────────────

class _BatchAddCmd:
    """QUndoCommand-compatible: add a list of items to the scene in one undo step."""

    def __init__(self, scene, items: list, label: str = 'Auto-draw'):
        self._scene  = scene
        self._items  = list(items)
        self._label  = label
        self._done   = False

    # QUndoCommand interface
    def text(self): return self._label

    def undo(self):
        for item in self._items:
            self._scene.removeItem(item)
        self._done = False

    def redo(self):
        if self._done:
            for item in self._items:
                self._scene.addItem(item)
        self._done = True


class AutoDrawEngine:
    """
    Reads the auto_fixable issues in a CodeReport and draws the missing
    structural elements directly on the given CADCanvas.

    Returns the number of items drawn.
    """

    # Tag stored in item data slot 0 to mark auto-generated items
    AUTO_TAG = 'auto_generated'

    def run(self, canvas: 'CADCanvas',
            code_report: 'CodeReport',
            settings: 'EstimatorSettings') -> int:
        """
        Draw all auto-fixable issues.  All drawn items are pushed as a
        single undo batch.  Returns item count.
        """
        from PyQt6.QtCore import QUndoCommand
        from canvas import _AddCmd

        fixable = [i for i in code_report.issues if i.auto_fixable]
        if not fixable:
            return 0

        scene = canvas.scene()
        # Get all current joist fill items from scene for coordinate lookup
        from items import JoistFillItem, LineItem, PostItem
        joist_items = [i for i in scene.items()
                       if isinstance(i, JoistFillItem)]

        drawn_items: list = []

        # Process each fixable issue
        for issue in fixable:
            if issue.element == 'Blocking' and issue.severity == 'ERROR':
                new = self._draw_blocking(scene, joist_items, issue, settings)
                drawn_items.extend(new)

            elif issue.element == 'Beam' and issue.severity == 'ERROR':
                new = self._draw_beam(scene, joist_items, issue, settings)
                drawn_items.extend(new)

        if not drawn_items:
            return 0

        # Tag all drawn items
        for item in drawn_items:
            item.setData(0, self.AUTO_TAG)

        # Wrap in undo stack as macro
        stack = canvas._undo_stack
        stack.beginMacro('Auto-Draw Missing Elements')
        for item in drawn_items:
            # Item is already in scene; use _AddCmd so undo removes it
            stack.push(_AddCmd(scene, item))
        stack.endMacro()

        return len(drawn_items)

    # ── Blocking ──────────────────────────────────────────────────────────────

    def _draw_blocking(self, scene, joist_items: list,
                       issue: 'CodeIssue',
                       settings: 'EstimatorSettings') -> list:
        """Add horizontal blocking lines at required mid-span positions."""
        from items import LineItem
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPen, QColor

        # Parse bay index from location string ('bay N')
        bay_idx = self._parse_bay(issue.location)
        if bay_idx < 0 or bay_idx >= len(joist_items):
            return []

        jf = joist_items[bay_idx]
        jf_rect = jf.mapToScene(jf.boundingRect()).boundingRect()

        x0 = jf_rect.left()
        x1 = jf_rect.right()
        w  = jf_rect.width()
        h  = jf_rect.height()

        # Determine span direction and number of blocking rows needed
        from code_tables import blocking_rows_required
        direction = getattr(jf, 'direction', 'h')
        span_in   = h if direction == 'h' else w
        rows_need = blocking_rows_required(span_in)
        rows_have = getattr(jf, 'blocking_rows', 0)
        rows_add  = max(0, rows_need - rows_have)

        added = []
        y0 = jf_rect.top()
        y1 = jf_rect.bottom()
        span_h = y1 - y0

        for r in range(1, rows_add + 1):
            # Evenly spaced blocking rows
            t  = r / (rows_add + 1)
            y  = y0 + span_h * t

            line_item = LineItem(x0, y, x1, y, color='#8B4513')
            line_item.setToolTip(f'Blocking — auto-draw (IRC R502.7)')
            scene.addItem(line_item)
            added.append(line_item)

        return added

    # ── Beam ──────────────────────────────────────────────────────────────────

    def _draw_beam(self, scene, joist_items: list,
                   issue: 'CodeIssue',
                   settings: 'EstimatorSettings') -> list:
        """Add a beam line at mid-span perpendicular to joist direction."""
        from items import LineItem
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPen, QColor

        bay_idx = self._parse_bay(issue.location)
        if bay_idx < 0 or bay_idx >= len(joist_items):
            return []

        jf = joist_items[bay_idx]
        jf_rect = jf.mapToScene(jf.boundingRect()).boundingRect()
        direction = getattr(jf, 'direction', 'h')

        if direction == 'h':
            # Joists run horizontally — beam runs vertically at mid-span
            mid_y = (jf_rect.top() + jf_rect.bottom()) / 2
            beam_item = LineItem(jf_rect.left(), mid_y, jf_rect.right(), mid_y,
                                 color='#4040A0')
        else:
            mid_x = (jf_rect.left() + jf_rect.right()) / 2
            beam_item = LineItem(mid_x, jf_rect.top(), mid_x, jf_rect.bottom(),
                                 color='#4040A0')

        # override pen to be thicker to indicate a beam
        from PyQt6.QtGui import QPen, QColor
        pen = QPen(QColor('#4040A0'), 4)
        pen.setCosmetic(True)
        beam_item.setPen(pen)
        beam_item.setToolTip(
            f'Beam — auto-draw: {issue.required} required (IRC R507.5)')
        scene.addItem(beam_item)
        return [beam_item]

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_bay(location: str) -> int:
        """Extract 0-based index from 'bay N' strings."""
        try:
            return int(location.split()[-1]) - 1
        except (ValueError, IndexError):
            return -1
