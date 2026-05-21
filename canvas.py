"""
ArchCAD — Drawing canvas
Scene unit = 1 inch.  Grid minor = 12 in (1 ft).  Grid major = 48 in (4 ft).
Default zoom: 2 px/in  →  1 ft = 24 px on screen.
"""

import json
import math
import uuid

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QFileDialog, QMessageBox, QGraphicsItem,
    QInputDialog,
)
from PyQt6.QtCore  import Qt, QPointF, QLineF, QRectF, pyqtSignal
from PyQt6.QtGui   import (QPainter, QPen, QBrush, QColor, QImage, QPixmap,
                           QUndoStack, QUndoCommand)

from items import (RoomItem, WallItem, DoorItem, WindowItem,
                   DimensionItem, PostItem, JoistFillItem,
                   ShapeItem, LineItem, TextItem, GroupItem)
from fixtures import FixtureItem

# ── Constants ─────────────────────────────────────────────────────────────────

GRID_MINOR  = 12    # inches (1 ft)
GRID_MAJOR  = 48    # inches (4 ft)
SNAP_IN     = 12    # default snap — 1 ft
SCENE_HALF  = 1440  # 120 ft each way  (240 ft total canvas)

# ── Tool IDs ─────────────────────────────────────────────────────────────────

TOOL_SELECT    = 'select'
TOOL_PAN       = 'pan'
TOOL_ROOM      = 'room'
TOOL_WALL      = 'wall'
TOOL_DOOR      = 'door'
TOOL_WINDOW    = 'window'
TOOL_DIMENSION = 'dimension'
TOOL_POST      = 'post'
TOOL_JOIST     = 'joist'
TOOL_SHAPE     = 'shape'
TOOL_LINE      = 'line'
TOOL_TEXT      = 'text'
TOOL_FIXTURE   = 'fixture'

# ── Undo commands ─────────────────────────────────────────────────────────────

class _AddCmd(QUndoCommand):
    """Item is already in scene when pushed; first redo() is a no-op."""
    def __init__(self, scene, item, parent=None):
        super().__init__('Add item', parent)
        self._scene = scene
        self._item  = item
        self._first = True

    def undo(self): self._scene.removeItem(self._item)

    def redo(self):
        if self._first:
            self._first = False
            return
        self._scene.addItem(self._item)


class _DeleteCmd(QUndoCommand):
    def __init__(self, scene, items, parent=None):
        super().__init__(f'Delete {len(items)} item(s)', parent)
        self._scene = scene
        self._items = list(items)

    def undo(self):
        for item in self._items: self._scene.addItem(item)

    def redo(self):
        for item in self._items: self._scene.removeItem(item)


class _MoveCmd(QUndoCommand):
    """data: list of (item, old_QPointF, new_QPointF)"""
    def __init__(self, data, parent=None):
        super().__init__(f'Move {len(data)} item(s)', parent)
        self._data = data

    def undo(self):
        for item, old, _ in self._data: item.setPos(old)

    def redo(self):
        for item, _, new in self._data: item.setPos(new)


class _GroupCmd(QUndoCommand):
    """Group items: redo = add group + addToGroup children; undo = removeFromGroup + remove group."""
    def __init__(self, scene, children, group, parent=None):
        super().__init__(f'Group {len(children)} item(s)', parent)
        self._scene    = scene
        self._children = children
        self._group    = group
        self._first    = True

    def undo(self):
        for child in list(self._group.childItems()):
            self._group.removeFromGroup(child)
        self._scene.removeItem(self._group)

    def redo(self):
        if self._first:
            self._first = False
            return
        self._scene.addItem(self._group)
        for child in self._children:
            self._group.addToGroup(child)


class _UngroupCmd(QUndoCommand):
    """Ungroup: redo = removeFromGroup + remove group; undo = add group + addToGroup children."""
    def __init__(self, scene, group, children, parent=None):
        super().__init__('Ungroup', parent)
        self._scene    = scene
        self._group    = group
        self._children = children
        self._first    = True

    def undo(self):
        self._scene.addItem(self._group)
        for child in self._children:
            self._group.addToGroup(child)

    def redo(self):
        if self._first:
            self._first = False
            return
        for child in list(self._group.childItems()):
            self._group.removeFromGroup(child)
        self._scene.removeItem(self._group)


class _PropCmd(QUndoCommand):
    """Generic property change: stores apply/revert callables. First redo is a no-op."""
    def __init__(self, label: str, apply_fn, revert_fn, parent=None):
        super().__init__(label, parent)
        self._apply  = apply_fn
        self._revert = revert_fn
        self._first  = True

    def undo(self): self._revert()

    def redo(self):
        if self._first:
            self._first = False
            return
        self._apply()


class CADCanvas(QGraphicsView):

    status_message    = pyqtSignal(str)
    selection_changed = pyqtSignal(list)    # list[QGraphicsItem]
    viewport_changed  = pyqtSignal()        # scroll or resize
    scale_changed     = pyqtSignal(float)   # scale_ratio updated
    layers_changed    = pyqtSignal()        # layer list modified

    def __init__(self, parent=None):
        scene = QGraphicsScene()
        scene.setSceneRect(-SCENE_HALF, -SCENE_HALF,
                           SCENE_HALF * 2, SCENE_HALF * 2)
        super().__init__(scene, parent)

        # ── state ─────────────────────────────────────────────────────────────
        self._tool         = TOOL_SELECT
        self._snap         = SNAP_IN
        self._show_grid    = True
        self._drawing      = False
        self._draw_start   = None    # QPointF (scene coords)
        self._preview      = None    # live preview item while drawing
        self.project_path  = None    # currently open file
        # ── tool parameters (set by mainwindow) ───────────────────────────────
        self._door_width      = 36    # inches
        self._joist_spacing   = 16.0  # inches o.c.
        self._joist_direction = 'h'   # 'h' or 'v'
        self._post_size       = 3.5   # inches
        self._wall_type       = 'interior'
        self._shape_type      = 'rect'    # 'rect' or 'ellipse'
        self._line_style      = 'solid'   # 'solid', 'dash', 'dot'
        self._text_size       = 12        # font size in points
        self._snap_enabled    = True
        self._fixture_type    = ''        # active fixture key for TOOL_FIXTURE
        self._undo_stack      = QUndoStack(self)
        self._move_origins: dict = {}        # ── layers ──────────────────────────────────────────────────────────────
        self._layers: list[dict] = [{'name': 'Layer 0', 'visible': True, 'locked': False}]
        self._active_layer: int  = 0        # ── page / scale ──────────────────────────────────────────────────────
        self.scale_ratio        = 48    # 1/4" = 1ft  (scene_in * ratio = page_in)
        self._paper_phys_w      = 8.5   # physical paper width  (inches)
        self._paper_phys_h      = 11.0  # physical paper height (inches)
        self._show_page_boundary = True

        # ── view settings ─────────────────────────────────────────────────────
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor('#1e2533')))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # default zoom: 2 px/in
        self.scale(2.0, 2.0)

        def _on_sel_changed(_self=self, _scene=scene):
            try:
                _self.selection_changed.emit(_scene.selectedItems())
            except RuntimeError:
                pass  # C++ object deleted during teardown
        scene.selectionChanged.connect(_on_sel_changed)

    # ── Tool ──────────────────────────────────────────────────────────────────

    def set_tool(self, tool: str):
        self._tool = tool
        if tool == TOOL_SELECT:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        elif tool == TOOL_PAN:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)

    def toggle_grid(self, visible: bool):
        self._show_grid = visible
        self.scene().update()

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def _snap_pt(self, pt: QPointF) -> QPointF:
        if not self._snap_enabled:
            return pt
        s = self._snap
        return QPointF(round(pt.x() / s) * s, round(pt.y() / s) * s)

    def _fmt_pos(self, pt: QPointF) -> str:
        def _fi(v):
            total = int(round(abs(v)))
            sign  = '-' if v < 0 else ' '
            return f"{sign}{total // 12}'-{total % 12:02d}\""
        scale_str = f'  [{self.scale_ratio}:1 scale]'
        return f"X: {_fi(pt.x())}   Y: {_fi(pt.y())}{scale_str}"

    # ── Grid ──────────────────────────────────────────────────────────────────

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        if not self._show_grid:
            return

        def _grid(step, color):
            pen = QPen(color, 0)
            painter.setPen(pen)
            x = float(int(rect.left()  / step) * step)
            y = float(int(rect.top()   / step) * step)
            while x <= rect.right()  + step:
                painter.drawLine(QLineF(x, rect.top(),    x, rect.bottom()))
                x += step
            while y <= rect.bottom() + step:
                painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
                y += step

        _grid(GRID_MINOR, QColor('#2c3a4e'))
        _grid(GRID_MAJOR, QColor('#3a4f68'))

        # origin cross (dashed)
        pen = QPen(QColor('#4a6080'), 0)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawLine(QLineF(rect.left(),  0, rect.right(),  0))
        painter.drawLine(QLineF(0, rect.top(), 0, rect.bottom()))

        # Page boundary
        if self._show_page_boundary:
            pw = self._paper_phys_w * self.scale_ratio
            ph = self._paper_phys_h * self.scale_ratio
            page_pen = QPen(QColor('#7090cc'), 0)
            page_pen.setCosmetic(True)
            page_pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(page_pen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 12)))
            painter.drawRect(QRectF(0, 0, pw, ph))
            painter.setBrush(Qt.BrushStyle.NoBrush)

    # ── Mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        # middle-mouse pan
        if event.button() == Qt.MouseButton.MiddleButton:
            self._pan_last = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if self._tool == TOOL_SELECT:
            if (event.button() == Qt.MouseButton.LeftButton
                    and self.itemAt(event.pos()) is None):
                # Drag on empty space → pan the canvas
                self._sel_pan_last = event.position()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return
            self._move_origins = {}
            super().mousePressEvent(event)
            # Record positions after Qt selects item(s), before any drag
            self._move_origins = {i: i.pos() for i in self.scene().selectedItems()}
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pt = self._snap_pt(self.mapToScene(event.position().toPoint()))
            self._drawing    = True
            self._draw_start = pt

            if self._tool == TOOL_ROOM:
                self._preview = RoomItem(0, 0)
                self._preview.setPos(pt)
                self._preview.setOpacity(0.60)
                self.scene().addItem(self._preview)

            elif self._tool == TOOL_WALL:
                self._preview = WallItem(pt.x(), pt.y(), pt.x(), pt.y(),
                                         self._wall_type)
                self._preview.setOpacity(0.60)
                self.scene().addItem(self._preview)

            elif self._tool == TOOL_DOOR:
                self._preview = DoorItem(36)
                self._preview.setPos(pt)
                self._preview.setOpacity(0.60)
                self.scene().addItem(self._preview)

            elif self._tool == TOOL_WINDOW:
                self._preview = WindowItem(0, 0)
                self._preview.setPos(pt)
                self._preview.setOpacity(0.60)
                self.scene().addItem(self._preview)

            elif self._tool == TOOL_DIMENSION:
                self._preview = DimensionItem(0, 0)
                self._preview.setPos(pt)
                self._preview.setOpacity(0.65)
                self.scene().addItem(self._preview)

            elif self._tool == TOOL_POST:
                # Click-to-place: no drag; place immediately
                post = PostItem(self._post_size)
                post.setPos(pt)
                self.scene().addItem(post)
                post._layer_idx = self._active_layer
                self._undo_stack.push(_AddCmd(self.scene(), post))
                self._drawing = False   # no drag phase

            elif self._tool == TOOL_JOIST:
                self._preview = JoistFillItem(
                    0, 0, self._joist_spacing, self._joist_direction)
                self._preview.setPos(pt)
                self._preview.setOpacity(0.75)
                self.scene().addItem(self._preview)

            elif self._tool == TOOL_SHAPE:
                self._preview = ShapeItem(0, 0, self._shape_type)
                self._preview.setPos(pt)
                self._preview.setOpacity(0.65)
                self.scene().addItem(self._preview)

            elif self._tool == TOOL_LINE:
                # 1-inch snap for precise fractional measurements
                raw  = self.mapToScene(event.position().toPoint())
                pt1  = QPointF(round(raw.x()), round(raw.y())) if self._snap_enabled else raw
                self._preview = LineItem(pt1.x(), pt1.y(), pt1.x(), pt1.y(),
                                         style=self._line_style)
                self._preview.setOpacity(0.65)
                self.scene().addItem(self._preview)

            elif self._tool == TOOL_TEXT:
                text, ok = QInputDialog.getText(self, 'Add Text', 'Enter label:')
                if ok and text.strip():
                    item = TextItem(text.strip(), self._text_size)
                    item.setPos(pt)
                    self.scene().addItem(item)
                    item._layer_idx = self._active_layer
                    self._undo_stack.push(_AddCmd(self.scene(), item))
                self._drawing = False

            elif self._tool == TOOL_FIXTURE and self._fixture_type:
                item = FixtureItem(self._fixture_type)
                item.setPos(pt)
                item._layer_idx = self._active_layer
                self.scene().addItem(item)
                self._undo_stack.push(_AddCmd(self.scene(), item))
                self._drawing = False

            event.accept()

    def mouseMoveEvent(self, event):
        # select-mode left-drag pan (empty space)
        if (hasattr(self, '_sel_pan_last')
                and event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.position() - self._sel_pan_last
            self._sel_pan_last = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return

        # middle-mouse pan
        if (hasattr(self, '_pan_last')
                and event.buttons() & Qt.MouseButton.MiddleButton):
            delta = event.position() - self._pan_last
            self._pan_last = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return

        pt = self._snap_pt(self.mapToScene(event.position().toPoint()))
        self.status_message.emit(self._fmt_pos(pt))

        if self._drawing and self._preview:
            s = self._draw_start
            if self._tool == TOOL_ROOM:
                x = min(s.x(), pt.x())
                y = min(s.y(), pt.y())
                w = abs(pt.x() - s.x())
                h = abs(pt.y() - s.y())
                self._preview.setPos(x, y)
                self._preview.setRect(0, 0, w, h)
            elif self._tool == TOOL_WALL:
                ln = self._preview.line()
                self._preview.setLine(ln.x1(), ln.y1(), pt.x(), pt.y())

            elif self._tool == TOOL_DOOR:
                dx = pt.x() - self._draw_start.x()
                dy = pt.y() - self._draw_start.y()
                if math.hypot(dx, dy) > 1:
                    self._preview.setRotation(
                        math.degrees(math.atan2(dy, dx)))

            elif self._tool in (TOOL_WINDOW, TOOL_DIMENSION):
                rel = pt - self._draw_start
                self._preview.dx = rel.x()
                self._preview.dy = rel.y()
                self._preview.prepareGeometryChange()
                self._preview.update()

            elif self._tool == TOOL_JOIST:
                s = self._draw_start
                x = min(s.x(), pt.x())
                y = min(s.y(), pt.y())
                self._preview.setPos(x, y)
                self._preview.w = abs(pt.x() - s.x())
                self._preview.h = abs(pt.y() - s.y())
                self._preview.prepareGeometryChange()
                self._preview.update()

            elif self._tool == TOOL_SHAPE:
                s = self._draw_start
                x = min(s.x(), pt.x())
                y = min(s.y(), pt.y())
                self._preview.setPos(x, y)
                self._preview.w = abs(pt.x() - s.x())
                self._preview.h = abs(pt.y() - s.y())
                self._preview.prepareGeometryChange()
                self._preview.update()

            elif self._tool == TOOL_LINE:
                # 1-inch snap so fractional inch measurements are visible while drawing
                raw_pt = self.mapToScene(event.position().toPoint())
                pt_ln  = QPointF(round(raw_pt.x()), round(raw_pt.y())) if self._snap_enabled else raw_pt
                ln = self._preview.line()
                self._preview.setLine(ln.x1(), ln.y1(), pt_ln.x(), pt_ln.y())

        if self._tool == TOOL_SELECT:
            super().mouseMoveEvent(event)
        else:
            event.accept()

    def mouseReleaseEvent(self, event):
        # end select-mode left-drag pan
        if (event.button() == Qt.MouseButton.LeftButton
                and hasattr(self, '_sel_pan_last')):
            del self._sel_pan_last
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            if self._tool == TOOL_SELECT:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self._tool == TOOL_PAN:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            if hasattr(self, '_pan_last'):
                del self._pan_last
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            keep = False
            if self._preview:
                if self._tool == TOOL_ROOM:
                    r    = self._preview.rect()
                    keep = r.width() >= self._snap and r.height() >= self._snap
                elif self._tool == TOOL_WALL:
                    keep = self._preview.line().length() >= self._snap

                elif self._tool == TOOL_DOOR:
                    keep = True   # single-click placement

                elif self._tool in (TOOL_WINDOW, TOOL_DIMENSION):
                    keep = math.hypot(
                        self._preview.dx, self._preview.dy) >= self._snap

                elif self._tool == TOOL_JOIST:
                    keep = (self._preview.w >= self._snap and
                            self._preview.h >= self._snap)

                elif self._tool == TOOL_SHAPE:
                    keep = (self._preview.w >= self._snap and
                            self._preview.h >= self._snap)

                elif self._tool == TOOL_LINE:
                    keep = self._preview.line().length() >= self._snap

                if keep:
                    self._preview._layer_idx = self._active_layer
                    self._preview.setOpacity(1.0)
                    self._undo_stack.push(_AddCmd(self.scene(), self._preview))
                    if self._tool == TOOL_LINE:
                        self.set_tool(TOOL_SELECT)
                else:
                    self.scene().removeItem(self._preview)

            self._preview    = None
            self._drawing    = False
            self._draw_start = None
            event.accept()
            return

        if self._tool == TOOL_SELECT:
            super().mouseReleaseEvent(event)
            if self._move_origins:
                moved = [
                    (item, old, item.pos())
                    for item, old in self._move_origins.items()
                    if abs(item.pos().x()-old.x()) + abs(item.pos().y()-old.y()) > 0.01
                ]
                if moved:
                    self._undo_stack.push(_MoveCmd(moved))
                self._move_origins = {}

    def scrollContentsBy(self, dx: int, dy: int):
        super().scrollContentsBy(dx, dy)
        self.viewport_changed.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewport_changed.emit()

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        self.scale(factor, factor)
        self.viewport_changed.emit()

    def keyPressEvent(self, event):
        k    = event.key()
        mods = event.modifiers()

        # ── Arrow-key nudge ───────────────────────────────────────────────────
        _ARROW = {
            Qt.Key.Key_Left:  QPointF(-1,  0),
            Qt.Key.Key_Right: QPointF( 1,  0),
            Qt.Key.Key_Up:    QPointF( 0, -1),
            Qt.Key.Key_Down:  QPointF( 0,  1),
        }
        if k in _ARROW:
            sel = [i for i in self.scene().selectedItems()
                   if hasattr(i, 'to_dict')]
            if sel:
                # Shift = 1-inch fine step; otherwise snap increment
                step  = (1.0 if mods & Qt.KeyboardModifier.ShiftModifier
                         else self._snap)
                delta = _ARROW[k] * step
                data  = [(it, it.pos(), it.pos() + delta) for it in sel]
                self._undo_stack.push(_MoveCmd(data))
                event.accept()
                return

        if k in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected()
        elif k == Qt.Key.Key_Escape:
            if self._drawing and self._preview:
                self.scene().removeItem(self._preview)
                self._preview = None
                self._drawing = False
        else:
            super().keyPressEvent(event)

    def delete_selected(self):
        """Remove selected items via the undo stack."""
        items = list(self.scene().selectedItems())
        if items:
            self._undo_stack.push(_DeleteCmd(self.scene(), items))
    # ── Clipboard helpers ──────────────────────────────────────────────────────────

    def paste_items(self, dicts: list, offset_x: float = 24.0,
                    offset_y: float = 24.0) -> list:
        """Create items from serialized dicts with positional offset, push to undo stack."""
        loaders = {
            RoomItem.item_type:      RoomItem,
            WallItem.item_type:      WallItem,
            DoorItem.item_type:      DoorItem,
            WindowItem.item_type:    WindowItem,
            DimensionItem.item_type: DimensionItem,
            PostItem.item_type:      PostItem,
            JoistFillItem.item_type: JoistFillItem,
            ShapeItem.item_type:     ShapeItem,
            LineItem.item_type:      LineItem,
            TextItem.item_type:      TextItem,
            GroupItem.item_type:     GroupItem,
        }
        new_items = []
        self._undo_stack.beginMacro(f'Paste {len(dicts)} item(s)')
        for d in dicts:
            cls = loaders.get(d.get('type'))
            if cls:
                dc = dict(d)   # shallow copy
                dc['x'] = dc.get('x', 0) + offset_x
                dc['y'] = dc.get('y', 0) + offset_y
                item = cls.from_dict(dc)
                item.item_id   = str(uuid.uuid4())   # fresh id
                item._layer_idx = dc.get('layer_idx', 0)
                self.scene().addItem(item)
                self._undo_stack.push(_AddCmd(self.scene(), item))
                new_items.append(item)
        self._undo_stack.endMacro()
        # Select only pasted items
        for i in self.scene().items():
            i.setSelected(False)
        for item in new_items:
            item.setSelected(True)
        return new_items

    # ── Group / Ungroup ──────────────────────────────────────────────────────────────

    def group_selected(self):
        """Wrap all selected top-level CAD items into a GroupItem."""
        items = [
            i for i in self.scene().selectedItems()
            if hasattr(i, 'to_dict') and not isinstance(i.parentItem(), GroupItem)
        ]
        if len(items) < 2:
            return
        g = GroupItem()
        g._layer_idx = getattr(items[0], '_layer_idx', 0)
        self.scene().addItem(g)
        for item in items:
            g.addToGroup(item)
        self._undo_stack.push(_GroupCmd(self.scene(), items, g))
        for i in self.scene().selectedItems():
            i.setSelected(False)
        g.setSelected(True)

    def ungroup_selected(self):
        """Dissolve all selected GroupItems back to individual items."""
        groups = [i for i in self.scene().selectedItems()
                  if isinstance(i, GroupItem)]
        if not groups:
            return
        if len(groups) > 1:
            self._undo_stack.beginMacro(f'Ungroup {len(groups)} group(s)')
        for g in groups:
            children = [c for c in g.childItems() if hasattr(c, 'to_dict')]
            for child in list(g.childItems()):
                g.removeFromGroup(child)
                child.setSelected(True)
            self.scene().removeItem(g)
            self._undo_stack.push(_UngroupCmd(self.scene(), g, children))
        if len(groups) > 1:
            self._undo_stack.endMacro()

    # ── Layer management ──────────────────────────────────────────────────────────

    def get_layers(self) -> list:
        return list(self._layers)

    def set_active_layer(self, idx: int):
        if 0 <= idx < len(self._layers):
            self._active_layer = idx

    def add_layer(self, name: str = '') -> int:
        idx = len(self._layers)
        self._layers.append({'name': name or f'Layer {idx}',
                             'visible': True, 'locked': False})
        self.layers_changed.emit()
        return idx

    def delete_layer(self, idx: int):
        """Delete layer idx; items on it move to Layer 0.  Layer 0 is protected."""
        if len(self._layers) <= 1 or idx <= 0:
            return
        for item in self.scene().items():
            li = getattr(item, '_layer_idx', 0)
            if li == idx:
                item._layer_idx = 0
            elif li > idx:
                item._layer_idx = li - 1
        self._layers.pop(idx)
        if self._active_layer >= len(self._layers):
            self._active_layer = len(self._layers) - 1
        self.layers_changed.emit()

    def rename_layer(self, idx: int, name: str):
        if 0 <= idx < len(self._layers) and name.strip():
            self._layers[idx]['name'] = name.strip()
            self.layers_changed.emit()

    def set_layer_visible(self, idx: int, visible: bool):
        if 0 <= idx < len(self._layers):
            self._layers[idx]['visible'] = visible
            for item in self.scene().items():
                if getattr(item, '_layer_idx', 0) == idx:
                    item.setVisible(visible)

    def set_layer_locked(self, idx: int, locked: bool):
        if 0 <= idx < len(self._layers):
            self._layers[idx]['locked'] = locked
            for item in self.scene().items():
                if getattr(item, '_layer_idx', 0) == idx:
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
                                 not locked)
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                                 not locked)
    # ── Zoom helpers ──────────────────────────────────────────────────────────

    # ── Scale / page ──────────────────────────────────────────────────────────

    def set_scale(self, ratio: float):
        self.scale_ratio = float(ratio)
        self.scale_changed.emit(float(ratio))
        self.scene().update()
        self.viewport_changed.emit()

    def set_paper(self, w_in: float, h_in: float):
        self._paper_phys_w = float(w_in)
        self._paper_phys_h = float(h_in)
        self.scene().update()

    def set_show_page_boundary(self, visible: bool):
        self._show_page_boundary = visible
        self.scene().update()

    def zoom_fit(self):
        rect = self.scene().itemsBoundingRect()
        if rect.isEmpty():
            return
        rect.adjust(-GRID_MAJOR, -GRID_MAJOR, GRID_MAJOR, GRID_MAJOR)
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    # ── Project I/O ───────────────────────────────────────────────────────────

    def new_project(self):
        self.scene().clear()
        self._undo_stack.clear()
        self._layers = [{'name': 'Layer 0', 'visible': True, 'locked': False}]
        self._active_layer = 0
        self.layers_changed.emit()
        self.project_path = None

    def save_project(self, force_dialog: bool = False) -> bool:
        path = None if force_dialog else self.project_path

        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, 'Save Project', '',
                'ArchCAD Files (*.acad);;All Files (*)')
            if not path:
                return False
            if not path.endswith('.acad'):
                path += '.acad'

        items_data = []
        for item in self.scene().items():
            if hasattr(item, 'to_dict'):
                # Skip items that are children of a group (serialized inside it)
                if isinstance(item.parentItem(), GroupItem):
                    continue
                d = item.to_dict()
                d['layer_idx'] = getattr(item, '_layer_idx', 0)
                items_data.append(d)
        project = {
            'version':      2,
            'scale_ratio':  self.scale_ratio,
            'paper_w':      self._paper_phys_w,
            'paper_h':      self._paper_phys_h,
            'layers':       self._layers,
            'items':        items_data,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(project, f, indent=2)

        self.project_path = path
        return True

    def open_project(self) -> bool:
        path, _ = QFileDialog.getOpenFileName(
            self, 'Open Project', '',
            'ArchCAD Files (*.acad);;All Files (*)')
        if not path:
            return False

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.scene().clear()
        self._undo_stack.clear()
        # Restore page settings if present (v2+)
        if 'scale_ratio' in data:
            self.scale_ratio    = data['scale_ratio']
            self._paper_phys_w  = data.get('paper_w', 8.5)
            self._paper_phys_h  = data.get('paper_h', 11.0)
            self.scale_changed.emit(self.scale_ratio)
        # Restore layers
        self._layers = data.get('layers',
                                [{'name': 'Layer 0', 'visible': True, 'locked': False}])
        self._active_layer = 0
        loaders = {
            RoomItem.item_type:      RoomItem,
            WallItem.item_type:      WallItem,
            DoorItem.item_type:      DoorItem,
            WindowItem.item_type:    WindowItem,
            DimensionItem.item_type: DimensionItem,
            PostItem.item_type:      PostItem,
            JoistFillItem.item_type: JoistFillItem,
            ShapeItem.item_type:     ShapeItem,
            LineItem.item_type:      LineItem,
            TextItem.item_type:      TextItem,
            FixtureItem.item_type:   FixtureItem,
        }
        for d in data.get('items', []):
            if d.get('type') == GroupItem.item_type:
                g = GroupItem.from_dict(d)
                self.scene().addItem(g)
                for cd in d.get('children', []):
                    ccls = loaders.get(cd.get('type'))
                    if ccls:
                        child = ccls.from_dict(cd)
                        child._layer_idx = cd.get('layer_idx', 0)
                        g.addToGroup(child)
            else:
                cls = loaders.get(d.get('type'))
                if cls:
                    item = cls.from_dict(d)
                    item._layer_idx = d.get('layer_idx', 0)
                    self.scene().addItem(item)
        # Apply visibility and lock from restored layers
        for item in self.scene().items():
            idx = getattr(item, '_layer_idx', 0)
            if 0 <= idx < len(self._layers):
                if not self._layers[idx]['visible']:
                    item.setVisible(False)
                if self._layers[idx]['locked']:
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.layers_changed.emit()

        self.project_path = path
        return True

    # ── Auto post grid ────────────────────────────────────────────────────────

    def place_post_grid(self, origin_x: float, origin_y: float,
                        width: float, height: float,
                        spacing_x: float, spacing_y: float,
                        post_size: float):
        """Place a grid of posts at spacing_x / spacing_y intervals."""
        x = origin_x
        while x <= origin_x + width + 0.1:
            y = origin_y
            while y <= origin_y + height + 0.1:
                post = PostItem(post_size)
                post.setPos(x, y)
                self.scene().addItem(post)
                y += spacing_y
            x += spacing_x

    # ── Export ────────────────────────────────────────────────────────────────

    def export_png(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, 'Export PNG', '', 'PNG Images (*.png)')
        if not path:
            return False
        if not path.endswith('.png'):
            path += '.png'

        rect = self.scene().itemsBoundingRect()
        if rect.isEmpty():
            QMessageBox.information(self, 'Export', 'Nothing to export.')
            return False

        margin = GRID_MAJOR
        rect.adjust(-margin, -margin, margin, margin)

        scale = 3   # export at 3× resolution
        img = QImage(int(rect.width() * scale), int(rect.height() * scale),
                     QImage.Format.Format_ARGB32)
        img.fill(QColor('#ffffff'))

        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene().render(painter, source=rect)
        painter.end()

        img.save(path)
        QMessageBox.information(self, 'Export PNG', f'Saved:\n{path}')
        return True
