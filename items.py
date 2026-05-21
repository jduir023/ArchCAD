"""
ArchCAD — CAD item classes
Scene coordinate unit: 1 = 1 inch
Grid minor: 12 in = 1 ft  |  Grid major: 48 in = 4 ft
"""

import math
import uuid
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsLineItem, QGraphicsItem, QGraphicsItemGroup
from PyQt6.QtCore    import Qt, QRectF, QLineF, QPointF
from PyQt6.QtGui     import (QPen, QBrush, QColor, QPainterPath,
                              QPolygonF, QFont, QFontMetricsF, QUndoCommand)

# ── Colours / styles ──────────────────────────────────────────────────────────

WALL_COLOR  = QColor('#e0e8f0')
WALL_WIDTH  = 5          # cosmetic px

# Wall type registry:  key → (display_label, thickness_in_inches, color)
WALL_TYPES = {
    'interior':   ('Interior  (4")',    4.0,  QColor('#e0e8f0')),
    'exterior_6': ('Exterior  (6")',    6.0,  QColor('#c8d8f0')),
    'exterior_8': ('Exterior  (8")',    8.0,  QColor('#c8d8f0')),
    'structural': ('Structural (12")', 12.0,  QColor('#f0d0d0')),
}

ROOM_FILL   = QColor(40, 60, 95, 80)
ROOM_BORDER = QColor('#e0e8f0')
ROOM_BW     = 2          # cosmetic px

SEL_COLOR   = QColor('#ff6600')


# ── Selection highlight helper ────────────────────────────────────────────────

class _SelectableMixin:
    """Override paint to draw orange selection handles."""

    def _setup_base(self):
        self.item_id    = str(uuid.uuid4())
        self._layer_idx = 0
        self._locked    = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def set_locked(self, locked: bool):
        self._locked = locked
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not locked)


# ── Room (rectangle) ──────────────────────────────────────────────────────────

class RoomItem(_SelectableMixin, QGraphicsRectItem):
    item_type = 'room'

    def __init__(self, w: float = 0, h: float = 0):
        QGraphicsRectItem.__init__(self, 0, 0, w, h)
        self._setup_base()
        self.label = ''
        pen = QPen(ROOM_BORDER, ROOM_BW)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setBrush(QBrush(ROOM_FILL))

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        r = self.rect()
        p = self.pos()
        return {
            'type':  self.item_type,
            'id':    self.item_id,
            'x':     p.x(),
            'y':     p.y(),
            'w':     r.width(),
            'h':     r.height(),
            'label': self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'RoomItem':
        item = cls(d['w'], d['h'])
        item.item_id = d['id']
        item.label   = d.get('label', '')
        item.setPos(d['x'], d['y'])
        return item

    # ── info string for properties panel ──────────────────────────────────────

    def info_str(self) -> str:
        r = self.rect()
        w = r.width()  / 12
        h = r.height() / 12
        return f"Room\n  {_ft(w)} × {_ft(h)}"
    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        r  = self.rect()
        rw, rh = r.width(), r.height()
        font = QFont('Arial'); font.setPixelSize(9)
        painter.setFont(font)
        painter.setPen(QPen(QColor('#e0e8f0'), 0))
        if self.label:
            painter.drawText(
                QRectF(4, 4, rw - 8, rh - 8),
                Qt.AlignmentFlag.AlignCenter, self.label)
        _lbl(painter, f'{_ft(rw / 12)} \u00d7 {_ft(rh / 12)}', rw / 2, rh - 4)

# ── Wall (thick line) ─────────────────────────────────────────────────────────

class WallItem(_SelectableMixin, QGraphicsLineItem):
    item_type = 'wall'

    def __init__(self, x1: float = 0, y1: float = 0,
                 x2: float = 0, y2: float = 0,
                 wall_type: str = 'interior'):
        QGraphicsLineItem.__init__(self, x1, y1, x2, y2)
        self._setup_base()
        self.wall_type = wall_type
        self._apply_pen()

    def _apply_pen(self):
        _, thickness, color = WALL_TYPES.get(self.wall_type, WALL_TYPES['interior'])
        pen = QPen(color, thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        ln = self.line()
        p  = self.pos()
        return {
            'type':      self.item_type,
            'id':        self.item_id,
            'x1':        p.x() + ln.x1(),
            'y1':        p.y() + ln.y1(),
            'x2':        p.x() + ln.x2(),
            'y2':        p.y() + ln.y2(),
            'wall_type': self.wall_type,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'WallItem':
        item = cls(d['x1'], d['y1'], d['x2'], d['y2'],
                   wall_type=d.get('wall_type', 'interior'))
        item.item_id = d['id']
        return item

    # ── info string ───────────────────────────────────────────────────────────

    def info_str(self) -> str:
        ln     = self.line()
        p      = self.pos()
        length = QLineF(p.x() + ln.x1(), p.y() + ln.y1(),
                        p.x() + ln.x2(), p.y() + ln.y2()).length()
        label  = WALL_TYPES.get(self.wall_type, WALL_TYPES['interior'])[0]
        return f"Wall ({label})\n  {_ft(length / 12)} long"

    def boundingRect(self) -> QRectF:
        """Expand base rect to include the dimension label drawn above the line."""
        return super().boundingRect().adjusted(-4, -30, 4, 4)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        ln = self.line()
        mx = (ln.x1() + ln.x2()) / 2
        my = (ln.y1() + ln.y2()) / 2
        _lbl(painter, _ft(ln.length() / 12), mx, my - 6)


# ── Door ─────────────────────────────────────────────────────────────────────

class DoorItem(_SelectableMixin, QGraphicsItem):
    item_type     = 'door'
    DEFAULT_WIDTH = 36   # 3 ft

    def __init__(self, width: float = 36):
        QGraphicsItem.__init__(self)
        self._setup_base()
        self.door_width = float(width)

    def boundingRect(self) -> QRectF:
        w, m = self.door_width, 4
        # Panel (0,0)→(w,0); arc sweeps CCW to (0,−w)
        return QRectF(-m, -w - m, w + m * 2, w + m * 2)

    def paint(self, painter, option, widget=None):
        w   = self.door_width
        col = SEL_COLOR if self.isSelected() else QColor('#e0e8f0')
        pen = QPen(col, 2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Door panel (closed, pointing right)
        painter.drawLine(QLineF(0, 0, w, 0))
        # Swing arc: 0° → +90° CCW  →  (w,0) to (0,−w)  [upward on screen]
        path = QPainterPath()
        path.moveTo(w, 0)
        path.arcTo(QRectF(-w, -w, 2 * w, 2 * w), 0, 90)
        painter.drawPath(path)
        # Hinge dot
        painter.drawEllipse(QRectF(-3, -3, 6, 6))
        _lbl(painter, f'{int(w)}"', w / 2, 10)

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            'type':     self.item_type,
            'id':       self.item_id,
            'x':        p.x(), 'y': p.y(),
            'width':    self.door_width,
            'rotation': self.rotation(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'DoorItem':
        item = cls(d.get('width', cls.DEFAULT_WIDTH))
        item.item_id = d['id']
        item.setPos(d['x'], d['y'])
        item.setRotation(d.get('rotation', 0))
        return item

    def info_str(self) -> str:
        return f"Door\n  {_ft(self.door_width/12)} wide\n  Angle: {self.rotation():.0f}\u00b0"


# ── Window ────────────────────────────────────────────────────────────────────

class WindowItem(_SelectableMixin, QGraphicsItem):
    item_type = 'window'
    DEPTH     = 6   # wall thickness (inches)

    def __init__(self, dx: float = 36, dy: float = 0):
        QGraphicsItem.__init__(self)
        self._setup_base()
        self.dx = float(dx)
        self.dy = float(dy)

    def _corners(self):
        L = math.hypot(self.dx, self.dy)
        if L < 0.1:
            return None
        half       = self.DEPTH / 2
        ux, uy     = self.dx / L, self.dy / L
        px, py     = -uy * half,  ux * half
        c1 = QPointF(-px,          -py)
        c2 = QPointF(px,            py)
        c3 = QPointF(self.dx + px,  self.dy + py)
        c4 = QPointF(self.dx - px,  self.dy - py)
        return c1, c2, c3, c4

    def boundingRect(self) -> QRectF:
        L = math.hypot(self.dx, self.dy)
        if L < 0.1:
            return QRectF(-10, -10, 20, 20)
        half   = self.DEPTH / 2 + 4
        ux, uy = self.dx / L, self.dy / L
        px, py = -uy * half, ux * half
        xs = [0, self.dx, px, -px, self.dx + px, self.dx - px]
        ys = [0, self.dy, py, -py, self.dy + py, self.dy - py]
        m  = 4
        return QRectF(min(xs) - m, min(ys) - m,
                      max(xs) - min(xs) + m * 2,
                      max(ys) - min(ys) + m * 2)

    def paint(self, painter, option, widget=None):
        corners = self._corners()
        if not corners:
            return
        c1, c2, c3, c4 = corners
        col = SEL_COLOR if self.isSelected() else QColor('#e0e8f0')
        pen = QPen(col, 2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Outer rectangle  c1-c4-c3-c2
        poly = QPolygonF([c1, c4, c3, c2])
        painter.drawPolygon(poly)
        # Glass centre line
        glass = QPen(QColor('#90bce0') if not self.isSelected() else SEL_COLOR, 1)
        glass.setCosmetic(True)
        painter.setPen(glass)
        painter.drawLine(QLineF(0, 0, self.dx, self.dy))
        L = math.hypot(self.dx, self.dy)
        if L > 0:
            _lbl(painter, f'{int(round(L))}"', self.dx / 2, self.dy / 2)

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            'type': self.item_type,
            'id':   self.item_id,
            'x1':   p.x(),           'y1': p.y(),
            'x2':   p.x() + self.dx, 'y2': p.y() + self.dy,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'WindowItem':
        item = cls(d['x2'] - d['x1'], d['y2'] - d['y1'])
        item.item_id = d['id']
        item.setPos(d['x1'], d['y1'])
        return item

    def info_str(self) -> str:
        return f"Window\n  {_ft(math.hypot(self.dx, self.dy) / 12)} wide"


# ── Dimension ─────────────────────────────────────────────────────────────────

class DimensionItem(_SelectableMixin, QGraphicsItem):
    item_type = 'dimension'

    def __init__(self, dx: float = 120, dy: float = 0, offset: float = 24):
        QGraphicsItem.__init__(self)
        self._setup_base()
        self.dx     = float(dx)      # end point relative to item pos
        self.dy     = float(dy)
        self.offset = float(offset)  # perpendicular offset (inches)

    def boundingRect(self) -> QRectF:
        L = math.hypot(self.dx, self.dy)
        if L < 0.1:
            return QRectF(-30, -30, 60, 60)
        ux, uy = -self.dy / L, self.dx / L
        off    = abs(self.offset) + 30
        xs = [0, self.dx,
              ux * off, -ux * off,
              self.dx + ux * off, self.dx - ux * off]
        ys = [0, self.dy,
              uy * off, -uy * off,
              self.dy + uy * off, self.dy - uy * off]
        m  = 20
        return QRectF(min(xs) - m, min(ys) - m,
                      max(xs) - min(xs) + m * 2,
                      max(ys) - min(ys) + m * 2)

    def paint(self, painter, option, widget=None):
        L = math.hypot(self.dx, self.dy)
        if L < 0.1:
            return
        col = SEL_COLOR if self.isSelected() else QColor('#e0e8f0')
        pen = QPen(col, 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Perpendicular unit vector (offset direction)
        ux, uy = -self.dy / L, self.dx / L
        ox, oy = ux * self.offset, uy * self.offset

        # Dimension line endpoints
        e1x, e1y = ox,             oy
        e2x, e2y = self.dx + ox,   self.dy + oy
        overshoot, gap = 8, 3

        # Extension lines
        painter.drawLine(QLineF(ux * gap,              uy * gap,
                                e1x + ux * overshoot,  e1y + uy * overshoot))
        painter.drawLine(QLineF(self.dx + ux * gap,    self.dy + uy * gap,
                                e2x + ux * overshoot,  e2y + uy * overshoot))
        # Dimension line
        painter.drawLine(QLineF(e1x, e1y, e2x, e2y))

        # Tick marks (along the measured direction)
        tick = 5
        tx   = self.dx / L * tick
        ty   = self.dy / L * tick
        painter.drawLine(QLineF(e1x - tx, e1y - ty, e1x + tx, e1y + ty))
        painter.drawLine(QLineF(e2x - tx, e2y - ty, e2x + tx, e2y + ty))

        # Label
        label     = _ft(L / 12)
        mid_x     = (e1x + e2x) / 2
        mid_y     = (e1y + e2y) / 2
        angle_deg = math.degrees(math.atan2(self.dy, self.dx))
        if angle_deg > 90 or angle_deg <= -90:
            angle_deg += 180

        painter.save()
        painter.translate(mid_x, mid_y)
        painter.rotate(angle_deg)
        font = QFont('Arial')
        font.setPixelSize(9)
        painter.setFont(font)
        fm  = QFontMetricsF(font)
        tw  = fm.horizontalAdvance(label)
        painter.fillRect(QRectF(-tw / 2 - 2, -14, tw + 4, 12),
                         QColor(30, 37, 51, 230))
        painter.setPen(QPen(QColor('#ffffff'), 0))
        painter.drawText(QPointF(-tw / 2, -4), label)
        painter.restore()

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            'type':   self.item_type,
            'id':     self.item_id,
            'x1':     p.x(),           'y1': p.y(),
            'x2':     p.x() + self.dx, 'y2': p.y() + self.dy,
            'offset': self.offset,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'DimensionItem':
        item = cls(d['x2'] - d['x1'], d['y2'] - d['y1'], d.get('offset', 24))
        item.item_id = d['id']
        item.setPos(d['x1'], d['y1'])
        return item

    def info_str(self) -> str:
        return f"Dimension\n  {_ft(math.hypot(self.dx, self.dy) / 12)}"


# ── Post (structural column) ──────────────────────────────────────────────────

class PostItem(_SelectableMixin, QGraphicsItem):
    item_type = 'post'

    def __init__(self, size: float = 3.5):
        QGraphicsItem.__init__(self)
        self._setup_base()
        self.post_size = float(size)

    def boundingRect(self) -> QRectF:
        s, m = self.post_size, 4
        return QRectF(-s / 2 - m, -s / 2 - m, s + m * 2, s + m * 2)

    def paint(self, painter, option, widget=None):
        s   = self.post_size
        col = SEL_COLOR if self.isSelected() else QColor('#5a3a10')
        pen = QPen(col, 1.5)
        pen.setCosmetic(True)
        fill = QColor(180, 130, 60, 200) if not self.isSelected() else SEL_COLOR
        painter.setPen(pen)
        painter.setBrush(QBrush(fill))
        painter.drawRect(QRectF(-s / 2, -s / 2, s, s))
        # Diagonal cross (standard architectural post symbol)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QLineF(-s / 2, -s / 2,  s / 2,  s / 2))
        painter.drawLine(QLineF( s / 2, -s / 2, -s / 2,  s / 2))
        _lbl(painter, f'{s}"', 0, s / 2 + 10)

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            'type': self.item_type,
            'id':   self.item_id,
            'x':    p.x(), 'y': p.y(),
            'size': self.post_size,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'PostItem':
        item = cls(d.get('size', 3.5))
        item.item_id = d['id']
        item.setPos(d['x'], d['y'])
        return item

    def info_str(self) -> str:
        return f"Post\n  {self.post_size:.2f}\" sq"


# ── Joist fill (floor/ceiling framing pattern) ────────────────────────────────

class JoistFillItem(_SelectableMixin, QGraphicsItem):
    item_type = 'joist_fill'

    def __init__(self, w: float = 120, h: float = 96,
                 spacing: float = 16, direction: str = 'h'):
        QGraphicsItem.__init__(self)
        self._setup_base()
        self.w         = float(w)          # region width  (always >= 0)
        self.h         = float(h)          # region height (always >= 0)
        self.spacing   = float(spacing)    # centre-to-centre, inches
        self.direction = direction         # 'h' = horiz joists, 'v' = vert

    def boundingRect(self) -> QRectF:
        m = 4
        return QRectF(-m, -m, self.w + m * 2, self.h + m * 2)

    def paint(self, painter, option, widget=None):
        if self.w < 1 or self.h < 1:
            return
        col = SEL_COLOR if self.isSelected() else QColor('#e0e8f0')

        # Dashed bounding rectangle
        pen = QPen(col, 1)
        pen.setCosmetic(True)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(40, 60, 95, 30)))
        painter.drawRect(QRectF(0, 0, self.w, self.h))

        # Joist lines
        jpen = QPen(col, 1)
        jpen.setCosmetic(True)
        painter.setPen(jpen)
        sp = max(self.spacing, 1)
        if self.direction == 'h':
            y = sp
            while y < self.h:
                painter.drawLine(QLineF(0, y, self.w, y))
                y += sp
        else:
            x = sp
            while x < self.w:
                painter.drawLine(QLineF(x, 0, x, self.h))
                x += sp

        # Label
        sp_str  = f'{sp:.4g}"'
        dir_str = 'Horiz' if self.direction == 'h' else 'Vert'
        label   = f'{sp_str} o.c.  {dir_str}'
        lpen = QPen(col, 0)
        painter.setPen(lpen)
        font = QFont('Arial')
        font.setPixelSize(8)
        painter.setFont(font)
        painter.drawText(QPointF(4, 10), label)

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            'type':      self.item_type,
            'id':        self.item_id,
            'x':         p.x(), 'y': p.y(),
            'w':         self.w, 'h': self.h,
            'spacing':   self.spacing,
            'direction': self.direction,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'JoistFillItem':
        item = cls(d['w'], d['h'], d.get('spacing', 16), d.get('direction', 'h'))
        item.item_id = d['id']
        item.setPos(d['x'], d['y'])
        return item

    def info_str(self) -> str:
        sp     = self.spacing
        label  = f'{sp:.4g}"'
        dir_l  = 'Horiz' if self.direction == 'h' else 'Vert'
        region = f"{_ft(self.w/12)} × {_ft(self.h/12)}"
        return f"Joist Fill\n  {label} o.c.  {dir_l}\n  Region: {region}"


# ── Shape (rectangle / ellipse) ───────────────────────────────────────────────

class ShapeItem(_SelectableMixin, QGraphicsItem):
    item_type = 'shape'

    def __init__(self, w: float = 0, h: float = 0,
                 shape_type: str = 'rect',
                 fill: str = '#2a3f5f', border: str = '#e0e8f0'):
        QGraphicsItem.__init__(self)
        self._setup_base()
        self.w          = float(w)
        self.h          = float(h)
        self.shape_type = shape_type   # 'rect' or 'ellipse'
        self.fill       = fill
        self.border     = border

    def boundingRect(self) -> QRectF:
        m = 4
        return QRectF(-m, -m, self.w + m * 2, self.h + m * 2)

    def paint(self, painter, option, widget=None):
        if self.w < 1 or self.h < 1:
            return
        b_col = SEL_COLOR if self.isSelected() else QColor(self.border)
        pen   = QPen(b_col, 1.5)
        pen.setCosmetic(True)
        painter.setPen(pen)
        f_col = QColor(self.fill)
        f_col.setAlpha(180)
        painter.setBrush(QBrush(f_col))
        r = QRectF(0, 0, self.w, self.h)
        if self.shape_type == 'ellipse':
            painter.drawEllipse(r)
        else:
            painter.drawRect(r)
        _lbl(painter, f'{_ft(self.w / 12)} \u00d7 {_ft(self.h / 12)}',
             self.w / 2, self.h / 2)

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            'type':       self.item_type,
            'id':         self.item_id,
            'x':          p.x(), 'y': p.y(),
            'w':          self.w, 'h': self.h,
            'shape_type': self.shape_type,
            'fill':       self.fill,
            'border':     self.border,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ShapeItem':
        item = cls(d['w'], d['h'],
                   shape_type=d.get('shape_type', 'rect'),
                    fill=d.get('fill', '#2a3f5f'),
                    border=d.get('border', '#e0e8f0'))
        item.item_id = d['id']
        item.setPos(d['x'], d['y'])
        return item

    def info_str(self) -> str:
        t = 'Rectangle' if self.shape_type == 'rect' else 'Ellipse'
        return f"{t}\n  {_ft(self.w / 12)} × {_ft(self.h / 12)}"


# ── Line-resize undo command ─────────────────────────────────────────────────

class _LineResizeCmd(QUndoCommand):
    def __init__(self, item, old_ln: QLineF, new_ln: QLineF, parent=None):
        super().__init__('Resize line', parent)
        self._item = item
        self._old  = old_ln
        self._new  = new_ln

    def undo(self): self._item.setLine(self._old)
    def redo(self): self._item.setLine(self._new)


# ── Decorative Line ───────────────────────────────────────────────────────────

class LineItem(_SelectableMixin, QGraphicsLineItem):
    item_type = 'line'

    def __init__(self, x1: float = 0, y1: float = 0,
                 x2: float = 0, y2: float = 0,
                 color: str = '#e0e8f0', style: str = 'solid'):
        QGraphicsLineItem.__init__(self, x1, y1, x2, y2)
        self._setup_base()
        self.line_color   = color
        self.line_style   = style   # 'solid', 'dash', 'dot'
        self._drag_handle = 0       # 0=none, 1=p1, 2=p2
        self._line_before = None    # QLineF snapshot before drag
        self._apply_pen()

    def _apply_pen(self):
        _styles = {
            'solid': Qt.PenStyle.SolidLine,
            'dash':  Qt.PenStyle.DashLine,
            'dot':   Qt.PenStyle.DotLine,
        }
        pen = QPen(QColor(self.line_color), 1.5)
        pen.setCosmetic(True)
        pen.setStyle(_styles.get(self.line_style, Qt.PenStyle.SolidLine))
        self.setPen(pen)

    def boundingRect(self) -> QRectF:
        """Expand base rect to include the label above and endpoint handles."""
        return super().boundingRect().adjusted(-10, -30, 10, 10)

    def _handle_r(self) -> float:
        """Endpoint handle radius in local (scene) units ≈ 7 screen px."""
        if self.scene() and self.scene().views():
            m11 = max(0.01, self.scene().views()[0].transform().m11())
        else:
            m11 = 2.0
        return 7.0 / m11

    def shape(self) -> QPainterPath:
        path = super().shape()
        ln   = self.line()
        path.addEllipse(ln.p1(), 8.0, 8.0)   # fixed hit radius, no view query
        path.addEllipse(ln.p2(), 8.0, 8.0)
        return path

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            r  = self._handle_r() * 1.8   # slightly forgiving
            ln = self.line()
            ep = event.pos()
            d1 = (ep - ln.p1()).manhattanLength()
            d2 = (ep - ln.p2()).manhattanLength()
            if d1 <= r and d1 <= d2:
                self._drag_handle = 1
                self._line_before = QLineF(ln)
                event.accept()
                return
            if d2 <= r:
                self._drag_handle = 2
                self._line_before = QLineF(ln)
                event.accept()
                return
        self._drag_handle = 0
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_handle:
            ln  = self.line()
            pt  = event.pos()
            # snap dragged point to grid if canvas snap is on
            if self.scene() and self.scene().views():
                view = self.scene().views()[0]
                if getattr(view, '_snap_enabled', False):
                    # 1-inch snap for line endpoints (allows fractional measurements)
                    spt = self.mapToScene(pt)
                    spt = QPointF(round(spt.x()), round(spt.y()))
                    pt  = self.mapFromScene(spt)
            if self._drag_handle == 1:
                self.setLine(QLineF(pt, ln.p2()))
            else:
                self.setLine(QLineF(ln.p1(), pt))
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_handle and event.button() == Qt.MouseButton.LeftButton:
            old_ln = self._line_before
            new_ln = self.line()
            if old_ln and old_ln != new_ln:
                if self.scene() and self.scene().views():
                    view = self.scene().views()[0]
                    if hasattr(view, '_undo_stack'):
                        view._undo_stack.push(
                            _LineResizeCmd(self, old_ln, new_ln))
            self._drag_handle = 0
            self._line_before = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        ln = self.line()
        L  = ln.length()
        if L > 0.1:
            _lbl(painter, _ft(L / 12),
                 (ln.x1() + ln.x2()) / 2,
                 (ln.y1() + ln.y2()) / 2 - 6)
        if self.isSelected():
            r  = self._handle_r()
            hp = QPen(QColor('#ff6600'), 1.5)
            hp.setCosmetic(True)
            painter.save()
            painter.setPen(hp)
            painter.setBrush(QBrush(QColor('#ff9933')))
            painter.drawEllipse(ln.p1(), r, r)
            painter.drawEllipse(ln.p2(), r, r)
            painter.restore()

    def to_dict(self) -> dict:
        ln = self.line()
        p  = self.pos()
        return {
            'type':       self.item_type,
            'id':         self.item_id,
            'x1':         p.x() + ln.x1(), 'y1': p.y() + ln.y1(),
            'x2':         p.x() + ln.x2(), 'y2': p.y() + ln.y2(),
            'line_color': self.line_color,
            'line_style': self.line_style,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'LineItem':
        item = cls(d['x1'], d['y1'], d['x2'], d['y2'],
                    color=d.get('line_color', '#e0e8f0'),
                   style=d.get('line_style', 'solid'))
        item.item_id = d['id']
        return item

    def info_str(self) -> str:
        ln = self.line()
        p  = self.pos()
        L  = QLineF(p.x() + ln.x1(), p.y() + ln.y1(),
                    p.x() + ln.x2(), p.y() + ln.y2()).length()
        return f"Line ({self.line_style})\n  {_ft(L / 12)} long"


# ── Text label ────────────────────────────────────────────────────────────────

class TextItem(_SelectableMixin, QGraphicsItem):
    item_type = 'text'

    def __init__(self, text: str = 'Text', font_size: int = 12,
                 color: str = '#e8edf3'):
        QGraphicsItem.__init__(self)
        self._setup_base()
        self.text      = text
        self.font_size = int(font_size)
        self.color     = color

    def _font(self) -> QFont:
        f = QFont('Arial')
        f.setPointSize(self.font_size)
        return f

    def boundingRect(self) -> QRectF:
        fm = QFontMetricsF(self._font())
        return QRectF(0, 0, fm.horizontalAdvance(self.text) + 10, fm.height() + 8)

    def paint(self, painter, option, widget=None):
        col = SEL_COLOR if self.isSelected() else QColor(self.color)
        if self.isSelected():
            painter.fillRect(self.boundingRect(), QColor(255, 200, 80, 55))
        painter.setFont(self._font())
        painter.setPen(QPen(col, 0))
        fm = QFontMetricsF(self._font())
        painter.drawText(QPointF(4, fm.ascent() + 4), self.text)

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            'type':      self.item_type,
            'id':        self.item_id,
            'x':         p.x(), 'y': p.y(),
            'text':      self.text,
            'font_size': self.font_size,
            'color':     self.color,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'TextItem':
        item = cls(d.get('text', 'Text'), d.get('font_size', 12),
                   d.get('color', '#e8edf3'))
        item.item_id = d['id']
        item.setPos(d['x'], d['y'])
        return item

    def info_str(self) -> str:
        preview = self.text[:20] + ('…' if len(self.text) > 20 else '')
        return f"Text  {self.font_size}pt\n  \"{preview}\""


# ── Helpers ───────────────────────────────────────────────────────────────────


class GroupItem(QGraphicsItemGroup):
    """Container that groups multiple CAD items into a single movable unit."""
    item_type = 'group'

    def __init__(self):
        super().__init__()
        self.item_id    = str(uuid.uuid4())
        self._layer_idx = 0
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,    True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def to_dict(self) -> dict:
        children = []
        for child in self.childItems():
            if hasattr(child, 'to_dict'):
                d = child.to_dict()
                d['layer_idx'] = getattr(child, '_layer_idx', 0)
                children.append(d)
        return {
            'type':      self.item_type,
            'id':        self.item_id,
            'x':         self.pos().x(),
            'y':         self.pos().y(),
            'layer_idx': self._layer_idx,
            'children':  children,
        }

    @staticmethod
    def from_dict(d: dict) -> 'GroupItem':
        g = GroupItem()
        g.item_id    = d.get('id', str(uuid.uuid4()))
        g._layer_idx = d.get('layer_idx', 0)
        g.setPos(d.get('x', 0), d.get('y', 0))
        return g

    def info_str(self) -> str:
        n = sum(1 for c in self.childItems() if hasattr(c, 'to_dict'))
        return f'Group ({n} item{"s" if n != 1 else ""})'


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ft(feet: float) -> str:
    """Format to nearest 1/8": e.g. 12' 6 1/4"  |  6 3/8"  |  22'"""
    total_in_f = abs(feet) * 12
    sign       = '-' if feet < 0 else ''

    eighths  = round(total_in_f * 8)   # total measurement in 1/8-inch units
    whole_in = eighths // 8            # whole inches
    rem8     = eighths % 8             # fractional part (0-7 eighths)

    ft   = whole_in // 12
    inch = whole_in % 12

    # Build reduced fraction string  e.g. rem8=2 → "1/4"
    if rem8:
        g    = math.gcd(rem8, 8)
        frac = f'{rem8 // g}/{8 // g}'
    else:
        frac = ''

    if ft == 0:
        if inch == 0:
            return f'{sign}{frac}"' if frac else '0"'
        if frac:
            return f'{sign}{inch} {frac}"'
        return f'{sign}{inch}"'
    else:
        if inch == 0 and not frac:
            return f"{sign}{ft}'"
        if inch == 0:
            return f"{sign}{ft}' 0 {frac}\""
        if not frac:
            return f"{sign}{ft}' {inch}\""
        return f"{sign}{ft}' {inch} {frac}\""


# ── _lbl helpers (font created once; metrics always from painter for correct scale) ──
_LBL_FONT: 'QFont | None' = None
_LBL_BG    = QColor(20, 28, 42, 210)
_LBL_PEN   = QPen(QColor('#ffffff'), 0)


def _lbl(painter, text: str, cx: float, cy: float) -> None:
    """Draw a compact dimension tag centred at (cx, cy) in scene coords.
    Uses painter.fontMetrics() so sizes are always in the current scene-unit space."""
    global _LBL_FONT
    if _LBL_FONT is None:
        _LBL_FONT = QFont('Arial')
        _LBL_FONT.setPixelSize(9)
    painter.save()
    painter.setFont(_LBL_FONT)
    fm = painter.fontMetrics()          # scene-coordinate metrics (zoom-aware)
    tw = fm.horizontalAdvance(text)
    th = fm.height()
    painter.fillRect(QRectF(cx - tw / 2 - 2, cy - th, tw + 4, th + 2), _LBL_BG)
    painter.setPen(_LBL_PEN)
    painter.drawText(QPointF(cx - tw / 2, cy), text)
    painter.restore()
