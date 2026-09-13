"""
ArchCAD — Fixture & Symbol Library
88 architectural symbols across 10 categories.
All dimensions in inches (scene units).  Top-down plan view.
"""

import math
import random
import uuid

from PyQt6.QtCore    import Qt, QRectF, QPointF, QLineF
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui     import (QPen, QBrush, QColor, QPainterPath,
                              QPolygonF, QFont)

import items as _items
from items import _SelectableMixin, _RotatableMixin, SEL_COLOR, _ft

# ── Colour palette ─────────────────────────────────────────────────────────────
_FG    = QColor('#c8d8f0')
_FG2   = QColor('#7a9abf')
_FILL  = QColor(38,  52,  80,  220)
_FILL2 = QColor(22,  34,  58,  240)
_FILL3 = QColor(60,  85, 130,  180)
_ELEC  = QColor('#e8c840')
_HVAC  = QColor('#50c8e8')
_PLUM  = QColor('#5090e0')
_INSUL = QColor('#e89840')
_STRUC = QColor('#b87050')

# ── Pen / brush helpers ────────────────────────────────────────────────────────
def _pen(sel, w=1.5, c=None):
    if sel:
        col = SEL_COLOR
    elif _items.PRINT_MODE:
        col = QColor('#111111')
    else:
        col = c or _FG
    p = QPen(col, w)
    p.setCosmetic(True); return p

def _pen2(sel, w=0.8, c=None):
    if sel:
        col = SEL_COLOR
    elif _items.PRINT_MODE:
        col = QColor('#333333')
    else:
        col = c or _FG2
    p = QPen(col, w)
    p.setCosmetic(True); return p

def _br(c=None):
    if _items.PRINT_MODE:
        fill = QColor(c) if c is not None else QColor(230, 230, 230, 80)
        fill.setAlpha(60)
        return QBrush(fill)
    return QBrush(c or _FILL)

# ── Common drawing primitives ─────────────────────────────────────────────────
def _rect(p, x, y, w, h, sel, fill=None, r=0):
    p.setPen(_pen(sel)); p.setBrush(_br(fill))
    if r: p.drawRoundedRect(QRectF(x, y, w, h), r, r)
    else: p.drawRect(QRectF(x, y, w, h))

def _basin(p, x, y, bw, bh, sel, r=3):
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL2))
    p.drawRoundedRect(QRectF(x, y, bw, bh), r, r)

def _drain(p, cx, cy, sel, r=2.5):
    p.setPen(_pen2(sel)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))

def _burner(p, cx, cy, sel, r=5.5):
    p.setBrush(Qt.BrushStyle.NoBrush)
    for fr in (1.0, 0.55, 0.22):
        p.setPen(_pen2(sel, 0.8 if fr < 1 else 1.2))
        rr = r * fr
        p.drawEllipse(QRectF(cx-rr, cy-rr, rr*2, rr*2))

def _text_label(p, text, cx, cy, sel, sz=7):
    p.save()
    f = QFont('Arial'); f.setPixelSize(sz)
    p.setFont(f)
    p.setPen(_pen2(sel))
    p.drawText(QRectF(cx-20, cy-sz//2, 40, sz+2), Qt.AlignmentFlag.AlignCenter, text)
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  KITCHEN
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_sink_single(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    bm = max(2.5, w * 0.11)
    _basin(p, bm, bm*1.4, w-2*bm, h-bm*2.2, sel)
    _drain(p, w/2, h*0.55, sel)
    # faucet
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL3))
    p.drawEllipse(QRectF(w/2-2.5, bm*0.35, 5, 5))
    p.restore()

def _draw_sink_double(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    bm = max(2, h * 0.12)
    bw = (w - 3*bm) / 2
    for bx in (bm, bm*2 + bw):
        _basin(p, bx, bm*1.3, bw, h-bm*2, sel)
        _drain(p, bx + bw/2, h*0.55, sel)
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL3))
    p.drawEllipse(QRectF(w/2-2.5, bm*0.35, 5, 5))
    p.restore()

def _draw_sink_farmhouse(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    bm = 2.5
    _basin(p, bm, bm, w-2*bm, h-bm*2, sel, r=2)
    _drain(p, w/2, h*0.55, sel)
    # apron front line
    p.setPen(_pen(sel, 2.5))
    p.drawLine(QLineF(0, h*0.9, w, h*0.9))
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL3))
    p.drawEllipse(QRectF(w/2-2.5, bm*0.35, 5, 5))
    p.restore()

def _draw_fridge_std(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # door line
    p.setPen(_pen2(sel))
    p.drawLine(QLineF(0, h*0.08, w, h*0.08))
    # handle
    p.setPen(_pen(sel, 2.5))
    p.drawLine(QLineF(w*0.15, h*0.04, w*0.85, h*0.04))
    _text_label(p, 'FRIDGE', w/2, h*0.55, sel, 8)
    p.restore()

def _draw_fridge_sbs(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    mid = w / 2
    p.setPen(_pen2(sel))
    p.drawLine(QLineF(mid, 0, mid, h))
    # handles
    p.setPen(_pen(sel, 2.5))
    p.drawLine(QLineF(w*0.08, h*0.04, mid*0.85, h*0.04))
    p.drawLine(QLineF(mid*1.15, h*0.04, w*0.92, h*0.04))
    _text_label(p, 'FRIDGE', w/2, h*0.55, sel, 7)
    p.restore()

def _draw_range_4b(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # front panel
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(0, h*0.82, w, h*0.18))
    # 4 burners  (2×2)
    xs = [w*0.28, w*0.72]
    ys = [h*0.27, h*0.65]
    for cx in xs:
        for cy in ys:
            _burner(p, cx, cy, sel, r=w*0.12)
    p.restore()

def _draw_range_6b(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(0, h*0.82, w, h*0.18))
    xs = [w*0.2, w*0.5, w*0.8]
    ys = [h*0.27, h*0.62]
    for cx in xs:
        for cy in ys:
            _burner(p, cx, cy, sel, r=w*0.09)
    p.restore()

def _draw_dishwasher(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # basket grid lines
    p.setPen(_pen2(sel))
    for i in range(1, 4):
        p.drawLine(QLineF(w*0.1, h*i*0.25, w*0.9, h*i*0.25))
    # handle
    p.setPen(_pen(sel, 2))
    p.drawLine(QLineF(w*0.2, h*0.06, w*0.8, h*0.06))
    _text_label(p, 'DW', w/2, h*0.88, sel, 7)
    p.restore()

def _draw_microwave(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # door panel
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(w*0.05, h*0.1, w*0.7, h*0.8))
    # control panel
    p.setBrush(_br(_FILL))
    p.drawRect(QRectF(w*0.77, h*0.1, w*0.18, h*0.8))
    _text_label(p, 'MW', w*0.38, h*0.5, sel, 7)
    p.restore()

def _draw_oven_wall(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # oven window
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL3))
    p.drawRect(QRectF(w*0.15, h*0.25, w*0.7, h*0.35))
    # handle
    p.setPen(_pen(sel, 2.5))
    p.drawLine(QLineF(w*0.2, h*0.16, w*0.8, h*0.16))
    _text_label(p, 'OVEN', w/2, h*0.82, sel, 7)
    p.restore()

def _draw_cooktop_4(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    xs = [w*0.27, w*0.73]
    ys = [h*0.28, h*0.72]
    for cx in xs:
        for cy in ys:
            _burner(p, cx, cy, sel, r=w*0.12)
    p.restore()

def _draw_hood_vent(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # vent chevron
    p.setPen(_pen(sel, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(w*0.1, h*0.85)
    path.lineTo(w*0.5, h*0.15)
    path.lineTo(w*0.9, h*0.85)
    p.drawPath(path)
    # fan circle
    p.drawEllipse(QRectF(w*0.35, h*0.35, w*0.3, w*0.3))
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  BATHROOM
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_toilet(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h*0.3, sel, fill=_FILL2)      # tank
    # bowl (oval)
    p.setPen(_pen(sel)); p.setBrush(_br(_FILL3))
    p.drawEllipse(QRectF(w*0.05, h*0.3, w*0.9, h*0.68))
    # seat outline
    p.setPen(_pen2(sel)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(w*0.1, h*0.34, w*0.8, h*0.56))
    p.restore()

def _draw_toilet_tankless(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h*0.12, sel, fill=_FILL2)     # very thin profile
    p.setPen(_pen(sel)); p.setBrush(_br(_FILL3))
    p.drawEllipse(QRectF(w*0.05, h*0.1, w*0.9, h*0.88))
    p.setPen(_pen2(sel)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(w*0.1, h*0.15, w*0.8, h*0.75))
    p.restore()

def _draw_vanity_single(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # sink basin (oval)
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL2))
    bm = min(w, h) * 0.12
    p.drawEllipse(QRectF(bm, bm, w-2*bm, h-2*bm))
    _drain(p, w/2, h/2, sel)
    p.restore()

def _draw_vanity_double(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    bm = h * 0.12
    bw = (w - 3*bm) / 2
    for bx in (bm, bm*2 + bw):
        p.setPen(_pen2(sel)); p.setBrush(_br(_FILL2))
        p.drawEllipse(QRectF(bx, bm, bw, h-2*bm))
        _drain(p, bx+bw/2, h/2, sel)
    # center line
    p.setPen(_pen2(sel)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(w/2, 0, w/2, h))
    p.restore()

def _draw_bathtub(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    apron = min(w, h) * 0.07
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL3))
    p.drawRect(QRectF(apron, apron, w-2*apron, h-2*apron))
    # tub oval
    p.setPen(_pen2(sel, 0.8)); p.setBrush(Qt.BrushStyle.NoBrush)
    inner = apron * 1.8
    p.drawEllipse(QRectF(inner, h*0.12, w-2*inner, h*0.72))
    _drain(p, w/2, h*0.82, sel)
    p.restore()

def _draw_bathtub_corner(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # angled front edge
    p.setPen(_pen(sel, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(0, h, w, 0))
    # inner oval
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL3))
    p.drawEllipse(QRectF(w*0.15, h*0.15, w*0.65, h*0.65))
    _drain(p, w*0.8, h*0.8, sel)
    p.restore()

def _draw_shower_stall(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # glass door gap (front edge)
    p.setPen(_pen2(sel))
    p.drawLine(QLineF(0, h*0.75, w*0.35, h))
    p.drawLine(QLineF(w*0.35, h, w, h))
    # diagonal X (glass)
    p.setPen(_pen2(sel, 0.8))
    p.drawLine(QLineF(0, 0, w, h))
    p.drawLine(QLineF(w, 0, 0, h))
    _drain(p, w/2, h/2, sel, r=3)
    p.restore()

def _draw_shower_corner(p, w, h, sel):
    p.save()
    # corner triangle
    poly = QPolygonF([QPointF(0, 0), QPointF(w, 0), QPointF(0, h)])
    p.setPen(_pen(sel)); p.setBrush(_br())
    p.drawPolygon(poly)
    # door arc
    path = QPainterPath()
    path.moveTo(w, 0)
    path.arcTo(QRectF(0, 0, w*2, h*2), 90, -90)
    p.setPen(_pen2(sel)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)
    _drain(p, w*0.3, h*0.3, sel, r=3)
    p.restore()

def _draw_bidet(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h*0.2, sel, fill=_FILL2)
    p.setPen(_pen(sel)); p.setBrush(_br(_FILL3))
    p.drawEllipse(QRectF(w*0.05, h*0.18, w*0.9, h*0.8))
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  BEDROOM / FURNITURE
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_bed(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # headboard
    p.setPen(QPen(SEL_COLOR if sel else _FG, 4.0)); p.pen().setCosmetic(True)
    hb = QPen(SEL_COLOR if sel else _FG, 4.0); hb.setCosmetic(True)
    p.setPen(hb); p.drawLine(QLineF(0, 0, w, 0))
    # pillows
    pm = w * 0.08
    ph = h * 0.12
    pw = (w - 3*pm) / 2
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL3))
    p.drawRoundedRect(QRectF(pm, pm, pw, ph), 2, 2)
    p.drawRoundedRect(QRectF(pm*2+pw, pm, pw, ph), 2, 2)
    # blanket fold
    p.setPen(_pen2(sel)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(0, pm*2+ph, w, pm*2+ph))
    p.restore()

def _draw_nightstand(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    p.setPen(_pen2(sel))
    p.drawLine(QLineF(0, h/2, w, h/2))  # drawer line
    # knob
    _drain(p, w/2, h*0.3, sel, r=1.5)
    _drain(p, w/2, h*0.73, sel, r=1.5)
    p.restore()

def _draw_dresser(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    n = 3
    dh = h / n
    for i in range(1, n):
        p.setPen(_pen2(sel))
        p.drawLine(QLineF(0, dh*i, w, dh*i))
    for i in range(n):
        _drain(p, w/2, dh*(i+0.5), sel, r=1.5)
    p.restore()

def _draw_wardrobe(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    mid = w/2
    p.setPen(_pen2(sel))
    p.drawLine(QLineF(mid, 0, mid, h))
    # door arcs
    path = QPainterPath()
    path.moveTo(0, 0); path.arcTo(QRectF(-mid, 0, mid*2, h), 0, -90)
    p.setBrush(Qt.BrushStyle.NoBrush); p.drawPath(path)
    path2 = QPainterPath()
    path2.moveTo(w, 0); path2.arcTo(QRectF(mid, 0, mid*2, h), 180, 90)
    p.drawPath(path2)
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  LIVING / DINING
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_sofa(p, w, h, sel, seats=2):
    p.save()
    # back cushion (top)
    _rect(p, 0, 0, w, h*0.3, sel, fill=_FILL2)
    # seat base
    _rect(p, 0, h*0.3, w, h*0.7, sel)
    # seat dividers
    sw = w / seats
    for i in range(1, seats):
        p.setPen(_pen2(sel))
        p.drawLine(QLineF(sw*i, h*0.3, sw*i, h))
    # arm rests
    p.setPen(_pen(sel)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(0, h*0.3, w*0.08, h*0.7))
    p.drawRect(QRectF(w*0.92, h*0.3, w*0.08, h*0.7))
    p.restore()

def _draw_armchair(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h*0.3, sel, fill=_FILL2)
    _rect(p, 0, h*0.3, w, h*0.7, sel)
    p.setPen(_pen(sel)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(0, h*0.3, w*0.12, h*0.7))
    p.drawRect(QRectF(w*0.88, h*0.3, w*0.12, h*0.7))
    p.restore()

def _draw_coffee_table(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # inset glass top
    mg = min(w, h) * 0.1
    p.setPen(_pen2(sel, 0.8)); p.setBrush(_br(_FILL3))
    p.drawRect(QRectF(mg, mg, w-2*mg, h-2*mg))
    p.restore()

def _draw_coffee_table_round(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel)); p.setBrush(_br())
    p.drawEllipse(QRectF(0, 0, w, h))
    mg = min(w, h) * 0.1
    p.setPen(_pen2(sel, 0.8)); p.setBrush(_br(_FILL3))
    p.drawEllipse(QRectF(mg, mg, w-2*mg, h-2*mg))
    p.restore()

def _draw_tv_unit(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # screen rectangle
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(w*0.05, h*0.1, w*0.9, h*0.7))
    # TV stand bars
    p.setPen(_pen(sel, 2))
    p.drawLine(QLineF(w*0.35, h*0.82, w*0.35, h))
    p.drawLine(QLineF(w*0.65, h*0.82, w*0.65, h))
    p.restore()

def _draw_dining_table_4(p, w, h, sel):
    p.save()
    ch = min(w, h) * 0.22  # chair depth
    cw = min(w*0.45, 14)
    # table surface
    _rect(p, 0, ch, w, h-2*ch, sel)
    # chairs
    p.setPen(_pen(sel)); p.setBrush(_br(_FILL2))
    cx = (w - cw) / 2
    p.drawRect(QRectF(cx, 0, cw, ch*0.85))           # top chair
    p.drawRect(QRectF(cx, h-ch*0.85, cw, ch*0.85))   # bottom chair
    side_h = min(h*0.3, 14)
    side_w = ch * 0.85
    mid_y  = (h - side_h) / 2
    p.drawRect(QRectF(0, mid_y, side_w, side_h))      # left chair
    p.drawRect(QRectF(w-side_w, mid_y, side_w, side_h)) # right chair
    p.restore()

def _draw_dining_table_6(p, w, h, sel):
    p.save()
    ch = min(w, h) * 0.18
    cw = min(w*0.3, 14)
    _rect(p, 0, ch, w, h-2*ch, sel)
    p.setPen(_pen(sel)); p.setBrush(_br(_FILL2))
    # 2 on each short side
    for i in range(2):
        offset = w * (0.2 + i * 0.35)
        p.drawRect(QRectF(offset, 0, cw, ch*0.85))
        p.drawRect(QRectF(offset, h-ch*0.85, cw, ch*0.85))
    # 1 on each long side
    side_h = min(h*0.25, 13)
    side_w = ch * 0.85
    mid_y  = (h - ch - side_h) / 2 + ch
    p.drawRect(QRectF(0, mid_y, side_w, side_h))
    p.drawRect(QRectF(w-side_w, mid_y, side_w, side_h))
    p.restore()

def _draw_dining_chair(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h*0.35, sel, fill=_FILL2)
    _rect(p, 0, h*0.35, w, h*0.65, sel)
    p.restore()

def _draw_bookcase(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    n = max(2, int(w / 14))
    sw = w / n
    for i in range(1, n):
        p.setPen(_pen2(sel))
        p.drawLine(QLineF(sw*i, 0, sw*i, h))
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  STAIRS
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_stairs_straight(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    # tread lines
    nstep = max(4, int(h / 10))
    th    = h / nstep
    p.setPen(_pen2(sel))
    for i in range(1, nstep):
        p.drawLine(QLineF(0, th*i, w, th*i))
    # UP arrow
    mid = w / 2
    p.setPen(_pen(sel, 1.5))
    p.drawLine(QLineF(mid, h*0.9, mid, h*0.1))
    p.drawLine(QLineF(mid-4, h*0.2, mid, h*0.1))
    p.drawLine(QLineF(mid+4, h*0.2, mid, h*0.1))
    _text_label(p, 'UP', mid, h*0.95, sel, 7)
    p.restore()

def _draw_stairs_l(p, w, h, sel):
    p.save()
    hw, hh = w/2, h/2
    # L-shape polygon
    poly = QPolygonF([
        QPointF(0,0), QPointF(w,0), QPointF(w,hh),
        QPointF(hw,hh), QPointF(hw,h), QPointF(0,h)
    ])
    p.setPen(_pen(sel)); p.setBrush(_br())
    p.drawPolygon(poly)
    # tread lines - vertical part
    nv = max(3, int(hh/10))
    for i in range(1, nv):
        y = hh*i/nv
        p.setPen(_pen2(sel))
        p.drawLine(QLineF(0, y, hw, y))
    # horizontal part
    nh = max(3, int(hw/10))
    for i in range(1, nh):
        x = hw + hw*i/nh
        p.drawLine(QLineF(x, 0, x, hh))
    p.restore()

def _draw_stairs_spiral(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    r_out  = min(w,h)/2
    p.setPen(_pen(sel)); p.setBrush(_br())
    p.drawEllipse(QRectF(0, 0, w, h))
    # center post
    p.setPen(_pen2(sel)); p.setBrush(_br(_FILL2))
    p.drawEllipse(QRectF(cx-4, cy-4, 8, 8))
    # treads (radial lines)
    nstep = 12
    for i in range(nstep):
        ang = math.radians(i * 360 / nstep)
        p.setPen(_pen2(sel, 0.8))
        p.drawLine(QLineF(cx + 4*math.cos(ang), cy + 4*math.sin(ang),
                          cx + r_out*math.cos(ang), cy + r_out*math.sin(ang)))
    # UP text
    _text_label(p, 'UP', cx, cy-r_out*0.55, sel, 7)
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  ELECTRICAL
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_outlet_duplex(p, w, h, sel):
    p.save()
    # wall line (back)
    p.setPen(_pen(sel, 2.5)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(0, h/2, w, h/2))
    # circle body
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_ELEC if not sel else _FILL))
    p.drawEllipse(QRectF(w*0.1, 0, w*0.8, h*0.9))
    # two prong slots
    p.setPen(_pen(sel, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(w*0.35, h*0.2, w*0.35, h*0.55))
    p.drawLine(QLineF(w*0.65, h*0.2, w*0.65, h*0.55))
    p.restore()

def _draw_outlet_gfci(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel, 2.5)); p.drawLine(QLineF(0, h/2, w, h/2))
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_ELEC if not sel else _FILL))
    p.drawEllipse(QRectF(w*0.1, 0, w*0.8, h*0.9))
    p.setPen(_pen(sel, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(w*0.35, h*0.2, w*0.35, h*0.55))
    p.drawLine(QLineF(w*0.65, h*0.2, w*0.65, h*0.55))
    _text_label(p, 'GF', w/2, h*0.35, sel, 5)
    p.restore()

def _draw_outlet_220(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel, 2.5)); p.drawLine(QLineF(0, h/2, w, h/2))
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_ELEC if not sel else _FILL))
    p.drawEllipse(QRectF(w*0.1, 0, w*0.8, h*0.9))
    # 3 prong slots
    for i, ang in enumerate([-30, 90, 210]):
        rad = math.radians(ang)
        cx, cy = w/2, h*0.42
        x = cx + w*0.18*math.cos(rad)
        y = cy + h*0.18*math.sin(rad)
        p.setPen(_pen(sel, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(x-2, y-2, 4, 4))
    _text_label(p, '220', w/2, h*0.35, sel, 5)
    p.restore()

def _draw_switch_single(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel, 2.5)); p.drawLine(QLineF(0, h*0.6, w, h*0.6))
    p.setPen(_pen(sel, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
    # S symbol
    _text_label(p, 'S', w/2, h*0.3, sel, 9)
    p.drawLine(QLineF(w*0.2, h*0.55, w*0.8, h*0.55))
    p.restore()

def _draw_switch_3way(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel, 2.5)); p.drawLine(QLineF(0, h*0.6, w, h*0.6))
    p.setPen(_pen(sel, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
    _text_label(p, 'S₃', w/2, h*0.3, sel, 8)
    p.drawLine(QLineF(w*0.2, h*0.55, w*0.8, h*0.55))
    p.restore()

def _draw_switch_dimmer(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel, 2.5)); p.drawLine(QLineF(0, h*0.6, w, h*0.6))
    p.setPen(_pen(sel, 1.5)); p.setBrush(Qt.BrushStyle.NoBrush)
    _text_label(p, 'SD', w/2, h*0.3, sel, 8)
    # dimmer arc
    path = QPainterPath()
    path.moveTo(w*0.2, h*0.55)
    path.arcTo(QRectF(w*0.2, h*0.4, w*0.6, h*0.3), 180, -180)
    p.drawPath(path)
    p.restore()

def _draw_panel_electric(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # breaker rows
    n = max(6, int(h / 3.5))
    rh = h / n
    for i in range(n):
        p.setPen(_pen2(sel, 0.7))
        p.drawLine(QLineF(w*0.05, rh*(i+0.5), w*0.45, rh*(i+0.5)))
        p.drawLine(QLineF(w*0.55, rh*(i+0.5), w*0.95, rh*(i+0.5)))
    # center divider
    p.setPen(_pen(sel, 1.2))
    p.drawLine(QLineF(w/2, 0, w/2, h))
    _text_label(p, 'PANEL', w/2, h*0.5, sel, 7)
    p.restore()

def _draw_light_ceiling(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    r = min(w,h)/2 * 0.85
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL3 if not sel else _FILL))
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    # cross lines
    p.setPen(_pen(sel, 1.2)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(cx-r, cy, cx+r, cy))
    p.drawLine(QLineF(cx, cy-r, cx, cy+r))
    p.restore()

def _draw_light_recessed(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    r = min(w,h)/2 * 0.85
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL3 if not sel else _FILL))
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br())
    p.drawEllipse(QRectF(cx-r*0.35, cy-r*0.35, r*0.7, r*0.7))
    p.restore()

def _draw_ceiling_fan_elec(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    r = min(w,h)/2
    # outer ring
    p.setPen(_pen2(sel, 0.8)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(0, 0, w, h))
    # 4 blades
    for ang in (0, 90, 180, 270):
        rad = math.radians(ang)
        bx  = cx + r*0.35*math.cos(rad)
        by  = cy + r*0.35*math.sin(rad)
        ex  = cx + r*0.90*math.cos(rad)
        ey  = cy + r*0.90*math.sin(rad)
        bw2 = r*0.2
        perp = math.radians(ang + 90)
        poly = QPolygonF([
            QPointF(bx+bw2*math.cos(perp), by+bw2*math.sin(perp)),
            QPointF(bx-bw2*math.cos(perp), by-bw2*math.sin(perp)),
            QPointF(ex, ey),
        ])
        p.setPen(_pen2(sel)); p.setBrush(_br(_FILL2))
        p.drawPolygon(poly)
    # center
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL3))
    p.drawEllipse(QRectF(cx-r*0.15, cy-r*0.15, r*0.3, r*0.3))
    p.restore()

def _draw_light_sconce(p, w, h, sel):
    p.save()
    # wall line (back)
    p.setPen(_pen(sel, 3)); p.drawLine(QLineF(0, 0, 0, h))
    # fixture body
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL3 if not sel else _FILL))
    p.drawEllipse(QRectF(0, (h-w*0.8)/2, w*0.8, w*0.8))
    p.restore()

def _draw_light_track(p, w, h, sel):
    p.save()
    _rect(p, 0, h*0.3, w, h*0.4, sel, fill=_FILL2)
    # fixture heads
    n = max(2, int(w / 10))
    sw = w / n
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL3 if not sel else _FILL))
    for i in range(n):
        cx = sw*(i+0.5)
        p.drawEllipse(QRectF(cx-h*0.3, 0, h*0.6, h*0.6))
        p.drawEllipse(QRectF(cx-h*0.3, h*0.4, h*0.6, h*0.6))
    p.restore()

def _draw_smoke_detector(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    r = min(w,h)/2 * 0.9
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL2 if not sel else _FILL))
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    # "S" in circle
    _text_label(p, 'S', cx, cy, sel, 7)
    p.restore()

def _draw_co_detector(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    r = min(w,h)/2 * 0.9
    p.setPen(_pen(sel, 1.5)); p.setBrush(_br(_FILL2 if not sel else _FILL))
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    _text_label(p, 'CO', cx, cy, sel, 6)
    p.restore()

def _draw_thermostat(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel)
    _text_label(p, 'T', w/2, h/2, sel, 8)
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  HVAC
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_supply_register(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL)
    # parallel lines (supply direction)
    n = max(3, int(h / 3))
    lh = h / n
    p.setPen(_pen2(sel, 0.8, _HVAC if not sel else None))
    for i in range(1, n):
        p.drawLine(QLineF(w*0.05, lh*i, w*0.95, lh*i))
    _text_label(p, 'S', w/2, h/2, sel, 6)
    p.restore()

def _draw_return_grille(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL)
    # crosshatch diagonals
    p.setPen(_pen2(sel, 0.8, _HVAC if not sel else None))
    n = 5
    for i in range(n+1):
        t = i/n
        p.drawLine(QLineF(w*t, 0, 0, h*t))
        p.drawLine(QLineF(w*(1-t), 0, w, h*t))
    _text_label(p, 'R', w/2, h/2, sel, 6)
    p.restore()

def _draw_ceiling_diffuser(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel)); p.setBrush(_br())
    p.drawRect(QRectF(0, 0, w, h))
    # nested rectangles (diffuser louvres)
    p.setPen(_pen2(sel, 0.8, _HVAC if not sel else None))
    for i in range(1, 4):
        mg = min(w,h)*i*0.1
        p.drawRect(QRectF(mg, mg, w-2*mg, h-2*mg))
    _text_label(p, 'D', w/2, h/2, sel, 6)
    p.restore()

def _draw_furnace(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # flame symbol
    p.setPen(_pen(sel, 1.5, _HVAC if not sel else None))
    p.setBrush(Qt.BrushStyle.NoBrush)
    path = QPainterPath()
    path.moveTo(w*0.5, h*0.7)
    path.cubicTo(w*0.3, h*0.5, w*0.4, h*0.35, w*0.5, h*0.45)
    path.cubicTo(w*0.6, h*0.3, w*0.45, h*0.15, w*0.5, h*0.2)
    path.cubicTo(w*0.65, h*0.35, w*0.7, h*0.5, w*0.5, h*0.7)
    p.drawPath(path)
    _text_label(p, 'FURN', w/2, h*0.85, sel, 7)
    p.restore()

def _draw_air_handler(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # fan circle
    cx, cy = w/2, h*0.4
    r = min(w,h)*0.25
    p.setPen(_pen(sel, 1.5, _HVAC if not sel else None)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    p.drawLine(QLineF(cx-r, cy, cx+r, cy))
    p.drawLine(QLineF(cx, cy-r, cx, cy+r))
    _text_label(p, 'AHU', w/2, h*0.82, sel, 7)
    p.restore()

def _draw_ac_condenser(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # top grille lines
    p.setPen(_pen2(sel, 0.8, _HVAC if not sel else None))
    n = max(4, int(w/8))
    sw = w/n
    for i in range(n):
        p.drawLine(QLineF(sw*(i+0.5), h*0.05, sw*(i+0.5), h*0.25))
    # fan
    cx, cy = w/2, h*0.6
    r = min(w,h)*0.25
    p.setPen(_pen(sel, 1.5, _HVAC if not sel else None)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    for ang in (0, 45, 90, 135):
        rad = math.radians(ang)
        p.drawLine(QLineF(cx+r*0.2*math.cos(rad), cy+r*0.2*math.sin(rad),
                          cx+r*0.9*math.cos(rad), cy+r*0.9*math.sin(rad)))
    _text_label(p, 'A/C', w/2, h*0.92, sel, 7)
    p.restore()

def _draw_heat_pump(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # two fan circles
    for cx_frac in (0.3, 0.7):
        cx, cy = w*cx_frac, h*0.5
        r = min(w,h)*0.2
        p.setPen(_pen(sel, 1.5, _HVAC if not sel else None)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
        p.drawLine(QLineF(cx-r, cy, cx+r, cy))
        p.drawLine(QLineF(cx, cy-r, cx, cy+r))
    _text_label(p, 'HP', w/2, h*0.9, sel, 7)
    p.restore()

def _draw_hrv_erv(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # two arrows (supply / exhaust)
    p.setPen(_pen(sel, 1.5, _HVAC if not sel else None))
    # supply arrow →
    p.drawLine(QLineF(w*0.05, h*0.35, w*0.75, h*0.35))
    p.drawLine(QLineF(w*0.65, h*0.2,  w*0.75, h*0.35))
    p.drawLine(QLineF(w*0.65, h*0.5,  w*0.75, h*0.35))
    # exhaust arrow ←
    p.drawLine(QLineF(w*0.25, h*0.65, w*0.95, h*0.65))
    p.drawLine(QLineF(w*0.25, h*0.5,  w*0.15, h*0.65))
    p.drawLine(QLineF(w*0.25, h*0.8,  w*0.15, h*0.65))
    _text_label(p, 'HRV', w/2, h*0.9, sel, 6)
    p.restore()

def _draw_baseboard_heater(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # heating element coil lines
    n = max(4, int(w/8))
    sw = w/n
    p.setPen(_pen2(sel, 0.8, _HVAC if not sel else None))
    for i in range(n):
        cx = sw*(i+0.5)
        p.drawLine(QLineF(cx, h*0.15, cx, h*0.85))
    p.restore()

def _draw_exhaust_fan_hvac(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    r = min(w,h)/2 * 0.9
    p.setPen(_pen(sel, 1.5, _HVAC if not sel else None)); p.setBrush(_br())
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    # blades
    for ang in (45, 135, 225, 315):
        rad = math.radians(ang)
        blen = r * 0.7
        p.setPen(_pen2(sel, 1.0, _HVAC if not sel else None))
        p.drawLine(QLineF(cx, cy,
                          cx + blen*math.cos(rad),
                          cy + blen*math.sin(rad)))
    _text_label(p, 'EF', cx, cy, sel, 6)
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  PLUMBING
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_water_heater_tank(p, w, h, sel):
    p.save()
    # tank body
    p.setPen(_pen(sel, 1.5, _PLUM if not sel else None)); p.setBrush(_br(_FILL2))
    p.drawEllipse(QRectF(w*0.05, h*0.1, w*0.9, h*0.8))
    # top pipe stubs
    p.setPen(_pen(sel, 2, _PLUM if not sel else None))
    p.drawLine(QLineF(w*0.3, h*0.1, w*0.3, 0))
    p.drawLine(QLineF(w*0.7, h*0.1, w*0.7, 0))
    # H / C labels
    _text_label(p, 'H', w*0.3, h*0.06, sel, 5)
    _text_label(p, 'C', w*0.7, h*0.06, sel, 5)
    _text_label(p, 'W.H.', w/2, h/2, sel, 7)
    p.restore()

def _draw_water_heater_tankless(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # heating element grid
    p.setPen(_pen2(sel, 0.8, _PLUM if not sel else None))
    for i in range(1, 5):
        p.drawLine(QLineF(w*0.1, h*i/5, w*0.9, h*i/5))
    # pipe stubs
    p.setPen(_pen(sel, 2, _PLUM if not sel else None))
    p.drawLine(QLineF(w*0.3, 0, w*0.3, h*0.12))
    p.drawLine(QLineF(w*0.7, 0, w*0.7, h*0.12))
    _text_label(p, 'T/L W.H.', w/2, h*0.65, sel, 6)
    p.restore()

def _draw_cleanout(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    r = min(w,h)/2 * 0.85
    p.setPen(_pen(sel, 1.5, _PLUM if not sel else None)); p.setBrush(_br())
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    _text_label(p, 'CO', cx, cy, sel, 6)
    p.restore()

def _draw_floor_drain(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    r = min(w,h)/2 * 0.85
    p.setPen(_pen(sel, 1.5, _PLUM if not sel else None)); p.setBrush(_br(_FILL2))
    p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    # cross grate
    p.setPen(_pen2(sel, 0.8, _PLUM if not sel else None))
    p.drawLine(QLineF(cx-r*0.8, cy, cx+r*0.8, cy))
    p.drawLine(QLineF(cx, cy-r*0.8, cx, cy+r*0.8))
    p.drawLine(QLineF(cx-r*0.55, cy-r*0.55, cx+r*0.55, cy+r*0.55))
    p.drawLine(QLineF(cx+r*0.55, cy-r*0.55, cx-r*0.55, cy+r*0.55))
    p.restore()

def _draw_valve_ball(p, w, h, sel):
    p.save()
    cy = h/2
    # pipe
    p.setPen(_pen(sel, 1.5, _PLUM if not sel else None)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(0, cy, w*0.25, cy))
    p.drawLine(QLineF(w*0.75, cy, w, cy))
    # ball circle
    r = min(w,h)*0.28
    p.setBrush(_br(_FILL2))
    p.drawEllipse(QRectF(w/2-r, cy-r, r*2, r*2))
    # handle
    p.setPen(_pen(sel, 2, _PLUM if not sel else None))
    p.drawLine(QLineF(w/2, cy-r, w/2, cy-r*1.8))
    p.restore()

def _draw_valve_gate(p, w, h, sel):
    p.save()
    cy = h/2
    p.setPen(_pen(sel, 1.5, _PLUM if not sel else None)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(0, cy, w*0.3, cy))
    p.drawLine(QLineF(w*0.7, cy, w, cy))
    # two triangles (gate valve symbol)
    p.setBrush(_br(_FILL2))
    poly1 = QPolygonF([QPointF(w*0.3, cy-h*0.35),
                       QPointF(w*0.7, cy),
                       QPointF(w*0.3, cy+h*0.35)])
    poly2 = QPolygonF([QPointF(w*0.7, cy-h*0.35),
                       QPointF(w*0.3, cy),
                       QPointF(w*0.7, cy+h*0.35)])
    p.drawPolygon(poly1); p.drawPolygon(poly2)
    # stem
    p.setPen(_pen(sel, 2, _PLUM if not sel else None))
    p.drawLine(QLineF(w/2, cy-h*0.35, w/2, 0))
    p.restore()

def _draw_valve_check(p, w, h, sel):
    p.save()
    cy = h/2
    p.setPen(_pen(sel, 1.5, _PLUM if not sel else None)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(0, cy, w, cy))
    # arrow head (check direction)
    p.setBrush(_br(_FILL2))
    poly = QPolygonF([QPointF(w*0.3, cy-h*0.3),
                      QPointF(w*0.7, cy),
                      QPointF(w*0.3, cy+h*0.3)])
    p.drawPolygon(poly)
    # vertical line
    p.setPen(_pen(sel, 2, _PLUM if not sel else None))
    p.drawLine(QLineF(w*0.7, cy-h*0.3, w*0.7, cy+h*0.3))
    p.restore()

def _draw_hose_bib(p, w, h, sel):
    p.save()
    # wall
    p.setPen(_pen(sel, 3)); p.drawLine(QLineF(0, 0, 0, h))
    # body
    p.setPen(_pen(sel, 1.5, _PLUM if not sel else None)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(0, h*0.25, w*0.6, h*0.5))
    # spout
    p.setPen(_pen(sel, 2, _PLUM if not sel else None))
    p.drawLine(QLineF(w*0.6, h/2, w, h*0.65))
    # handle
    p.drawLine(QLineF(w*0.3, h*0.25, w*0.3, 0))
    p.restore()

def _draw_water_meter(p, w, h, sel):
    p.save()
    cy = h/2
    p.setPen(_pen(sel, 1.5, _PLUM if not sel else None)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(w*0.1, cy-h*0.3, w*0.8, h*0.6))
    p.setPen(_pen2(sel, 0.8)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QLineF(0, cy, w*0.1, cy))
    p.drawLine(QLineF(w*0.9, cy, w, cy))
    _text_label(p, 'W.M.', w/2, cy, sel, 6)
    p.restore()

def _draw_sump_pump(p, w, h, sel):
    p.save()
    # pit circle
    p.setPen(_pen(sel, 1.5, _PLUM if not sel else None)); p.setBrush(_br(_FILL2))
    p.drawEllipse(QRectF(0, h*0.3, w, h*0.7))
    # pump body
    p.setBrush(_br(_FILL3))
    r = min(w,h)*0.15
    p.drawEllipse(QRectF(w/2-r, h*0.5-r, r*2, r*2))
    # discharge pipe
    p.setPen(_pen(sel, 2, _PLUM if not sel else None))
    p.drawLine(QLineF(w*0.65, h*0.5, w, h*0.1))
    _text_label(p, 'SP', w/2, h*0.7, sel, 6)
    p.restore()

def _draw_p_trap(p, w, h, sel):
    p.save()
    cx = w/2; r = min(w,h) * 0.35
    p.setPen(_pen(sel, 2, _PLUM if not sel else None)); p.setBrush(Qt.BrushStyle.NoBrush)
    # inlet arm
    p.drawLine(QLineF(0, h*0.2, cx-r, h*0.2))
    # U bend
    path = QPainterPath()
    path.moveTo(cx-r, h*0.2)
    path.arcTo(QRectF(cx-r, h*0.2, r*2, r*2), 180, -180)
    path.lineTo(cx+r, h*0.2+r*2)
    p.drawPath(path)
    # outlet arm
    p.drawLine(QLineF(cx+r, h*0.2+r*2, w, h*0.2+r*2))
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  INSULATION
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_insul_batt(p, w, h, sel):
    p.save()
    # border
    p.setPen(_pen(sel, 1.2, _INSUL if not sel else None)); p.setBrush(_br(_FILL))
    p.drawRect(QRectF(0, 0, w, h))
    # zigzag fill (batt insulation symbol)
    p.setPen(_pen2(sel, 0.8, _INSUL if not sel else None))
    n  = max(3, int(w / (h*1.2)))
    sw = w / n
    for i in range(n):
        x0 = sw * i; x1 = sw * (i + 0.5); x2 = sw * (i + 1)
        p.drawLine(QLineF(x0, h*0.05, x1, h*0.95))
        p.drawLine(QLineF(x1, h*0.95, x2, h*0.05))
    p.restore()

def _draw_insul_rigid(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel, 1.2, _INSUL if not sel else None)); p.setBrush(_br(_FILL))
    p.drawRect(QRectF(0, 0, w, h))
    # cross-hatch
    p.setPen(_pen2(sel, 0.7, _INSUL if not sel else None))
    spacing = max(6, h*1.5)
    x = 0
    while x < w + h:
        p.drawLine(QLineF(max(0, x-h), min(h, max(0, h-(x))),
                          min(w, x),   max(0, h-max(0,x-w+h))))
        p.drawLine(QLineF(min(w, x), max(0, x-w),
                          max(0, x-h), min(h, x)))
        x += spacing
    p.restore()

def _draw_insul_spray(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel, 1.2, _INSUL if not sel else None)); p.setBrush(_br(_FILL))
    p.drawRect(QRectF(0, 0, w, h))
    # wavy lines
    p.setPen(_pen2(sel, 0.8, _INSUL if not sel else None))
    rows = max(2, int(h / 6))
    for row in range(rows):
        cy = h * (row + 0.5) / rows
        path = QPainterPath()
        path.moveTo(0, cy)
        seg = max(6, w/8)
        x = 0
        toggle = 0
        while x < w:
            path.quadTo(x + seg/2, cy + (h*0.08 if toggle else -h*0.08), x + seg, cy)
            x += seg; toggle = 1 - toggle
        p.drawPath(path)
    p.restore()

def _draw_insul_blown(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel, 1.2, _INSUL if not sel else None)); p.setBrush(_br(_FILL))
    p.drawRect(QRectF(0, 0, w, h))
    # random dots
    rng = random.Random(42)
    p.setPen(_pen2(sel, 0.8, _INSUL if not sel else None)); p.setBrush(Qt.BrushStyle.NoBrush)
    n = max(10, int(w*h/25))
    for _ in range(n):
        cx = rng.uniform(2, w-2)
        cy = rng.uniform(2, h-2)
        r  = rng.uniform(1.5, 3.5)
        p.drawEllipse(QRectF(cx-r, cy-r, r*2, r*2))
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  STRUCTURAL / MISC
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_fireplace(p, w, h, sel):
    p.save()
    _rect(p, 0, 0, w, h, sel, fill=_FILL2)
    # firebox opening
    fo = w * 0.1
    p.setPen(_pen2(sel)); p.setBrush(_br(_STRUC if not sel else _FILL))
    p.drawRect(QRectF(fo, fo, w-2*fo, h*0.65))
    # hearth line
    p.setPen(_pen(sel, 2.5))
    p.drawLine(QLineF(0, h*0.75, w, h*0.75))
    # grate lines
    p.setPen(_pen2(sel, 0.8))
    for i in range(1, 4):
        p.drawLine(QLineF(fo*1.5, fo + (h*0.65-2*fo)*i/4,
                          w-fo*1.5, fo + (h*0.65-2*fo)*i/4))
    p.restore()

def _draw_fireplace_corner(p, w, h, sel):
    p.save()
    # L-shape outline
    poly = QPolygonF([
        QPointF(0, 0), QPointF(w, 0), QPointF(w, h*0.35),
        QPointF(w*0.35, h*0.35), QPointF(w*0.35, h), QPointF(0, h)
    ])
    p.setPen(_pen(sel)); p.setBrush(_br(_FILL2))
    p.drawPolygon(poly)
    # firebox
    p.setPen(_pen2(sel)); p.setBrush(_br(_STRUC if not sel else _FILL))
    p.drawRect(QRectF(w*0.04, h*0.04, w*0.28, h*0.28))
    p.restore()

def _draw_column_steel(p, w, h, sel):
    p.save()
    cx, cy = w/2, h/2
    # wide flange (W-shape top view)
    p.setPen(_pen(sel, 2, _STRUC if not sel else None)); p.setBrush(_br(_FILL2))
    # flanges
    p.drawRect(QRectF(0, cy-h*0.12, w, h*0.24))
    # web
    p.drawRect(QRectF(cx-w*0.06, 0, w*0.12, h))
    p.restore()

def _draw_column_wood(p, w, h, sel):
    p.save()
    p.setPen(_pen(sel, 1.5, _STRUC if not sel else None)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(0, 0, w, h))
    # diagonal lines (wood grain symbol)
    p.setPen(_pen2(sel, 0.7, _STRUC if not sel else None))
    p.drawLine(QLineF(0, 0, w, h))
    p.drawLine(QLineF(w, 0, 0, h))
    p.restore()

def _draw_beam_steel(p, w, h, sel):
    p.save()
    cy = h/2
    # wide flange cross-section profile (side view)
    p.setPen(_pen(sel, 2, _STRUC if not sel else None)); p.setBrush(_br(_FILL2))
    p.drawRect(QRectF(0, 0, w, h))
    # web line
    p.setPen(_pen2(sel, 0.8, _STRUC if not sel else None))
    p.drawLine(QLineF(0, h*0.25, w, h*0.25))
    p.drawLine(QLineF(0, h*0.75, w, h*0.75))
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  FLOOR PLAN HELPERS  (Bedroom Layouts + Full Floor Plans)
# ═══════════════════════════════════════════════════════════════════════════════

def _fp_pen_out(sel):
    p = QPen(SEL_COLOR if sel else _FG,  2.5); p.setCosmetic(True); return p
def _fp_pen_iw(sel):
    p = QPen(SEL_COLOR if sel else _FG2, 1.8); p.setCosmetic(True); return p
def _fp_pen_fix(sel):
    p = QPen(SEL_COLOR if sel else _FG2, 1.0); p.setCosmetic(True); return p

def _fp_out(p, w, h, sel):
    p.setPen(_fp_pen_out(sel)); p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(0, 0, w, h))

def _fp_iwall(p, x1, y1, x2, y2, sel):
    p.setPen(_fp_pen_iw(sel)); p.drawLine(QLineF(x1, y1, x2, y2))

def _fp_win(p, x1, y1, x2, y2, sel):
    """Window: two parallel lines + end caps."""
    dx, dy = x2-x1, y2-y1; L = math.hypot(dx, dy)
    if L < 0.1: return
    ux, uy = dx/L, dy/L; px, py = -uy*3, ux*3
    p.setPen(_fp_pen_fix(sel))
    p.drawLine(QLineF(x1+px, y1+py, x2+px, y2+py))
    p.drawLine(QLineF(x1-px, y1-py, x2-px, y2-py))
    p.drawLine(QLineF(x1-px, y1-py, x1+px, y1+py))
    p.drawLine(QLineF(x2-px, y2-py, x2+px, y2+py))

def _fp_door(p, hx, hy, dw, panel_deg, sweep_deg, sel):
    """Door arc. panel_deg=0 → panel goes east; sweep +/-90 typical."""
    p.setPen(_fp_pen_fix(sel)); p.setBrush(Qt.BrushStyle.NoBrush)
    ex = hx + dw * math.cos(math.radians(panel_deg))
    ey = hy - dw * math.sin(math.radians(panel_deg))
    p.drawLine(QLineF(hx, hy, ex, ey))
    arc = QRectF(hx-dw, hy-dw, 2*dw, 2*dw)
    path = QPainterPath(); path.arcMoveTo(arc, panel_deg); path.arcTo(arc, panel_deg, sweep_deg)
    p.drawPath(path)

def _fp_lbl(p, text, cx, cy, sel, sz=8):
    f = QFont('Arial'); f.setPixelSize(max(1, sz)); p.setFont(f)
    p.setPen(_fp_pen_fix(sel))
    p.drawText(QRectF(cx-80, cy-sz//2-1, 160, sz+4), Qt.AlignmentFlag.AlignCenter, text)

def _fp_bed(p, x, y, bw, bh, sel):
    p.setPen(_fp_pen_fix(sel)); p.setBrush(QBrush(_FILL2))
    p.drawRect(QRectF(x, y, bw, bh))
    ph = bh*0.20; p.setBrush(QBrush(_FILL3))
    p.drawRect(QRectF(x+bw*0.07, y+bh*0.04, bw*0.38, ph))
    p.drawRect(QRectF(x+bw*0.55, y+bh*0.04, bw*0.38, ph))

def _fp_cbox(p, x, y, cw, ch, sel):
    p.setPen(_fp_pen_fix(sel)); p.setBrush(QBrush(_FILL2))
    p.drawRect(QRectF(x, y, cw, ch))
    for i in (0.33, 0.67): p.drawLine(QLineF(x, y+ch*i, x+cw, y+ch*i))

def _fp_toilet_s(p, x, y, tw, th, sel):
    p.setPen(_fp_pen_fix(sel)); p.setBrush(QBrush(_FILL2))
    p.drawRect(QRectF(x, y, tw, th*0.34))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(x+tw*0.10, y+th*0.31, tw*0.80, th*0.66))

def _fp_vanity_s(p, x, y, vw, vh, sel):
    p.setPen(_fp_pen_fix(sel)); p.setBrush(QBrush(_FILL2))
    p.drawRect(QRectF(x, y, vw, vh))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(x+vw*0.18, y+vh*0.16, vw*0.64, vh*0.68))

def _fp_tub_s(p, x, y, tw, th, sel):
    p.setPen(_fp_pen_fix(sel)); p.setBrush(QBrush(_FILL2))
    p.drawRect(QRectF(x, y, tw, th))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(x+tw*0.08, y+th*0.08, tw*0.84, th*0.84), 4, 4)

def _fp_cntr(p, x, y, cw, ch, sel):
    p.setPen(_fp_pen_fix(sel)); p.setBrush(QBrush(_FILL2))
    p.drawRect(QRectF(x, y, cw, ch))
    p.setBrush(Qt.BrushStyle.NoBrush)
    r = min(cw, ch)*0.28
    p.drawEllipse(QRectF(x+cw*0.5-r, y+ch*0.5-r, r*2, r*2))

# ═══════════════════════════════════════════════════════════════════════════════
#  BEDROOM LAYOUTS
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_fp_bed_twin(p, w, h, sel):
    """9'×10' twin bedroom."""
    p.save(); sz = max(6, int(min(w, h)*0.06))
    _fp_out(p, w, h, sel)
    _fp_win(p, w*0.25, 0, w*0.65, 0, sel)
    _fp_door(p, w, h, w*0.30, 180, -90, sel)
    _fp_bed(p, w*0.05, h*0.06, w*0.34, h*0.58, sel)
    ns = w*0.14
    _fp_cbox(p, w*0.43, h*0.06, ns, ns, sel)
    _fp_cbox(p, w*0.62, h*0.06, w*0.33, h*0.22, sel)
    _fp_cbox(p, w*0.62, h*0.35, w*0.33, h*0.20, sel)
    _fp_lbl(p, "9' × 10'", w/2, h*0.90, sel, sz)
    p.restore()

def _draw_fp_bed_standard(p, w, h, sel):
    """11'×12' standard bedroom."""
    p.save(); sz = max(6, int(min(w, h)*0.06))
    _fp_out(p, w, h, sel)
    _fp_win(p, w*0.25, 0, w*0.75, 0, sel)
    _fp_door(p, 0, h, w*0.28, 0, 90, sel)
    ns = min(w, h)*0.12
    bx = ns + w*0.02
    bw, bh = w*0.46, h*0.54
    _fp_bed(p, bx, h*0.06, bw, bh, sel)
    _fp_cbox(p, w*0.02, h*0.06, ns, ns, sel)
    _fp_cbox(p, bx+bw+w*0.01, h*0.06, ns, ns, sel)
    _fp_cbox(p, w*0.72, h*0.68, w*0.24, h*0.26, sel)
    _fp_lbl(p, "11' × 12'", w/2, h*0.91, sel, sz)
    p.restore()

def _draw_fp_bed_large(p, w, h, sel):
    """12'×14' bedroom with walk-in closet."""
    p.save(); sz = max(6, int(min(w, h)*0.06))
    _fp_out(p, w, h, sel)
    cx, ch = w*0.65, h*0.27
    _fp_iwall(p, cx, 0, cx, ch, sel)
    _fp_iwall(p, cx, ch, w, ch, sel)
    _fp_lbl(p, 'W.I.C.', cx+(w-cx)/2, ch/2, sel, sz-1)
    _fp_door(p, cx, ch, w*0.17, 0, -90, sel)
    _fp_win(p, 0, h*0.30, 0, h*0.70, sel)
    _fp_door(p, w, h, w*0.28, 180, -90, sel)
    _fp_bed(p, w*0.05, h*0.08, w*0.48, h*0.48, sel)
    ns = min(w, h)*0.12
    _fp_cbox(p, w*0.05, h*0.58, ns, ns, sel)
    _fp_cbox(p, w*0.05, h*0.75, w*0.38, h*0.16, sel)
    _fp_lbl(p, "12' × 14'  + WIC", w/2, h*0.94, sel, sz)
    p.restore()

def _draw_fp_bed_master(p, w, h, sel):
    """14'×16' master bedroom with walk-in closet."""
    p.save(); sz = max(6, int(min(w, h)*0.06))
    _fp_out(p, w, h, sel)
    cx = w*0.62
    _fp_iwall(p, cx, 0, cx, h, sel)
    _fp_lbl(p, 'W.I.C.', cx+(w-cx)/2, h/2, sel, sz-1)
    _fp_door(p, cx, h*0.18, w*0.22, 0, 90, sel)
    _fp_win(p, w*0.05, 0, w*0.50, 0, sel)
    _fp_door(p, 0, h, w*0.26, 0, 90, sel)
    _fp_bed(p, w*0.06, h*0.10, w*0.50, h*0.47, sel)
    ns = min(w, h)*0.12
    _fp_cbox(p, w*0.06, h*0.60, ns, ns, sel)
    _fp_cbox(p, w*0.06+ns+w*0.02, h*0.60, ns, ns, sel)
    _fp_cbox(p, w*0.06, h*0.76, w*0.40, h*0.16, sel)
    _fp_lbl(p, "14' × 16'  + WIC", cx/2, h*0.94, sel, sz)
    p.restore()

def _draw_fp_bed_master_en(p, w, h, sel):
    """14'×20' master with ensuite."""
    p.save(); sz = max(6, int(min(w, h)*0.055))
    dy = h*0.62
    _fp_out(p, w, h, sel)
    _fp_iwall(p, 0, dy, w, dy, sel)
    # bedroom
    _fp_win(p, w*0.12, 0, w*0.62, 0, sel)
    _fp_door(p, 0, dy, w*0.22, 0, 90, sel)
    cx = w*0.65
    _fp_iwall(p, cx, 0, cx, dy, sel)
    _fp_lbl(p, 'W.I.C.', cx+(w-cx)/2, dy*0.32, sel, sz-1)
    _fp_door(p, cx, dy*0.08, w*0.22, 0, -90, sel)
    _fp_bed(p, w*0.06, h*0.04, w*0.52, dy*0.66, sel)
    _fp_lbl(p, 'BEDROOM', cx*0.40, dy*0.85, sel, sz)
    # ensuite
    _fp_lbl(p, 'ENSUITE', w/2, dy+(h-dy)*0.08, sel, sz-1)
    _fp_door(p, w*0.34, dy, w*0.20, 0, -90, sel)
    _fp_toilet_s(p, w*0.68, dy+h*0.04, w*0.20, (h-dy)*0.44, sel)
    _fp_vanity_s(p, w*0.06, dy+h*0.04, w*0.36, (h-dy)*0.42, sel)
    _fp_tub_s(p, w*0.60, dy+(h-dy)*0.52, w*0.35, (h-dy)*0.42, sel)
    _fp_win(p, w*0.18, h, w*0.55, h, sel)
    _fp_lbl(p, "14' × 20'  +Ensuite", w*0.32, h*0.97, sel, sz)
    p.restore()

def _draw_fp_bed_kids(p, w, h, sel):
    """10'×12' kids / bunk room."""
    p.save(); sz = max(6, int(min(w, h)*0.06))
    _fp_out(p, w, h, sel)
    _fp_win(p, w*0.20, 0, w*0.68, 0, sel)
    _fp_door(p, w, h, w*0.30, 180, -90, sel)
    bw = w*0.42; bh = h*0.53
    _fp_bed(p, w*0.04, h*0.06, bw, bh, sel)
    _fp_bed(p, w*0.50, h*0.06, bw, bh, sel)
    _fp_cbox(p, w*0.04, h*0.68, w*0.44, h*0.18, sel)
    _fp_cbox(p, w*0.54, h*0.68, w*0.40, h*0.18, sel)
    _fp_lbl(p, "10' × 12'  Bunk Rm", w/2, h*0.92, sel, sz)
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  FULL FLOOR PLANS
# ═══════════════════════════════════════════════════════════════════════════════

def _draw_fp_home_2br_800(p, w, h, sel):
    """2BR ~800 sqft  (28'×30')."""
    p.save(); sz = max(6, int(min(w, h)*0.044))
    _fp_out(p, w, h, sel)
    yd = h*0.46
    _fp_iwall(p, 0, yd, w, yd, sel)
    xd1 = w*0.63
    _fp_iwall(p, xd1, 0, xd1, yd, sel)
    xb1, xb2 = w*0.44, w*0.69
    _fp_iwall(p, xb1, yd, xb1, h, sel)
    _fp_iwall(p, xb2, yd, xb2, h, sel)
    # labels
    _fp_lbl(p, 'LIVING', xd1*0.50, yd*0.36, sel, sz)
    _fp_lbl(p, 'KITCHEN', (xd1+w)*0.50, yd*0.36, sel, sz)
    _fp_lbl(p, 'BEDROOM 1', xb1*0.50, yd+(h-yd)*0.42, sel, sz)
    _fp_lbl(p, 'BATH', (xb1+xb2)*0.50, yd+(h-yd)*0.45, sel, sz-1)
    _fp_lbl(p, 'BEDROOM 2', (xb2+w)*0.50, yd+(h-yd)*0.42, sel, sz)
    # fixtures
    _fp_cntr(p, xd1, h*0.04, w-xd1, yd*0.30, sel)
    _fp_toilet_s(p, xb1+w*0.03, yd+(h-yd)*0.07, (xb2-xb1)*0.46, (h-yd)*0.38, sel)
    _fp_vanity_s(p, xb1+w*0.03, yd+(h-yd)*0.54, (xb2-xb1)*0.46, (h-yd)*0.36, sel)
    # doors
    _fp_door(p, w*0.82, 0, w*0.14, 270, -90, sel)
    _fp_door(p, 0, yd, w*0.20, 0, -90, sel)
    _fp_door(p, xb2, yd, w*0.20, 0, -90, sel)
    # windows
    _fp_win(p, w*0.08, 0, w*0.44, 0, sel)
    _fp_win(p, 0, h*0.08, 0, h*0.36, sel)
    _fp_win(p, 0, yd+h*0.06, 0, yd+h*0.32, sel)
    _fp_win(p, w*0.72, h, w*0.93, h, sel)
    p.restore()

def _draw_fp_home_2br_1000(p, w, h, sel):
    """2BR ~1000 sqft  (34'×30')."""
    p.save(); sz = max(6, int(min(w, h)*0.040))
    _fp_out(p, w, h, sel)
    yd = h*0.48
    _fp_iwall(p, 0, yd, w, yd, sel)
    xg = w*0.28
    _fp_iwall(p, xg, 0, xg, yd, sel)
    xm, xhb = w*0.50, w*0.66
    _fp_iwall(p, xm, yd, xm, h, sel)
    _fp_iwall(p, xhb, yd, xhb, h, sel)
    xba = xhb + (w-xhb)*0.46
    _fp_iwall(p, xba, yd, xba, yd+(h-yd)*0.56, sel)
    _fp_iwall(p, xhb, yd+(h-yd)*0.56, xba, yd+(h-yd)*0.56, sel)
    # labels
    _fp_lbl(p, 'GARAGE', xg/2, yd*0.38, sel, sz)
    _fp_lbl(p, 'OPEN LIVING + KITCHEN', (xg+w)*0.50, yd*0.38, sel, sz)
    _fp_lbl(p, 'MASTER', xm*0.50, yd+(h-yd)*0.50, sel, sz)
    _fp_lbl(p, 'HALL', (xm+xhb)*0.50, yd+(h-yd)*0.38, sel, sz-1)
    _fp_lbl(p, 'BATH', (xhb+xba)*0.50, yd+(h-yd)*0.28, sel, sz-1)
    _fp_lbl(p, 'BED 2', (xba+w)*0.50, yd+(h-yd)*0.50, sel, sz-1)
    # fixtures
    _fp_toilet_s(p, xhb+w*0.01, yd+h*0.02, (xba-xhb)*0.50, (h-yd)*0.38, sel)
    _fp_vanity_s(p, xhb+w*0.01, yd+(h-yd)*0.44, (xba-xhb)*0.65, (h-yd)*0.34, sel)
    # doors
    _fp_door(p, xg*0.46, 0, w*0.14, 270, -90, sel)
    _fp_door(p, 0, yd, w*0.20, 0, -90, sel)
    _fp_door(p, xhb, yd, w*0.18, 0, -90, sel)
    # windows
    _fp_win(p, w*0.36, 0, w*0.74, 0, sel)
    _fp_win(p, 0, h*0.08, 0, h*0.36, sel)
    _fp_win(p, 0, yd+h*0.08, 0, yd+h*0.32, sel)
    _fp_win(p, (xba+w)*0.50-w*0.08, h, (xba+w)*0.50+w*0.08, h, sel)
    p.restore()

def _draw_fp_home_3br_1200(p, w, h, sel):
    """3BR ~1200 sqft  (36'×34')."""
    p.save(); sz = max(6, int(min(w, h)*0.038))
    _fp_out(p, w, h, sel)
    yd = h*0.44
    _fp_iwall(p, 0, yd, w, yd, sel)
    xk = w*0.58
    _fp_iwall(p, xk, 0, xk, yd, sel)
    xm, xb2, xb3 = w*0.42, w*0.64, w*0.82
    _fp_iwall(p, xm, yd, xm, h, sel)
    _fp_iwall(p, xb2, yd, xb2, h, sel)
    _fp_iwall(p, xb3, yd, xb3, h, sel)
    # master bath pocket top-left of bottom
    xmb = xm*0.55
    _fp_iwall(p, xmb, yd, xmb, yd+(h-yd)*0.54, sel)
    _fp_iwall(p, 0, yd+(h-yd)*0.54, xmb, yd+(h-yd)*0.54, sel)
    # hall bath
    xhb = xm + (xb2-xm)*0.42
    _fp_iwall(p, xhb, yd, xhb, yd+(h-yd)*0.56, sel)
    _fp_iwall(p, xm, yd+(h-yd)*0.56, xhb, yd+(h-yd)*0.56, sel)
    # labels
    _fp_lbl(p, 'LIVING', xk*0.50, yd*0.38, sel, sz)
    _fp_lbl(p, 'KITCHEN', (xk+w)*0.50, yd*0.38, sel, sz)
    _fp_lbl(p, 'M.BATH', xmb*0.50, yd+(h-yd)*0.26, sel, sz-1)
    _fp_lbl(p, 'MASTER', (xmb+xm)*0.50, yd+(h-yd)*0.72, sel, sz)
    _fp_lbl(p, 'BATH', (xm+xhb)*0.50, yd+(h-yd)*0.28, sel, sz-1)
    _fp_lbl(p, 'BED 2', (xb2+xm)*0.50+(xhb-xm)*0.30, yd+(h-yd)*0.72, sel, sz)
    _fp_lbl(p, 'BED 3', (xb2+xb3)*0.50, yd+(h-yd)*0.50, sel, sz)
    _fp_lbl(p, 'BED 4', (xb3+w)*0.50, yd+(h-yd)*0.50, sel, sz)
    # fixtures
    _fp_toilet_s(p, xmb*0.06, yd+h*0.02, xmb*0.48, (h-yd)*0.38, sel)
    _fp_vanity_s(p, xmb*0.06, yd+(h-yd)*0.44, xmb*0.62, (h-yd)*0.34, sel)
    _fp_toilet_s(p, xm+w*0.01, yd+h*0.02, (xhb-xm)*0.55, (h-yd)*0.38, sel)
    _fp_vanity_s(p, xm+w*0.01, yd+(h-yd)*0.44, (xhb-xm)*0.70, (h-yd)*0.34, sel)
    # doors
    _fp_door(p, w*0.30, 0, w*0.14, 270, -90, sel)
    _fp_door(p, xmb, yd+(h-yd)*0.54, w*0.18, 0, -90, sel)
    _fp_door(p, xm, yd, w*0.16, 0, -90, sel)
    _fp_door(p, xb2, yd, w*0.16, 0, -90, sel)
    _fp_door(p, xb3, yd, w*0.16, 0, -90, sel)
    # windows
    _fp_win(p, w*0.06, 0, w*0.44, 0, sel)
    _fp_win(p, w*0.68, 0, w*0.92, 0, sel)
    _fp_win(p, 0, h*0.08, 0, h*0.34, sel)
    _fp_win(p, 0, yd+h*0.06, 0, yd+h*0.30, sel)
    _fp_win(p, w*0.08, h, w*0.36, h, sel)
    _fp_win(p, w*0.66, h, w*0.92, h, sel)
    p.restore()

def _draw_fp_home_3br_1400(p, w, h, sel):
    """3BR ~1400 sqft  (40'×36')."""
    p.save(); sz = max(6, int(min(w, h)*0.038))
    _fp_out(p, w, h, sel)
    yd = h*0.54
    _fp_iwall(p, 0, yd, w, yd, sel)
    xe, xms = w*0.22, w*0.74
    _fp_iwall(p, xe, 0, xe, yd, sel)
    _fp_iwall(p, xms, 0, xms, yd, sel)
    xmb = xms + (w-xms)*0.44
    _fp_iwall(p, xmb, 0, xmb, yd*0.54, sel)
    _fp_iwall(p, xms, yd*0.54, xmb, yd*0.54, sel)
    xbd, xha, xba = w*0.38, w*0.52, w*0.66
    _fp_iwall(p, xbd, yd, xbd, h, sel)
    _fp_iwall(p, xha, yd, xha, h, sel)
    _fp_iwall(p, xba, yd, xba, h, sel)
    # labels
    _fp_lbl(p, 'ENTRY', xe/2, yd*0.38, sel, sz-1)
    _fp_lbl(p, 'GREAT ROOM + KITCHEN', (xe+xms)*0.50, yd*0.38, sel, sz)
    _fp_lbl(p, 'MASTER', (xms+w)*0.50, yd*0.70, sel, sz)
    _fp_lbl(p, 'M.BA', (xmb+w)*0.50, yd*0.24, sel, sz-1)
    _fp_lbl(p, 'BED 2', xbd*0.50, yd+(h-yd)*0.50, sel, sz)
    _fp_lbl(p, 'HALL', (xbd+xha)*0.50, yd+(h-yd)*0.38, sel, sz-1)
    _fp_lbl(p, 'BATH', (xha+xba)*0.50, yd+(h-yd)*0.38, sel, sz-1)
    _fp_lbl(p, 'BED 3', (xba+w)*0.50, yd+(h-yd)*0.50, sel, sz)
    # fixtures
    _fp_toilet_s(p, xmb+w*0.01, h*0.02, (w-xmb)*0.52, yd*0.38, sel)
    _fp_vanity_s(p, xmb+w*0.01, yd*0.42, (w-xmb)*0.68, yd*0.34, sel)
    _fp_toilet_s(p, xha+w*0.01, yd+h*0.02, (xba-xha)*0.56, (h-yd)*0.38, sel)
    _fp_vanity_s(p, xha+w*0.01, yd+(h-yd)*0.44, (xba-xha)*0.72, (h-yd)*0.34, sel)
    # doors
    _fp_door(p, xe*0.48, 0, w*0.16, 270, -90, sel)
    _fp_door(p, xms, yd*0.56, w*0.18, 0, 90, sel)
    _fp_door(p, 0, yd, w*0.18, 0, -90, sel)
    _fp_door(p, xba, yd, w*0.18, 0, -90, sel)
    # windows
    _fp_win(p, w*0.30, 0, w*0.68, 0, sel)
    _fp_win(p, w*0.80, 0, w*0.95, 0, sel)
    _fp_win(p, 0, h*0.06, 0, h*0.42, sel)
    _fp_win(p, 0, yd+h*0.06, 0, yd+h*0.32, sel)
    _fp_win(p, w*0.06, h, w*0.30, h, sel)
    _fp_win(p, w*0.70, h, w*0.93, h, sel)
    p.restore()

def _draw_fp_home_4br_1800(p, w, h, sel):
    """4BR ~1800 sqft  (44'×42')."""
    p.save(); sz = max(6, int(min(w, h)*0.036))
    _fp_out(p, w, h, sel)
    yd = h*0.50
    _fp_iwall(p, 0, yd, w, yd, sel)
    xg, xl = w*0.28, w*0.82
    _fp_iwall(p, xg, 0, xg, yd, sel)
    _fp_iwall(p, xl, yd*0.38, xl, yd, sel)
    _fp_iwall(p, xl, yd*0.38, w, yd*0.38, sel)
    xm, xhb, xb3, xb4 = w*0.36, w*0.58, w*0.76, w*0.89
    _fp_iwall(p, xm, yd, xm, h, sel)
    _fp_iwall(p, xhb, yd, xhb, h, sel)
    _fp_iwall(p, xb3, yd, xb3, h, sel)
    _fp_iwall(p, xb4, yd, xb4, h, sel)
    xmb = xm*0.58
    _fp_iwall(p, xmb, yd, xmb, yd+(h-yd)*0.56, sel)
    _fp_iwall(p, 0, yd+(h-yd)*0.56, xmb, yd+(h-yd)*0.56, sel)
    # labels
    _fp_lbl(p, 'GARAGE', xg*0.50, yd*0.38, sel, sz)
    _fp_lbl(p, 'LIVING / DINING / KITCHEN', (xg+xl)*0.50, yd*0.38, sel, sz)
    _fp_lbl(p, 'UTIL', (xl+w)*0.50, yd*0.70, sel, sz-2)
    _fp_lbl(p, 'M.BA', xmb*0.50, yd+(h-yd)*0.26, sel, sz-1)
    _fp_lbl(p, 'MASTER', (xmb+xm)*0.50, yd+(h-yd)*0.72, sel, sz)
    _fp_lbl(p, 'BATH', (xm+xhb)*0.50, yd+(h-yd)*0.30, sel, sz-1)
    _fp_lbl(p, 'BED 2', (xm+xhb)*0.50, yd+(h-yd)*0.72, sel, sz)
    _fp_lbl(p, 'BED 3', (xhb+xb3)*0.50, yd+(h-yd)*0.50, sel, sz)
    _fp_lbl(p, 'BED 4', (xb3+xb4)*0.50, yd+(h-yd)*0.50, sel, sz)
    # fixtures
    _fp_toilet_s(p, xmb*0.06, yd+h*0.02, xmb*0.48, (h-yd)*0.38, sel)
    _fp_vanity_s(p, xmb*0.06, yd+(h-yd)*0.44, xmb*0.62, (h-yd)*0.34, sel)
    _fp_toilet_s(p, xm+w*0.01, yd+h*0.02, (xhb-xm)*0.50, (h-yd)*0.38, sel)
    _fp_vanity_s(p, xm+w*0.01, yd+(h-yd)*0.44, (xhb-xm)*0.65, (h-yd)*0.34, sel)
    # doors
    _fp_door(p, xg*0.45, 0, w*0.14, 270, -90, sel)
    _fp_door(p, xmb, yd+(h-yd)*0.56, w*0.18, 0, -90, sel)
    _fp_door(p, xm, yd, w*0.16, 0, -90, sel)
    _fp_door(p, xhb, yd, w*0.16, 0, -90, sel)
    _fp_door(p, xb3, yd, w*0.16, 0, -90, sel)
    # windows
    _fp_win(p, w*0.35, 0, w*0.73, 0, sel)
    _fp_win(p, 0, h*0.08, 0, h*0.38, sel)
    _fp_win(p, 0, yd+h*0.07, 0, yd+h*0.30, sel)
    _fp_win(p, w*0.06, h, w*0.28, h, sel)
    _fp_win(p, (xhb+xb3)*0.50-w*0.06, h, (xhb+xb3)*0.50+w*0.06, h, sel)
    _fp_win(p, w*0.76, h, w*0.93, h, sel)
    p.restore()

def _draw_fp_home_4br_2000(p, w, h, sel):
    """4BR open-plan ~2000 sqft  (48'×44')."""
    p.save(); sz = max(6, int(min(w, h)*0.036))
    _fp_out(p, w, h, sel)
    yd = h*0.46
    _fp_iwall(p, 0, yd, w, yd, sel)
    xe, xmr = w*0.20, w*0.72
    _fp_iwall(p, xe, 0, xe, yd, sel)
    _fp_iwall(p, xmr, 0, xmr, yd, sel)
    xmb = xmr + (w-xmr)*0.44
    _fp_iwall(p, xmb, 0, xmb, yd*0.56, sel)
    _fp_iwall(p, xmr, yd*0.56, xmb, yd*0.56, sel)
    xb1, xba1, xb2, xb3, xba2 = w*0.22, w*0.36, w*0.50, w*0.64, w*0.78
    for x in (xb1, xba1, xb2, xb3, xba2):
        _fp_iwall(p, x, yd, x, h, sel)
    # labels
    _fp_lbl(p, 'ENTRY', xe*0.50, yd*0.38, sel, sz-1)
    _fp_lbl(p, 'GREAT ROOM + KITCHEN', (xe+xmr)*0.50, yd*0.38, sel, sz)
    _fp_lbl(p, 'MASTER', (xmr+w)*0.50, yd*0.68, sel, sz)
    _fp_lbl(p, 'M.BA', (xmb+w)*0.50, yd*0.26, sel, sz-1)
    _fp_lbl(p, 'BED 1', xb1*0.50, yd+(h-yd)*0.50, sel, sz)
    _fp_lbl(p, 'BA', (xb1+xba1)*0.50, yd+(h-yd)*0.30, sel, sz-1)
    _fp_lbl(p, 'BED 2', (xba1+xb2)*0.50, yd+(h-yd)*0.50, sel, sz)
    _fp_lbl(p, 'BED 3', (xb2+xb3)*0.50, yd+(h-yd)*0.50, sel, sz)
    _fp_lbl(p, 'BA', (xb3+xba2)*0.50, yd+(h-yd)*0.30, sel, sz-1)
    _fp_lbl(p, 'BED 4', (xba2+w)*0.50, yd+(h-yd)*0.50, sel, sz)
    # fixtures
    _fp_toilet_s(p, xb1+w*0.01, yd+h*0.02, (xba1-xb1)*0.54, (h-yd)*0.38, sel)
    _fp_vanity_s(p, xb1+w*0.01, yd+(h-yd)*0.44, (xba1-xb1)*0.70, (h-yd)*0.34, sel)
    _fp_toilet_s(p, xb3+w*0.01, yd+h*0.02, (xba2-xb3)*0.54, (h-yd)*0.38, sel)
    _fp_vanity_s(p, xb3+w*0.01, yd+(h-yd)*0.44, (xba2-xb3)*0.70, (h-yd)*0.34, sel)
    _fp_toilet_s(p, xmb+w*0.01, h*0.02, (w-xmb)*0.54, yd*0.40, sel)
    _fp_vanity_s(p, xmb+w*0.01, yd*0.44, (w-xmb)*0.70, yd*0.35, sel)
    # doors
    _fp_door(p, xe*0.46, 0, w*0.14, 270, -90, sel)
    _fp_door(p, xmr, yd*0.58, w*0.16, 0, 90, sel)
    _fp_door(p, 0, yd, w*0.16, 0, -90, sel)
    _fp_door(p, xba1, yd, w*0.14, 0, -90, sel)
    _fp_door(p, xb2, yd, w*0.14, 0, -90, sel)
    _fp_door(p, xba2, yd, w*0.14, 0, -90, sel)
    # windows
    _fp_win(p, w*0.28, 0, w*0.65, 0, sel)
    _fp_win(p, w*0.79, 0, w*0.93, 0, sel)
    _fp_win(p, 0, h*0.05, 0, h*0.38, sel)
    _fp_win(p, 0, yd+h*0.06, 0, yd+h*0.32, sel)
    _fp_win(p, w*0.04, h, w*0.17, h, sel)
    _fp_win(p, w*0.53, h, w*0.62, h, sel)
    _fp_win(p, w*0.80, h, w*0.93, h, sel)
    p.restore()

# ═══════════════════════════════════════════════════════════════════════════════
#  Registry
# ═══════════════════════════════════════════════════════════════════════════════

FIXTURE_SPECS = {
    # key: (label, category, default_w_in, default_h_in, draw_fn)
    # KITCHEN
    'sink_single':      ('Sink (Single)',         'Kitchen',    21, 21,  _draw_sink_single),
    'sink_double':      ('Sink (Double)',          'Kitchen',    33, 21,  _draw_sink_double),
    'sink_farmhouse':   ('Sink (Farmhouse)',       'Kitchen',    36, 22,  _draw_sink_farmhouse),
    'fridge_std':       ('Refrigerator',           'Kitchen',    30, 30,  _draw_fridge_std),
    'fridge_sbs':       ('Fridge (Side-by-Side)',  'Kitchen',    36, 30,  _draw_fridge_sbs),
    'range_4b':         ('Range (4-Burner)',       'Kitchen',    30, 26,  _draw_range_4b),
    'range_6b':         ('Range (6-Burner)',       'Kitchen',    36, 26,  _draw_range_6b),
    'dishwasher':       ('Dishwasher',             'Kitchen',    24, 24,  _draw_dishwasher),
    'microwave':        ('Microwave',              'Kitchen',    24, 14,  _draw_microwave),
    'oven_wall':        ('Wall Oven',              'Kitchen',    24, 24,  _draw_oven_wall),
    'cooktop_4':        ('Cooktop (4-Burner)',     'Kitchen',    30, 21,  _draw_cooktop_4),
    'hood_vent':        ('Hood Vent',              'Kitchen',    30, 18,  _draw_hood_vent),
    # BATHROOM
    'toilet':           ('Toilet',                 'Bathroom',   18, 30,  _draw_toilet),
    'toilet_tankless':  ('Toilet (Tankless)',      'Bathroom',   18, 28,  _draw_toilet_tankless),
    'vanity_single':    ('Vanity (Single)',         'Bathroom',   24, 21,  _draw_vanity_single),
    'vanity_double':    ('Vanity (Double)',         'Bathroom',   48, 21,  _draw_vanity_double),
    'bathtub':          ('Bathtub',                'Bathroom',   32, 60,  _draw_bathtub),
    'bathtub_corner':   ('Bathtub (Corner)',       'Bathroom',   48, 48,  _draw_bathtub_corner),
    'shower_stall':     ('Shower Stall',           'Bathroom',   36, 36,  _draw_shower_stall),
    'shower_corner':    ('Shower (Corner)',        'Bathroom',   36, 36,  _draw_shower_corner),
    'bidet':            ('Bidet',                  'Bathroom',   14, 22,  _draw_bidet),
    # BEDROOM / FURNITURE
    'bed_twin':         ('Bed (Twin 38×75)',       'Bedroom',    38, 75,  _draw_bed),
    'bed_full':         ('Bed (Full 54×75)',       'Bedroom',    54, 75,  _draw_bed),
    'bed_queen':        ('Bed (Queen 60×80)',      'Bedroom',    60, 80,  _draw_bed),
    'bed_king':         ('Bed (King 76×80)',       'Bedroom',    76, 80,  _draw_bed),
    'nightstand':       ('Nightstand',             'Bedroom',    18, 18,  _draw_nightstand),
    'dresser':          ('Dresser',                'Bedroom',    36, 18,  _draw_dresser),
    'wardrobe':         ('Wardrobe',               'Bedroom',    48, 24,  _draw_wardrobe),
    # LIVING / DINING
    'sofa_2seat':       ('Sofa (2-Seat)',          'Living',     60, 32,  lambda p,w,h,s: _draw_sofa(p,w,h,s,2)),
    'sofa_3seat':       ('Sofa (3-Seat)',          'Living',     84, 32,  lambda p,w,h,s: _draw_sofa(p,w,h,s,3)),
    'armchair':         ('Armchair',               'Living',     36, 36,  _draw_armchair),
    'coffee_table':     ('Coffee Table',           'Living',     48, 24,  _draw_coffee_table),
    'coffee_table_rnd': ('Coffee Table (Round)',   'Living',     36, 36,  _draw_coffee_table_round),
    'tv_unit':          ('TV / Media Unit',        'Living',     60, 18,  _draw_tv_unit),
    'dining_table_4':   ('Dining Table (4-seat)',  'Living',     48, 36,  _draw_dining_table_4),
    'dining_table_6':   ('Dining Table (6-seat)',  'Living',     72, 36,  _draw_dining_table_6),
    'dining_chair':     ('Dining Chair',           'Living',     18, 18,  _draw_dining_chair),
    'bookcase':         ('Bookcase',               'Living',     36, 12,  _draw_bookcase),
    # STAIRS
    'stairs_straight':  ('Stairs (Straight)',      'Stairs',     36, 96,  _draw_stairs_straight),
    'stairs_l':         ('Stairs (L-Shape)',       'Stairs',     60, 60,  _draw_stairs_l),
    'stairs_spiral':    ('Stairs (Spiral)',        'Stairs',     48, 48,  _draw_stairs_spiral),
    # ELECTRICAL
    'outlet_duplex':    ('Duplex Outlet',          'Electrical',  8,  8,  _draw_outlet_duplex),
    'outlet_gfci':      ('GFCI Outlet',            'Electrical',  8,  8,  _draw_outlet_gfci),
    'outlet_220':       ('220V Outlet',            'Electrical',  8,  8,  _draw_outlet_220),
    'switch_single':    ('Switch (Single)',        'Electrical',  8,  8,  _draw_switch_single),
    'switch_3way':      ('Switch (3-Way)',         'Electrical',  8,  8,  _draw_switch_3way),
    'switch_dimmer':    ('Dimmer Switch',          'Electrical',  8,  8,  _draw_switch_dimmer),
    'panel_electric':   ('Electrical Panel',       'Electrical', 12, 24,  _draw_panel_electric),
    'light_ceiling':    ('Ceiling Light',          'Electrical', 12, 12,  _draw_light_ceiling),
    'light_recessed':   ('Recessed Can Light',     'Electrical',  8,  8,  _draw_light_recessed),
    'ceiling_fan_elec': ('Ceiling Fan',            'Electrical', 48, 48,  _draw_ceiling_fan_elec),
    'light_sconce':     ('Wall Sconce',            'Electrical',  8,  8,  _draw_light_sconce),
    'light_track':      ('Track Lighting',         'Electrical', 48,  8,  _draw_light_track),
    'smoke_detector':   ('Smoke Detector',         'Electrical',  8,  8,  _draw_smoke_detector),
    'co_detector':      ('CO Detector',            'Electrical',  8,  8,  _draw_co_detector),
    'thermostat':       ('Thermostat',             'Electrical',  5,  7,  _draw_thermostat),
    # HVAC
    'supply_register':  ('Supply Register',        'HVAC',       12,  8,  _draw_supply_register),
    'return_grille':    ('Return Grille',          'HVAC',       16, 12,  _draw_return_grille),
    'ceiling_diffuser': ('Ceiling Diffuser',       'HVAC',       12, 12,  _draw_ceiling_diffuser),
    'furnace':          ('Furnace',                'HVAC',       24, 30,  _draw_furnace),
    'air_handler':      ('Air Handler (AHU)',      'HVAC',       24, 30,  _draw_air_handler),
    'ac_condenser':     ('AC Condenser',           'HVAC',       30, 30,  _draw_ac_condenser),
    'heat_pump':        ('Heat Pump',              'HVAC',       36, 36,  _draw_heat_pump),
    'hrv_erv':          ('HRV/ERV Unit',           'HVAC',       18, 12,  _draw_hrv_erv),
    'baseboard_heater': ('Baseboard Heater',       'HVAC',       36,  4,  _draw_baseboard_heater),
    'exhaust_fan_hvac': ('Exhaust Fan',            'HVAC',       12, 12,  _draw_exhaust_fan_hvac),
    # PLUMBING
    'water_heater_tank':('Water Heater (Tank)',    'Plumbing',   18, 22,  _draw_water_heater_tank),
    'water_heater_tl':  ('Water Heater (Tankless)','Plumbing',   12, 20,  _draw_water_heater_tankless),
    'cleanout':         ('Cleanout (CO)',          'Plumbing',    8,  8,  _draw_cleanout),
    'floor_drain':      ('Floor Drain',            'Plumbing',    8,  8,  _draw_floor_drain),
    'valve_ball':       ('Ball Valve',             'Plumbing',   10,  6,  _draw_valve_ball),
    'valve_gate':       ('Gate Valve',             'Plumbing',   10,  8,  _draw_valve_gate),
    'valve_check':      ('Check Valve',            'Plumbing',   10,  8,  _draw_valve_check),
    'hose_bib':         ('Hose Bib',               'Plumbing',    8,  8,  _draw_hose_bib),
    'water_meter':      ('Water Meter',            'Plumbing',   12,  6,  _draw_water_meter),
    'sump_pump':        ('Sump Pump',              'Plumbing',   18, 18,  _draw_sump_pump),
    'p_trap':           ('P-Trap',                 'Plumbing',   10, 10,  _draw_p_trap),
    # INSULATION
    'insul_batt_24':    ('Batt 24" (2×4 stud)',   'Insulation', 24, 3.5, _draw_insul_batt),
    'insul_batt_26':    ('Batt 24" (2×6 stud)',   'Insulation', 24, 5.5, _draw_insul_batt),
    'insul_rigid_2':    ('Rigid Foam 2"',          'Insulation', 48, 2,   _draw_insul_rigid),
    'insul_rigid_4':    ('Rigid Foam 4"',          'Insulation', 48, 4,   _draw_insul_rigid),
    'insul_spray':      ('Spray Foam',             'Insulation', 24, 6,   _draw_insul_spray),
    'insul_blown':      ('Blown-In',               'Insulation', 24, 8,   _draw_insul_blown),
    # STRUCTURAL
    'fireplace':        ('Fireplace',              'Structural', 48, 18,  _draw_fireplace),
    'fireplace_corner': ('Fireplace (Corner)',     'Structural', 42, 42,  _draw_fireplace_corner),
    'column_steel':     ('Column (Steel W)',       'Structural',  8,  8,  _draw_column_steel),
    'column_wood':      ('Post/Column (Wood)',     'Structural', 5.5, 5.5,_draw_column_wood),
    'beam_steel':       ('Steel Beam',             'Structural', 96,  6,  _draw_beam_steel),
    # BEDROOM LAYOUTS
    'fp_bed_twin':      ("Twin Bedroom 9'×10'",    'Bedroom Layouts', 108, 120, _draw_fp_bed_twin),
    'fp_bed_standard':  ("Bedroom 11'×12'",        'Bedroom Layouts', 132, 144, _draw_fp_bed_standard),
    'fp_bed_large':     ("Bedroom 12'×14' +WIC",   'Bedroom Layouts', 144, 168, _draw_fp_bed_large),
    'fp_bed_master':    ("Master Bed 14'×16'",     'Bedroom Layouts', 168, 192, _draw_fp_bed_master),
    'fp_bed_master_en': ("Master+Ensuite 14'×20'", 'Bedroom Layouts', 168, 240, _draw_fp_bed_master_en),
    'fp_bed_kids':      ("Kids/Bunk 10'×12'",      'Bedroom Layouts', 120, 144, _draw_fp_bed_kids),
    # FLOOR PLANS
    'fp_home_2br_800':  ('2BR Home ~800 sqft',      'Floor Plans', 336, 360, _draw_fp_home_2br_800),
    'fp_home_2br_1000': ('2BR Home ~1000 sqft',     'Floor Plans', 408, 360, _draw_fp_home_2br_1000),
    'fp_home_3br_1200': ('3BR Home ~1200 sqft',     'Floor Plans', 432, 408, _draw_fp_home_3br_1200),
    'fp_home_3br_1400': ('3BR Home ~1400 sqft',     'Floor Plans', 480, 432, _draw_fp_home_3br_1400),
    'fp_home_4br_1800': ('4BR Home ~1800 sqft',     'Floor Plans', 528, 504, _draw_fp_home_4br_1800),
    'fp_home_4br_2000': ('4BR Open Plan ~2000 sqft','Floor Plans', 576, 528, _draw_fp_home_4br_2000),
}

# Ordered category list (controls panel display order)
FIXTURE_CATEGORIES = [
    'Kitchen', 'Bathroom', 'Bedroom', 'Living',
    'Stairs', 'Electrical', 'HVAC', 'Plumbing',
    'Insulation', 'Structural', 'Bedroom Layouts', 'Floor Plans',
]

# ── FixtureItem ────────────────────────────────────────────────────────────────

class FixtureItem(_SelectableMixin, _RotatableMixin, QGraphicsItem):
    item_type   = 'fixture'
    _ROT_OFFSET = 18   # gap above item to handle

    def __init__(self, fixture_type: str, w: float = None, h: float = None):
        QGraphicsItem.__init__(self)
        self._setup_base()
        self._rot_setup()
        self._ftype = fixture_type
        spec = FIXTURE_SPECS.get(fixture_type)
        self._w = float(w) if w is not None else float(spec[2] if spec else 24)
        self._h = float(h) if h is not None else float(spec[3] if spec else 24)
        self._update_transform_origin()

    def _update_transform_origin(self):
        """Rotate around the item centre."""
        self.setTransformOriginPoint(self._w / 2, self._h / 2)

    # ── rotation handle positions ─────────────────────────────────────────────

    def _rot_pivot_local(self) -> QPointF:
        return QPointF(self._w / 2, self._h / 2)   # centre

    def _rot_handle_local(self) -> QPointF:
        extra = self._ROT_OFFSET + self._ROT_R + 2
        return QPointF(self._w / 2, -extra)

    # ── QGraphicsItem interface ───────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        extra = self._ROT_OFFSET + self._ROT_R * 2 + 6
        return QRectF(0, -extra, self._w, self._h + extra)

    def paint(self, painter, option, widget=None):
        painter.save()
        spec = FIXTURE_SPECS.get(self._ftype)
        if spec:
            spec[4](painter, self._w, self._h, self.isSelected())
        else:
            # Unknown fixture type – draw placeholder
            painter.setPen(QPen(QColor('#ff4040'), 1))
            painter.drawRect(QRectF(0, 0, self._w, self._h))
            painter.drawText(QRectF(0, 0, self._w, self._h),
                             Qt.AlignmentFlag.AlignCenter, '?')
        # Selection highlight
        if self.isSelected():
            hp = QPen(SEL_COLOR, 1.5)
            hp.setCosmetic(True)
            hp.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(hp)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(-1, -1, self._w+2, self._h+2))
        painter.restore()
        # Rotation handle drawn outside the save/restore
        self._draw_rot_handle(painter)

    # ── Info / serialisation ──────────────────────────────────────────────────

    def info_str(self) -> str:
        spec = FIXTURE_SPECS.get(self._ftype)
        label = spec[0] if spec else self._ftype
        return f"Fixture: {label}\n  {_ft(self._w/12)} × {_ft(self._h/12)}"

    def to_dict(self) -> dict:
        p = self.pos()
        return {
            'type':         self.item_type,
            'id':           self.item_id,
            'fixture_type': self._ftype,
            'x': p.x(), 'y': p.y(),
            'w': self._w, 'h': self._h,
            'rotation':     self.rotation(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'FixtureItem':
        item = cls(d['fixture_type'], d.get('w'), d.get('h'))
        item.item_id = d['id']
        item.setPos(d.get('x', 0), d.get('y', 0))
        item.setRotation(d.get('rotation', 0))
        item._layer_idx = d.get('layer_idx', 0)
        return item
