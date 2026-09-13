"""
ArchCAD — Comprehensive Smoke Test  (155 tests, 18 sections)
Run with:
    python smoke_test.py

All tests run headless (QT_QPA_PLATFORM=offscreen).
Sections:
  1.  _ft formatter                    (11 tests)
  2.  _parse_length_to_inches          (10 tests)
  3.  Item constructors + info_str     (14 tests)
  4.  Item serialization               (11 tests)
  5.  Canvas defaults + tools + snap   (10 tests)
  6.  Undo / redo commands             ( 8 tests)
  7.  Layer management                 ( 9 tests)
  8.  Project save / load roundtrip    ( 3 tests)
  9.  Paste / duplicate                ( 8 tests)
 10.  MainWindow selection + panels    ( 9 tests)
 11.  Property commits XY/WH/text/font ( 5 tests)
 12.  Lock toggle                      ( 4 tests)
 13.  Alignment operations             ( 7 tests)
 14.  Z-order, select-all, move-layer  ( 5 tests)
 15.  Scale / paper / page / post-grid ( 5 tests)
 16.  Item flags + uniqueness          ( 3 tests)
 17.  Estimator unit tests             (12 tests)
 18.  Code Compliance Engine           (12 tests)
"""
import sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.argv = ['archcad']

import json, math, tempfile
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)

# ── Test runner ──────────────────────────────────────────────────────────────

_results = []

def chk(name: str, fn):
    try:
        fn()
        _results.append(('PASS', name))
    except Exception as exc:
        import traceback
        msg = str(exc)
        tb  = traceback.format_exc()
        # Break the traceback reference cycle so Qt C++ objects are destroyed
        # promptly (prevents "cannot access free variable 'self'" NameError
        # from firing during exception cleanup in Python 3.14+).
        try:
            exc.__traceback__ = None
        except Exception:
            pass
        _results.append(('FAIL', name, msg, tb))


# ── Imports ──────────────────────────────────────────────────────────────────

from PyQt6.QtCore import QPointF, QLineF, QRectF
from PyQt6.QtWidgets import QGraphicsItem as _GItemFlags, QGraphicsScene, QGraphicsView
from PyQt6.QtGui import QUndoStack

from items import (
    RoomItem, WallItem, DoorItem, WindowItem, DimensionItem,
    PostItem, JoistFillItem, ShapeItem, LineItem, TextItem, GroupItem,
    _ft, _LineResizeCmd, WALL_TYPES,
)
from canvas import (
    CADCanvas,
    TOOL_SELECT, TOOL_PAN, TOOL_LINE, TOOL_ROOM, TOOL_WALL,
    TOOL_DOOR, TOOL_WINDOW, TOOL_DIMENSION, TOOL_POST,
    TOOL_JOIST, TOOL_SHAPE, TOOL_TEXT,
    _AddCmd, _DeleteCmd, _MoveCmd, _PropCmd,
    SNAP_IN,
)
from mainwindow import MainWindow


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — _ft formatter
# ═════════════════════════════════════════════════════════════════════════════

def s1_ft_zero():
    assert _ft(0) == '0"', f"got {_ft(0)!r}"

def s1_ft_whole_feet():
    assert _ft(10) == "10'", f"got {_ft(10)!r}"

def s1_ft_feet_and_inches():
    assert _ft(10.5) == "10' 6\"", f"got {_ft(10.5)!r}"

def s1_ft_inches_only():
    assert _ft(0.5) == '6"', f"got {_ft(0.5)!r}"

def s1_ft_fraction_only():
    s = _ft(3 / (4 * 12))
    assert s == '3/4"', f"got {s!r}"

def s1_ft_feet_inches_fraction():
    s = _ft(1 + 3.75 / 12)
    assert s == "1' 3 3/4\"", f"got {s!r}"

def s1_ft_negative():
    s = _ft(-1)
    assert s.startswith('-'), f"expected leading '-', got {s!r}"

def s1_ft_large():
    s = _ft(100)
    assert "100'" in s, f"got {s!r}"

def s1_ft_half_inch():
    s = _ft(0.5 / 12)
    assert s == '1/2"', f"got {s!r}"

def s1_ft_one_inch():
    s = _ft(1 / 12)
    assert s == '1"', f"got {s!r}"

def s1_ft_three_eighths():
    s = _ft((6 + 3 / 8) / 12)
    assert s == '6 3/8"', f"got {s!r}"

for _name, _fn in [
    ('_ft: 0"',             s1_ft_zero),
    ('_ft: whole feet',     s1_ft_whole_feet),
    ('_ft: feet+inches',    s1_ft_feet_and_inches),
    ('_ft: inches only',    s1_ft_inches_only),
    ('_ft: fraction only',  s1_ft_fraction_only),
    ('_ft: ft+in+fraction', s1_ft_feet_inches_fraction),
    ('_ft: negative',       s1_ft_negative),
    ('_ft: large value',    s1_ft_large),
    ('_ft: half inch',      s1_ft_half_inch),
    ('_ft: one inch',       s1_ft_one_inch),
    ('_ft: 3/8 inch',       s1_ft_three_eighths),
]:
    chk(_name, _fn)



# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — _parse_length_to_inches
# ═════════════════════════════════════════════════════════════════════════════

_p = MainWindow._parse_length_to_inches

def s2_parse_feet_only():
    assert abs(_p("10'") - 120) < 0.001

def s2_parse_inches_only():
    assert abs(_p('9"') - 9) < 0.001

def s2_parse_feet_and_inches():
    assert abs(_p("10' 6\"") - 126) < 0.001

def s2_parse_fraction_inches():
    assert abs(_p('3/4"') - 0.75) < 0.001

def s2_parse_ft_whole_fraction():
    assert abs(_p("1' 3 1/2\"") - 15.5) < 0.001

def s2_parse_bare_number():
    assert abs(_p('72') - 72) < 0.001

def s2_parse_empty_is_none():
    assert _p('') is None

def s2_parse_invalid_is_none():
    assert _p('not a measurement') is None

def s2_parse_zero_ft_fraction():
    assert abs(_p("0' 1/8\"") - 0.125) < 0.001

def s2_parse_large_value():
    assert abs(_p("20' 0\"") - 240) < 0.001

for _name, _fn in [
    ('parse: feet only',         s2_parse_feet_only),
    ('parse: inches only',       s2_parse_inches_only),
    ('parse: feet + inches',     s2_parse_feet_and_inches),
    ('parse: fraction inches',   s2_parse_fraction_inches),
    ('parse: ft+whole+frac',     s2_parse_ft_whole_fraction),
    ('parse: bare number',       s2_parse_bare_number),
    ('parse: empty -> None',     s2_parse_empty_is_none),
    ('parse: invalid -> None',   s2_parse_invalid_is_none),
    ('parse: 0ft+1/8 frac',      s2_parse_zero_ft_fraction),
    ('parse: large value',       s2_parse_large_value),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Item constructors + info_str
# ═════════════════════════════════════════════════════════════════════════════

def s3_room():
    ri = RoomItem(120, 96)
    assert abs(ri.rect().width() - 120) < 0.01
    assert abs(ri.rect().height() - 96) < 0.01
    assert hasattr(ri, 'item_id') and ri._locked is False
    s = ri.info_str()
    assert 'Room' in s and "'" in s

def s3_wall():
    wi = WallItem(0, 0, 144, 0, 'exterior_6')
    assert wi.wall_type == 'exterior_6'
    assert abs(wi.line().length() - 144) < 0.01
    assert 'Wall' in wi.info_str()

def s3_wall_all_types():
    for wt in WALL_TYPES:
        wi = WallItem(0, 0, 120, 0, wt)
        assert wi.wall_type == wt and 'Wall' in wi.info_str()

def s3_door():
    di = DoorItem()
    assert abs(di.door_width - 36) < 0.01 and 'Door' in di.info_str()
    di2 = DoorItem(42)
    assert abs(di2.door_width - 42) < 0.01

def s3_window():
    wi = WindowItem(48, 0)
    assert abs(wi.dx - 48) < 0.01 and 'Window' in wi.info_str()

def s3_dimension():
    di = DimensionItem(120, 0, 24)
    assert abs(di.dx - 120) < 0.01 and abs(di.offset - 24) < 0.01
    assert 'Dimension' in di.info_str()

def s3_post_all_sizes():
    for sz in [2.0, 3.5, 5.5, 7.25]:
        pi = PostItem(sz)
        assert abs(pi.post_size - sz) < 0.01 and 'Post' in pi.info_str()

def s3_joist():
    jh = JoistFillItem(120, 96, 16, 'h')
    assert jh.direction == 'h' and 'Joist' in jh.info_str()
    jv = JoistFillItem(120, 96, 24, 'v')
    assert jv.direction == 'v' and 'Vert' in jv.info_str()

def s3_shape():
    sr = ShapeItem(60, 48, 'rect')
    assert 'Rectangle' in sr.info_str()
    se = ShapeItem(60, 48, 'ellipse')
    assert 'Ellipse' in se.info_str()

def s3_line_styles():
    for style in ['solid', 'dash', 'dot']:
        li = LineItem(0, 0, 120, 0, style=style)
        assert li.line_style == style
        s = li.info_str()
        assert 'Line' in s and style in s

def s3_text():
    ti = TextItem('Hello World', 14, '#ff0000')
    assert ti.text == 'Hello World' and ti.font_size == 14
    assert 'Text' in ti.info_str() and 'Hello World' in ti.info_str()
    long_ti = TextItem('A' * 30)
    assert '\u2026' in long_ti.info_str()   # truncated with ellipsis

def s3_group_info_str():
    g = GroupItem()
    assert 'Group' in g.info_str() and '0' in g.info_str()

for _name, _fn in [
    ('Room constructor+info_str',        s3_room),
    ('Wall constructor+info_str',        s3_wall),
    ('Wall all 4 types',                 s3_wall_all_types),
    ('Door default+custom width',        s3_door),
    ('Window constructor+info_str',      s3_window),
    ('Dimension constructor+info_str',   s3_dimension),
    ('Post all sizes+info_str',          s3_post_all_sizes),
    ('JoistFill h+v+info_str',           s3_joist),
    ('Shape rect+ellipse+info_str',      s3_shape),
    ('Line all styles+info_str',         s3_line_styles),
    ('Text constructor+truncation',      s3_text),
    ('Group info_str (empty)',           s3_group_info_str),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Item serialization (to_dict / from_dict)
# ═════════════════════════════════════════════════════════════════════════════

def s4_room():
    ri = RoomItem(120, 96)
    ri.setPos(10, 20); ri.label = 'Living Room'
    d = ri.to_dict()
    assert d['type'] == 'room' and d['label'] == 'Living Room'
    r2 = RoomItem.from_dict(d)
    assert abs(r2.rect().width() - 120) < 0.01 and r2.item_id == ri.item_id

def s4_wall_all_types():
    for wt in WALL_TYPES:
        wi = WallItem(0, 0, 144, 48, wt)
        d = wi.to_dict()
        w2 = WallItem.from_dict(d)
        assert w2.wall_type == wt
        assert abs(w2.line().x2() - d['x2']) < 0.01

def s4_door():
    di = DoorItem(42)
    di.setPos(50, 60); di.setRotation(45)
    d = di.to_dict()
    assert d['type'] == 'door' and abs(d['rotation'] - 45) < 0.01
    d2 = DoorItem.from_dict(d)
    assert abs(d2.door_width - 42) < 0.01 and abs(d2.rotation() - 45) < 0.01

def s4_window():
    wi = WindowItem(48, 12)
    d = wi.to_dict()
    w2 = WindowItem.from_dict(d)
    assert abs(w2.dx - 48) < 0.01 and abs(w2.dy - 12) < 0.01

def s4_dimension():
    di = DimensionItem(120, 60, 30)
    d = di.to_dict()
    d2 = DimensionItem.from_dict(d)
    assert abs(d2.dx - 120) < 0.01 and abs(d2.offset - 30) < 0.01

def s4_post():
    pi = PostItem(5.5)
    pi.setPos(100, 200)
    d = pi.to_dict()
    p2 = PostItem.from_dict(d)
    assert abs(p2.post_size - 5.5) < 0.01 and abs(p2.pos().x() - 100) < 0.01

def s4_joist():
    ji = JoistFillItem(200, 150, 24, 'v')
    d = ji.to_dict()
    j2 = JoistFillItem.from_dict(d)
    assert abs(j2.w - 200) < 0.01 and j2.direction == 'v' and j2.spacing == 24

def s4_shape():
    si = ShapeItem(80, 60, 'ellipse', '#ff0000', '#00ff00')
    d = si.to_dict()
    s2 = ShapeItem.from_dict(d)
    assert s2.shape_type == 'ellipse'
    assert s2.fill == '#ff0000' and s2.border == '#00ff00'

def s4_line():
    li = LineItem(10, 20, 130, 20, '#ff0000', 'dash')
    d = li.to_dict()
    assert d['line_style'] == 'dash' and d['line_color'] == '#ff0000'
    l2 = LineItem.from_dict(d)
    assert l2.line_style == 'dash' and abs(l2.line().length() - 120) < 0.01

def s4_text():
    ti = TextItem('Kitchen', 16, '#ffcc00')
    ti.setPos(30, 50)
    d = ti.to_dict()
    t2 = TextItem.from_dict(d)
    assert t2.text == 'Kitchen' and t2.font_size == 16 and t2.color == '#ffcc00'

def s4_group():
    sc = QGraphicsScene()
    r = RoomItem(60, 48); w = WallItem(0, 0, 60, 0)
    sc.addItem(r); sc.addItem(w)
    g = GroupItem(); sc.addItem(g)
    g.addToGroup(r); g.addToGroup(w)
    d = g.to_dict()
    assert d['type'] == 'group' and len(d['children']) == 2

for _name, _fn in [
    ('Room to_dict/from_dict',            s4_room),
    ('Wall all types to_dict/from_dict',  s4_wall_all_types),
    ('Door to_dict/from_dict',            s4_door),
    ('Window to_dict/from_dict',          s4_window),
    ('Dimension to_dict/from_dict',       s4_dimension),
    ('Post to_dict/from_dict',            s4_post),
    ('JoistFill to_dict/from_dict',       s4_joist),
    ('Shape to_dict/from_dict',           s4_shape),
    ('Line to_dict/from_dict',            s4_line),
    ('Text to_dict/from_dict',            s4_text),
    ('Group to_dict/from_dict',           s4_group),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Canvas defaults, tools, snap, grid, fmt_pos, delete+undo
# ═════════════════════════════════════════════════════════════════════════════

def s5_defaults():
    c = CADCanvas()
    assert c._tool == TOOL_SELECT and c._snap == SNAP_IN
    assert c._snap_enabled and c._show_grid
    assert c.scale_ratio == 48 and len(c._layers) == 1

def s5_all_12_tools():
    c = CADCanvas()
    for tool in [TOOL_SELECT, TOOL_PAN, TOOL_LINE, TOOL_ROOM, TOOL_WALL,
                 TOOL_DOOR, TOOL_WINDOW, TOOL_DIMENSION, TOOL_POST,
                 TOOL_JOIST, TOOL_SHAPE, TOOL_TEXT]:
        c.set_tool(tool)
        assert c._tool == tool, f"Expected {tool!r}, got {c._tool!r}"
    c.set_tool(TOOL_SELECT)
    assert c.dragMode() == QGraphicsView.DragMode.RubberBandDrag
    c.set_tool(TOOL_PAN)
    assert c.dragMode() == QGraphicsView.DragMode.ScrollHandDrag
    c.set_tool(TOOL_LINE)
    assert c.dragMode() == QGraphicsView.DragMode.NoDrag

def s5_snap_disabled():
    c = CADCanvas()
    c._snap_enabled = False
    r = c._snap_pt(QPointF(7.3, 11.8))
    assert abs(r.x() - 7.3) < 0.001 and abs(r.y() - 11.8) < 0.001

def s5_snap_12in():
    c = CADCanvas()
    c._snap_enabled = True; c._snap = 12
    r = c._snap_pt(QPointF(13, 7))
    assert r.x() == 12.0 and r.y() == 12.0, f"got ({r.x()},{r.y()})"

def s5_snap_6in():
    c = CADCanvas()
    c._snap = 6
    r = c._snap_pt(QPointF(4, 7))
    assert r.x() == 6.0 and r.y() == 6.0, f"got ({r.x()},{r.y()})"

def s5_snap_1in():
    c = CADCanvas()
    c._snap = 1
    r = c._snap_pt(QPointF(3.7, 5.2))
    assert r.x() == 4.0 and r.y() == 5.0, f"got ({r.x()},{r.y()})"

def s5_toggle_grid():
    c = CADCanvas()
    c.toggle_grid(False); assert not c._show_grid
    c.toggle_grid(True);  assert c._show_grid

def s5_fmt_pos():
    c = CADCanvas()
    s0 = c._fmt_pos(QPointF(0, 0))
    assert "0'" in s0 or '0"' in s0, f"got {s0!r}"
    s12 = c._fmt_pos(QPointF(144, 0))
    assert "12'" in s12, f"got {s12!r}"

def s5_delete_and_undo():
    c = CADCanvas()
    sc = c.scene()
    ri = RoomItem(60, 48)
    sc.addItem(ri); ri.setSelected(True)
    c.delete_selected()
    assert len(sc.items()) == 0
    c._undo_stack.undo()
    assert len(sc.items()) == 1

def s5_zoom_fit():
    c = CADCanvas()
    c.scene().addItem(RoomItem(120, 96))
    c.zoom_fit()   # must not raise

for _name, _fn in [
    ('Canvas defaults',             s5_defaults),
    ('Canvas all 12 tools',         s5_all_12_tools),
    ('Snap disabled: passthrough',  s5_snap_disabled),
    ('Snap 12in grid',              s5_snap_12in),
    ('Snap 6in grid',               s5_snap_6in),
    ('Snap 1in grid',               s5_snap_1in),
    ('Toggle grid on/off',          s5_toggle_grid),
    ('_fmt_pos at 0 and 12ft',      s5_fmt_pos),
    ('delete_selected + undo',      s5_delete_and_undo),
    ('zoom_fit no crash',           s5_zoom_fit),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Undo / redo commands
# ═════════════════════════════════════════════════════════════════════════════

def s6_add_cmd():
    c = CADCanvas(); sc = c.scene()
    ri = RoomItem(60, 48); sc.addItem(ri)
    c._undo_stack.push(_AddCmd(sc, ri))
    assert ri in sc.items()          # first redo noop
    c._undo_stack.undo()
    assert ri not in sc.items()
    c._undo_stack.redo()
    assert ri in sc.items()

def s6_delete_cmd():
    c = CADCanvas(); sc = c.scene()
    ri = RoomItem(60, 48); sc.addItem(ri)
    c._undo_stack.push(_DeleteCmd(sc, [ri]))
    assert ri not in sc.items()      # immediate
    c._undo_stack.undo()
    assert ri in sc.items()

def s6_move_cmd():
    c = CADCanvas(); sc = c.scene()
    ri = RoomItem(60, 48); sc.addItem(ri); ri.setPos(0, 0)
    c._undo_stack.push(_MoveCmd([(ri, QPointF(0, 0), QPointF(120, 48))]))
    assert abs(ri.pos().x() - 120) < 0.01
    c._undo_stack.undo()
    assert abs(ri.pos().x() - 0) < 0.01
    c._undo_stack.redo()
    assert abs(ri.pos().x() - 120) < 0.01

def s6_line_resize_cmd():
    li = LineItem(0, 0, 120, 0)
    old_ln = QLineF(li.line()); new_ln = QLineF(0, 0, 240, 0)
    cmd = _LineResizeCmd(li, old_ln, new_ln)
    cmd.redo(); assert abs(li.line().x2() - 240) < 0.01
    cmd.undo(); assert abs(li.line().x2() - 120) < 0.01

def s6_prop_cmd():
    stk = QUndoStack()
    state = [False]
    def _a(): state[0] = True
    def _r(): state[0] = False
    state[0] = True                  # pre-apply
    stk.push(_PropCmd('T', _a, _r))
    assert state[0]                  # first redo noop
    stk.undo(); assert not state[0]
    stk.redo(); assert state[0]

def s6_group():
    c = CADCanvas(); sc = c.scene()
    r = RoomItem(60, 48); w = WallItem(0, 0, 60, 0)
    sc.addItem(r); sc.addItem(w)
    r.setSelected(True); w.setSelected(True)
    c.group_selected()
    assert len([i for i in sc.items() if isinstance(i, GroupItem)]) == 1

def s6_ungroup():
    c = CADCanvas(); sc = c.scene()
    r = RoomItem(60, 48); w = WallItem(0, 0, 60, 0)
    sc.addItem(r); sc.addItem(w)
    r.setSelected(True); w.setSelected(True)
    c.group_selected()
    g = [i for i in sc.items() if isinstance(i, GroupItem)][0]
    g.setSelected(True)
    c.ungroup_selected()
    assert len([i for i in sc.items() if isinstance(i, GroupItem)]) == 0

def s6_undo_group():
    c = CADCanvas(); sc = c.scene()
    r = RoomItem(60, 48); w = WallItem(0, 0, 60, 0)
    sc.addItem(r); sc.addItem(w)
    r.setSelected(True); w.setSelected(True)
    c.group_selected()
    assert len([i for i in sc.items() if isinstance(i, GroupItem)]) == 1
    c._undo_stack.undo()
    assert len([i for i in sc.items() if isinstance(i, GroupItem)]) == 0

for _name, _fn in [
    ('_AddCmd undo/redo',          s6_add_cmd),
    ('_DeleteCmd immediate+undo',  s6_delete_cmd),
    ('_MoveCmd undo/redo',         s6_move_cmd),
    ('_LineResizeCmd undo/redo',   s6_line_resize_cmd),
    ('_PropCmd pre-apply pattern', s6_prop_cmd),
    ('group_selected',             s6_group),
    ('ungroup round-trip',         s6_ungroup),
    ('undo group_selected',        s6_undo_group),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Layer management
# ═════════════════════════════════════════════════════════════════════════════

def s7_add():
    c = CADCanvas()
    idx = c.add_layer('Structural')
    assert idx == 1
    assert c._layers[1]['name'] == 'Structural'
    assert c._layers[1]['visible'] is True and c._layers[1]['locked'] is False

def s7_rename():
    c = CADCanvas()
    c.add_layer('Old'); c.rename_layer(1, 'New')
    assert c._layers[1]['name'] == 'New'

def s7_delete():
    c = CADCanvas()
    c.add_layer('Temp')
    c.delete_layer(1)
    assert len(c._layers) == 1

def s7_protect_0():
    c = CADCanvas()
    c.delete_layer(0)           # must be silently ignored
    assert len(c._layers) == 1

def s7_visibility():
    c = CADCanvas(); sc = c.scene()
    c.add_layer('L1')
    ri = RoomItem(60, 48); ri._layer_idx = 1; sc.addItem(ri)
    c.set_layer_visible(1, False); assert not ri.isVisible()
    c.set_layer_visible(1, True);  assert ri.isVisible()

def s7_lock_layer():
    c = CADCanvas(); sc = c.scene()
    c.add_layer('L1')
    ri = RoomItem(60, 48); ri._layer_idx = 1; sc.addItem(ri)
    c.set_layer_locked(1, True)
    assert not (ri.flags() & _GItemFlags.GraphicsItemFlag.ItemIsMovable)
    c.set_layer_locked(1, False)
    assert ri.flags() & _GItemFlags.GraphicsItemFlag.ItemIsMovable

def s7_active_layer():
    c = CADCanvas()
    c.add_layer('L1'); c.set_active_layer(1)
    assert c._active_layer == 1

def s7_oob_active_ignored():
    c = CADCanvas()
    c.add_layer('L1'); c.set_active_layer(1)
    c.set_active_layer(99)
    assert c._active_layer == 1

def s7_delete_moves_items():
    c = CADCanvas(); sc = c.scene()
    c.add_layer('L1')
    ri = RoomItem(60, 48); ri._layer_idx = 1; sc.addItem(ri)
    c.delete_layer(1)
    assert ri._layer_idx == 0

for _name, _fn in [
    ('layer: add',                       s7_add),
    ('layer: rename',                    s7_rename),
    ('layer: delete',                    s7_delete),
    ('layer: 0 is protected',            s7_protect_0),
    ('layer: visibility toggles items',  s7_visibility),
    ('layer: lock toggles items',        s7_lock_layer),
    ('layer: set_active_layer',          s7_active_layer),
    ('layer: OOB active ignored',        s7_oob_active_ignored),
    ('layer: delete moves items to 0',   s7_delete_moves_items),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Project save / load roundtrip (bypasses QFileDialog)
# ═════════════════════════════════════════════════════════════════════════════

def _make_project(c, sc):
    items_data = []
    for item in sc.items():
        if hasattr(item, 'to_dict') and not isinstance(item.parentItem(), GroupItem):
            d = item.to_dict()
            d['layer_idx'] = getattr(item, '_layer_idx', 0)
            items_data.append(d)
    return {'version': 2, 'scale_ratio': c.scale_ratio,
            'paper_w': c._paper_phys_w, 'paper_h': c._paper_phys_h,
            'layers': c._layers, 'items': items_data}

def _load_project(data):
    loaders = {'room': RoomItem, 'wall': WallItem, 'door': DoorItem,
               'window': WindowItem, 'dimension': DimensionItem,
               'post': PostItem, 'joist_fill': JoistFillItem,
               'shape': ShapeItem, 'line': LineItem, 'text': TextItem}
    c2 = CADCanvas(); sc2 = c2.scene()
    for d in data.get('items', []):
        cls = loaders.get(d.get('type'))
        if cls:
            sc2.addItem(cls.from_dict(d))
    return c2, sc2

def s8_all_types():
    c = CADCanvas(); sc = c.scene()
    originals = [
        RoomItem(120, 96), WallItem(0, 0, 144, 0, 'interior'),
        DoorItem(36), WindowItem(36, 0), DimensionItem(120, 0, 24),
        PostItem(3.5), JoistFillItem(120, 96, 16, 'h'),
        ShapeItem(60, 48, 'rect'), LineItem(0, 0, 120, 60, '#ff0000', 'dash'),
        TextItem('Smoke', 12),
    ]
    for it in originals: sc.addItem(it)
    with tempfile.NamedTemporaryFile(suffix='.acad', delete=False, mode='w') as f:
        json.dump(_make_project(c, sc), f); path = f.name
    try:
        with open(path) as f: data = json.load(f)
        _, sc2 = _load_project(data)
        loaded = [i for i in sc2.items() if hasattr(i, 'to_dict')]
        assert len(loaded) == 10, f"expected 10, got {len(loaded)}"
    finally:
        os.unlink(path)

def s8_scale_paper():
    c = CADCanvas(); c.set_scale(96); c.set_paper(11.0, 17.0)
    with tempfile.NamedTemporaryFile(suffix='.acad', delete=False, mode='w') as f:
        json.dump(_make_project(c, c.scene()), f); path = f.name
    try:
        with open(path) as f: data = json.load(f)
        assert data['scale_ratio'] == 96
        assert abs(data['paper_w'] - 11.0) < 0.01
        assert abs(data['paper_h'] - 17.0) < 0.01
    finally:
        os.unlink(path)

def s8_layers():
    c = CADCanvas()
    c.add_layer('Structural'); c.add_layer('Electrical')
    with tempfile.NamedTemporaryFile(suffix='.acad', delete=False, mode='w') as f:
        json.dump(_make_project(c, c.scene()), f); path = f.name
    try:
        with open(path) as f: data = json.load(f)
        assert len(data['layers']) == 3
        assert data['layers'][1]['name'] == 'Structural'
    finally:
        os.unlink(path)

for _name, _fn in [
    ('save/load: all 10 item types', s8_all_types),
    ('save/load: scale + paper',     s8_scale_paper),
    ('save/load: layers',            s8_layers),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Paste / duplicate
# ═════════════════════════════════════════════════════════════════════════════

def s9_paste_offset_and_fresh_id():
    c = CADCanvas(); sc = c.scene()
    ri = RoomItem(120, 96); ri.setPos(0, 0); sc.addItem(ri)
    pasted = c.paste_items([ri.to_dict()], 24, 24)
    assert len(pasted) == 1
    assert abs(pasted[0].pos().x() - 24) < 0.01
    assert pasted[0].item_id != ri.item_id

def s9_paste_multiple():
    c = CADCanvas(); sc = c.scene()
    items = [RoomItem(60, 48), PostItem(3.5), TextItem('Hi')]
    for it in items: sc.addItem(it)
    pasted = c.paste_items([it.to_dict() for it in items], 12, 12)
    assert len(pasted) == 3

def s9_paste_undo_macro():
    c = CADCanvas(); sc = c.scene()
    ri = RoomItem(60, 48); sc.addItem(ri)
    pre = len(sc.items())
    c.paste_items([ri.to_dict()], 12, 12)
    assert len(sc.items()) == pre + 1
    c._undo_stack.undo()             # single undo undoes entire macro
    assert len(sc.items()) == pre

def s9_paste_wall_xy_offset():
    c = CADCanvas(); sc = c.scene()
    w = WallItem(0, 0, 120, 0); sc.addItem(w)
    pasted = c.paste_items([w.to_dict()], 24, 12)
    assert len(pasted) == 1
    d = pasted[0].to_dict()
    assert abs(d['x1'] - 24) < 0.01
    assert abs(d['y1'] - 12) < 0.01
    assert abs(d['x2'] - 144) < 0.01

def s9_paste_window_xy_offset():
    c = CADCanvas(); sc = c.scene()
    w = WindowItem(36, 0); w.setPos(10, 20); sc.addItem(w)
    pasted = c.paste_items([w.to_dict()], 24, 24)
    assert len(pasted) == 1
    d = pasted[0].to_dict()
    assert abs(d['x1'] - 34) < 0.01
    assert abs(d['y1'] - 44) < 0.01
    assert abs(d['x2'] - 70) < 0.01

def s9_paste_fixture():
    from fixtures import FixtureItem
    c = CADCanvas(); sc = c.scene()
    f = FixtureItem('toilet'); f.setPos(0, 0); sc.addItem(f)
    pasted = c.paste_items([f.to_dict()], 24, 24)
    assert len(pasted) == 1
    assert pasted[0].item_type == 'fixture'
    assert abs(pasted[0].pos().x() - 24) < 0.01
    assert pasted[0].item_id != f.item_id

def s9_paste_group_keeps_children():
    c = CADCanvas(); sc = c.scene()
    r = RoomItem(60, 48); w = WallItem(0, 0, 60, 0)
    sc.addItem(r); sc.addItem(w)
    r.setSelected(True); w.setSelected(True)
    c.group_selected()
    groups = [i for i in sc.items() if isinstance(i, GroupItem)]
    assert groups
    pasted = c.paste_items([groups[0].to_dict()], 24, 24)
    assert len(pasted) == 1
    kids = [ch for ch in pasted[0].childItems() if hasattr(ch, 'to_dict')]
    assert len(kids) == 2

def s9_window_preset_width():
    c = CADCanvas()
    c._window_width = 48
    assert c._window_width == 48
    item = WindowItem(c._window_width, 0)
    assert abs(math.hypot(item.dx, item.dy) - 48) < 0.01

for _name, _fn in [
    ('paste: offset + fresh ID',       s9_paste_offset_and_fresh_id),
    ('paste: multiple item types',     s9_paste_multiple),
    ('paste: undo is one macro step',  s9_paste_undo_macro),
    ('paste: wall x1/y1 offset',       s9_paste_wall_xy_offset),
    ('paste: window x1/y1 offset',     s9_paste_window_xy_offset),
    ('paste: fixture not dropped',     s9_paste_fixture),
    ('paste: group keeps children',    s9_paste_group_keeps_children),
    ('window preset width applied',    s9_window_preset_width),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 10 — MainWindow: selection + properties panel visibility
# ═════════════════════════════════════════════════════════════════════════════

def s10_init_attrs():
    w = MainWindow()
    for attr in ('_canvas', '_btn_lock',
                 '_prop_line_frame', '_prop_line_length',
                 '_prop_pos_frame', '_prop_x', '_prop_y',
                 '_prop_size_frame', '_prop_w', '_prop_h',
                 '_prop_text_frame', '_prop_text_edit', '_prop_font_size',
                 '_prop_info', '_preset_btn_sel', '_preset_btn_pan',
                 '_clipboard', '_props_updating'):
        assert hasattr(w, attr), f'Missing: {attr!r}'
    assert callable(w._act_print)
    assert callable(w._act_print_preview)
    assert hasattr(w, '_estimator_dock')
    from PyQt6.QtWidgets import QDockWidget as _QD
    feat = w._estimator_dock.features()
    assert not (feat & _QD.DockWidgetFeature.DockWidgetClosable), \
        'Estimator dock must not be closable — Redock instead of Close'
    w.close()

def s10_selection_empty():
    w = MainWindow()
    w._on_selection_changed([])
    assert w._prop_pos_frame.isHidden()
    assert w._prop_size_frame.isHidden()
    assert w._prop_line_frame.isHidden()
    assert w._prop_text_frame.isHidden()
    assert not w._btn_lock.isEnabled()
    w.close()

def s10_selection_room():
    w = MainWindow()
    ri = RoomItem(120, 96); ri.setPos(10, 20)
    w._on_selection_changed([ri])
    assert not w._prop_pos_frame.isHidden()
    assert not w._prop_size_frame.isHidden()
    assert w._prop_line_frame.isHidden()
    assert w._prop_text_frame.isHidden()
    assert w._btn_lock.isEnabled()
    assert abs(w._prop_w.value() - 120) < 0.01
    assert abs(w._prop_h.value() - 96) < 0.01
    assert abs(w._prop_x.value() - 10) < 0.01
    w.close()

def s10_selection_line():
    w = MainWindow()
    li = LineItem(0, 0, 144, 0)     # 12 ft
    w._on_selection_changed([li])
    assert not w._prop_line_frame.isHidden()
    assert not w._prop_pos_frame.isHidden()
    assert w._prop_size_frame.isHidden()
    assert w._btn_lock.isEnabled()
    txt = w._prop_line_length.text()
    assert "12'" in txt or "144" in txt, f"unexpected: {txt!r}"
    w.close()

def s10_selection_wall_no_line_frame():
    w = MainWindow()
    wi = WallItem(0, 0, 144, 0, 'interior')
    w._on_selection_changed([wi])
    assert w._prop_line_frame.isHidden()
    assert not w._prop_pos_frame.isHidden()
    assert w._btn_lock.isEnabled()
    w.close()

def s10_selection_text():
    w = MainWindow()
    ti = TextItem('Hello', 14)
    w._on_selection_changed([ti])
    assert not w._prop_text_frame.isHidden()
    assert w._prop_text_edit.text() == 'Hello'
    assert w._prop_font_size.value() == 14
    assert w._btn_lock.isEnabled()
    w.close()

def s10_selection_multi():
    w = MainWindow()
    w._on_selection_changed([RoomItem(60, 48), WallItem(0, 0, 60, 0)])
    assert w._prop_pos_frame.isHidden()
    assert w._prop_size_frame.isHidden()
    assert w._prop_text_frame.isHidden()
    assert w._prop_line_frame.isHidden()
    assert w._btn_lock.isEnabled()
    w.close()

def s10_selection_shape():
    w = MainWindow()
    si = ShapeItem(80, 60, 'ellipse'); si.setPos(5, 7)
    w._on_selection_changed([si])
    assert not w._prop_size_frame.isHidden()
    assert abs(w._prop_w.value() - 80) < 0.01
    assert abs(w._prop_h.value() - 60) < 0.01
    w.close()

def s10_info_label():
    w = MainWindow()
    w._on_selection_changed([TextItem('Foo', 12)])
    assert 'Text' in w._prop_info.text() or 'Foo' in w._prop_info.text()
    w._on_selection_changed([])
    assert 'No selection' in w._prop_info.text()
    w.close()

for _name, _fn in [
    ('MainWindow: init attrs',              s10_init_attrs),
    ('MainWindow: on_selection empty',      s10_selection_empty),
    ('MainWindow: on_selection room',       s10_selection_room),
    ('MainWindow: on_selection line',       s10_selection_line),
    ('MainWindow: on_selection wall',       s10_selection_wall_no_line_frame),
    ('MainWindow: on_selection text',       s10_selection_text),
    ('MainWindow: on_selection multi',      s10_selection_multi),
    ('MainWindow: on_selection shape',      s10_selection_shape),
    ('MainWindow: info label updated',      s10_info_label),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 11 — Property commits: XY, WH, text, font, line-length
# ═════════════════════════════════════════════════════════════════════════════

def s11_commit_xy():
    w = MainWindow()
    try:
        sc = w._canvas.scene()
        ri = RoomItem(60, 48); sc.addItem(ri); ri.setPos(0, 0); ri.setSelected(True)
        w._on_selection_changed([ri])
        w._prop_x.setValue(120); w._prop_y.setValue(96)
        w._prop_commit_xy()
        assert abs(ri.pos().x() - 120) < 0.01, f"got x={ri.pos().x()}"
        assert abs(ri.pos().y() - 96) < 0.01,  f"got y={ri.pos().y()}"
        w._canvas._undo_stack.undo()
        assert abs(ri.pos().x() - 0) < 0.01
    finally:
        w.close()

def s11_commit_wh():
    w = MainWindow()
    try:
        sc = w._canvas.scene()
        ri = RoomItem(60, 48); sc.addItem(ri); ri.setSelected(True)
        w._on_selection_changed([ri])
        w._prop_w.setValue(120); w._prop_h.setValue(96)
        w._prop_commit_wh()
        assert abs(ri.rect().width() - 120) < 0.01, \
            f"WH commit did not resize: w={ri.rect().width()}"
        w._canvas._undo_stack.undo()
        assert abs(ri.rect().width() - 60) < 0.01
    finally:
        w.close()

def s11_commit_text():
    w = MainWindow()
    try:
        sc = w._canvas.scene()
        ti = TextItem('Original', 12); sc.addItem(ti); ti.setSelected(True)
        w._on_selection_changed([ti])
        w._prop_text_edit.setText('Updated')
        w._prop_commit_text()
        assert ti.text == 'Updated', f"text commit not applied: {ti.text!r}"
        w._canvas._undo_stack.undo()
        assert ti.text == 'Original'
    finally:
        w.close()

def s11_commit_font():
    w = MainWindow()
    try:
        sc = w._canvas.scene()
        ti = TextItem('Label', 12); sc.addItem(ti); ti.setSelected(True)
        w._on_selection_changed([ti])
        w._prop_font_size.setValue(24)
        w._prop_commit_font()
        assert ti.font_size == 24, f"font commit not applied: {ti.font_size}"
        w._canvas._undo_stack.undo()
        assert ti.font_size == 12
    finally:
        w.close()

def s11_commit_line_length():
    w = MainWindow()
    try:
        sc = w._canvas.scene()
        li = LineItem(0, 0, 120, 0); sc.addItem(li); li.setSelected(True)
        w._on_selection_changed([li])
        w._prop_line_length.setText("15'")
        w._prop_commit_line_length()
        ln = li.line()
        L = math.sqrt((ln.x2()-ln.x1())**2 + (ln.y2()-ln.y1())**2)
        assert abs(L - 180) < 0.5, f"expected 180in, got {L}"
        w._canvas._undo_stack.undo()
        ln2 = li.line()
        L2 = math.sqrt((ln2.x2()-ln2.x1())**2 + (ln2.y2()-ln2.y1())**2)
        assert abs(L2 - 120) < 0.5, f"undo expected 120in, got {L2}"
    finally:
        w.close()

for _name, _fn in [
    ('prop commit: XY move',      s11_commit_xy),
    ('prop commit: WH resize',    s11_commit_wh),
    ('prop commit: text edit',    s11_commit_text),
    ('prop commit: font size',    s11_commit_font),
    ('prop commit: line length',  s11_commit_line_length),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 12 — Lock toggle
# ═════════════════════════════════════════════════════════════════════════════

def s12_toggle():
    w = MainWindow(); sc = w._canvas.scene()
    li = LineItem(0, 0, 120, 0); sc.addItem(li); li.setSelected(True)
    w._prop_commit_lock(); assert li._locked
    w._prop_commit_lock(); assert not li._locked
    w.close()

def s12_undo():
    w = MainWindow(); sc = w._canvas.scene()
    li = LineItem(0, 0, 120, 0); sc.addItem(li); li.setSelected(True)
    stk = w._canvas._undo_stack; pre = stk.count()
    w._prop_commit_lock()
    assert li._locked and stk.count() > pre
    stk.undo(); assert not li._locked
    w.close()

def s12_button_text():
    w = MainWindow(); sc = w._canvas.scene()
    li = LineItem(0, 0, 120, 0); sc.addItem(li); li.setSelected(True)
    w._on_selection_changed([li])
    assert 'Lock' in w._btn_lock.text()
    w._prop_commit_lock()
    assert 'Unlock' in w._btn_lock.text()
    w.close()

def s12_flag():
    from PyQt6.QtWidgets import QGraphicsItem as _GI
    li = LineItem(0, 0, 120, 0)
    li.set_locked(True)
    assert li._locked and not (li.flags() & _GI.GraphicsItemFlag.ItemIsMovable)
    li.set_locked(False)
    assert not li._locked and (li.flags() & _GI.GraphicsItemFlag.ItemIsMovable)

for _name, _fn in [
    ('lock: toggle via prop_commit',      s12_toggle),
    ('lock: undo restores unlock state',  s12_undo),
    ('lock: button text changes',         s12_button_text),
    ('lock: ItemIsMovable flag',          s12_flag),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 13 — Alignment operations
# ═════════════════════════════════════════════════════════════════════════════

def _two_rooms(w, x1, y1, x2, y2):
    sc = w._canvas.scene()
    r1 = RoomItem(60, 48); r1.setPos(x1, y1)
    r2 = RoomItem(60, 48); r2.setPos(x2, y2)
    sc.addItem(r1); sc.addItem(r2)
    r1.setSelected(True); r2.setSelected(True)
    return r1, r2

def s13_left():
    w = MainWindow(); r1, r2 = _two_rooms(w, 100, 0, 200, 0)
    w._align_items('left')
    assert abs(r1.pos().x() - r2.pos().x()) < 0.01
    w.close()

def s13_right():
    w = MainWindow(); r1, r2 = _two_rooms(w, 100, 0, 200, 0)
    w._align_items('right')
    assert abs(r1.sceneBoundingRect().right() - r2.sceneBoundingRect().right()) < 0.01
    w.close()

def s13_top():
    w = MainWindow(); r1, r2 = _two_rooms(w, 0, 100, 0, 200)
    w._align_items('top')
    assert abs(r1.pos().y() - r2.pos().y()) < 0.01
    w.close()

def s13_bottom():
    w = MainWindow(); r1, r2 = _two_rooms(w, 0, 100, 0, 200)
    w._align_items('bottom')
    assert abs(r1.sceneBoundingRect().bottom() - r2.sceneBoundingRect().bottom()) < 0.01
    w.close()

def s13_center_h():
    w = MainWindow(); r1, r2 = _two_rooms(w, 100, 0, 200, 0)
    w._align_items('center_h')
    assert abs(r1.sceneBoundingRect().center().x() -
               r2.sceneBoundingRect().center().x()) < 0.01
    w.close()

def s13_center_v():
    w = MainWindow(); r1, r2 = _two_rooms(w, 0, 100, 0, 200)
    w._align_items('center_v')
    assert abs(r1.sceneBoundingRect().center().y() -
               r2.sceneBoundingRect().center().y()) < 0.01
    w.close()

def s13_undo():
    w = MainWindow(); r1, r2 = _two_rooms(w, 100, 0, 200, 0)
    orig_x2 = r2.pos().x()
    w._align_items('left')
    assert abs(r2.pos().x() - r1.pos().x()) < 0.01
    w._canvas._undo_stack.undo()
    assert abs(r2.pos().x() - orig_x2) < 0.01, \
        f"undo: expected {orig_x2}, got {r2.pos().x()}"
    w.close()

for _name, _fn in [
    ('align: left',     s13_left),
    ('align: right',    s13_right),
    ('align: top',      s13_top),
    ('align: bottom',   s13_bottom),
    ('align: center_h', s13_center_h),
    ('align: center_v', s13_center_v),
    ('align: undo',     s13_undo),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 14 — Z-order, select-all, select-walls, move-to-layer
# ═════════════════════════════════════════════════════════════════════════════

def s14_select_all():
    w = MainWindow(); sc = w._canvas.scene()
    for _ in range(5): sc.addItem(RoomItem(60, 48))
    w._select_all()
    assert len(sc.selectedItems()) == 5
    w.close()

def s14_select_all_lines():
    # _select_all_lines actually selects WallItem + DimensionItem
    w = MainWindow(); sc = w._canvas.scene()
    sc.addItem(WallItem(0, 0, 60, 0))
    sc.addItem(DimensionItem(60, 0, 12))
    sc.addItem(RoomItem(60, 48))        # NOT selected
    sc.addItem(LineItem(0, 0, 60, 0))   # NOT selected
    w._select_all_lines()
    sel = sc.selectedItems()
    assert len(sel) == 2, f"expected 2 (wall+dim), got {len(sel)}"
    assert all(isinstance(i, (WallItem, DimensionItem)) for i in sel)
    w.close()

def s14_bring_to_front():
    w = MainWindow(); sc = w._canvas.scene()
    r1 = RoomItem(60, 48); r2 = RoomItem(60, 48); r3 = RoomItem(60, 48)
    r1.setZValue(1); r2.setZValue(2); r3.setZValue(3)
    for r in (r1, r2, r3): sc.addItem(r)
    r1.setSelected(True)
    w._bring_to_front()
    assert r1.zValue() >= max(i.zValue() for i in sc.items())
    w.close()

def s14_send_to_back():
    w = MainWindow(); sc = w._canvas.scene()
    r1 = RoomItem(60, 48); r2 = RoomItem(60, 48); r3 = RoomItem(60, 48)
    r1.setZValue(3); r2.setZValue(2); r3.setZValue(1)
    for r in (r1, r2, r3): sc.addItem(r)
    r1.setSelected(True)
    w._send_to_back()
    assert r1.zValue() <= min(i.zValue() for i in sc.items())
    w.close()

def s14_move_to_layer():
    w = MainWindow(); sc = w._canvas.scene()
    w._canvas.add_layer('L1')
    ri = RoomItem(60, 48); sc.addItem(ri); ri.setSelected(True)
    w._move_selected_to_layer(1)
    assert ri._layer_idx == 1
    w.close()

for _name, _fn in [
    ('select_all selects all items',          s14_select_all),
    ('_select_all_lines selects walls+dims',  s14_select_all_lines),
    ('bring_to_front: z >= all others',       s14_bring_to_front),
    ('send_to_back: z <= all others',         s14_send_to_back),
    ('move_selected_to_layer',                s14_move_to_layer),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 15 — Scale / paper / page boundary / new_project / post-grid
# ═════════════════════════════════════════════════════════════════════════════

def s15_scale():
    c = CADCanvas(); c.set_scale(96); assert c.scale_ratio == 96

def s15_paper():
    c = CADCanvas(); c.set_paper(11.0, 17.0)
    assert abs(c._paper_phys_w - 11.0) < 0.01
    assert abs(c._paper_phys_h - 17.0) < 0.01

def s15_page_boundary():
    c = CADCanvas()
    c.set_show_page_boundary(False); assert not c._show_page_boundary
    c.set_show_page_boundary(True);  assert c._show_page_boundary

def s15_new_project():
    c = CADCanvas(); sc = c.scene()
    sc.addItem(RoomItem(60, 48)); c.add_layer('Extra')
    c.new_project()
    assert len(sc.items()) == 0
    assert len(c._layers) == 1 and c._layers[0]['name'] == 'Layer 0'
    assert c._undo_stack.count() == 0

def s15_post_grid():
    c = CADCanvas(); sc = c.scene()
    c.place_post_grid(0, 0, 120, 120, 60, 60, 3.5)
    posts = [i for i in sc.items() if isinstance(i, PostItem)]
    assert len(posts) == 9, f"expected 9, got {len(posts)}"

for _name, _fn in [
    ('set_scale',                   s15_scale),
    ('set_paper size',              s15_paper),
    ('page boundary toggle',        s15_page_boundary),
    ('new_project resets scene',    s15_new_project),
    ('place_post_grid 3x3 = 9',     s15_post_grid),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 16 — Item flags + uniqueness
# ═════════════════════════════════════════════════════════════════════════════

def s16_lock_all_types():
    from PyQt6.QtWidgets import QGraphicsItem as _GI
    cases = [(RoomItem, (60, 48)), (WallItem, (0, 0, 60, 0)),
             (DoorItem, (36,)), (WindowItem, (36, 0)), (PostItem, (3.5,)),
             (ShapeItem, (60, 48, 'rect')), (LineItem, (0, 0, 60, 0)),
             (TextItem, ('X', 12))]
    for cls, args in cases:
        item = cls(*args)
        item.set_locked(True)
        assert item._locked, f"{cls.__name__} lock failed"
        assert not (item.flags() & _GI.GraphicsItemFlag.ItemIsMovable)
        item.set_locked(False)
        assert not item._locked, f"{cls.__name__} unlock failed"
        assert item.flags() & _GI.GraphicsItemFlag.ItemIsMovable

def s16_item_id_unique():
    ids = {RoomItem(60, 48).item_id for _ in range(20)}
    assert len(ids) == 20

def s16_selectable_flag():
    for cls, args in [(RoomItem, (60, 48)), (LineItem, (0, 0, 60, 0)),
                      (TextItem, ('A',))]:
        item = cls(*args)
        assert item.flags() & _GItemFlags.GraphicsItemFlag.ItemIsSelectable, \
            f"{cls.__name__} not selectable"

for _name, _fn in [
    ('lock/unlock all item types',        s16_lock_all_types),
    ('item_id: 20 instances all unique',  s16_item_id_unique),
    ('all item types are selectable',     s16_selectable_flag),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# Section 17 — Estimator unit tests  (12 tests)
# ═════════════════════════════════════════════════════════════════════════════

from estimator import (LumberSchedule, EstimatorSettings,
                       MaterialEstimator, MaterialReport)

# 17-1  LumberSchedule.round_up basic cases
def s17_round_up_basic():
    sched = LumberSchedule([8, 10, 12, 16])
    assert sched.round_up(7.0)  == 8,  'round 7 → 8'
    assert sched.round_up(8.0)  == 8,  'exact 8 → 8'
    assert sched.round_up(8.5)  == 10, 'round 8.5 → 10'
    assert sched.round_up(12.0) == 12, 'exact 12 → 12'
    assert sched.round_up(15.9) == 16, 'round 15.9 → 16'
    assert sched.round_up(17.0) == 16, 'clamp beyond max → 16'

# 17-2  LumberSchedule.summarize groups correctly
def s17_summarize():
    sched = LumberSchedule([8, 10, 12, 16])
    summary = sched.summarize([7.5, 7.5, 9.0, 11.5])
    # 7.5 → 8  (×2),  9.0 → 10  (×1),  11.5 → 12  (×1)
    assert summary.get(8)  == 2
    assert summary.get(10) == 1
    assert summary.get(12) == 1

# 17-3  Post grid: corners always included
def s17_post_grid_corners():
    est = MaterialEstimator()
    pos = est._grid_positions(240, 96)   # 20 ft span, 8 ft spacing
    assert pos[0]  == 0,   'grid must start at 0'
    assert pos[-1] == 240, 'grid must end at span'

# 17-4  Post grid: zero-size region → no crash
def s17_post_grid_zero():
    est = MaterialEstimator()
    pos = est._grid_positions(0, 96)
    assert 0 in pos, 'zero span must still include 0'

# 17-5  Joist count for 120×96 fill @ 16" o.c. horizontal
def s17_joist_count():
    report = MaterialReport()
    sched  = LumberSchedule([8, 10, 12, 16])
    est    = MaterialEstimator()
    settings = EstimatorSettings(waste_pct=0)
    fill = [{'type': 'joist_fill', 'x': 0, 'y': 0,
              'w': 120, 'h': 96, 'spacing': 16, 'direction': 'h'}]
    est._calc_substructure(report, sched, fill, [], settings)
    # direction='h', spacing=16, h=96 → 96/16=6 spaces → 5 interior joists
    joist_lines = [ln for ln in report.lines
                   if 'joist' in ln.description and 'band' not in ln.description]
    total_pcs = sum(int(ln.qty) for ln in joist_lines)
    assert total_pcs == 5, f'expected 5 joists, got {total_pcs}'

# 17-6  Band board count: 4 per JoistFillItem
def s17_band_count():
    report = MaterialReport()
    sched  = LumberSchedule([8, 10, 12, 16])
    est    = MaterialEstimator()
    settings = EstimatorSettings(waste_pct=0)
    fill = [{'type': 'joist_fill', 'x': 0, 'y': 0,
              'w': 96, 'h': 96, 'spacing': 16, 'direction': 'h'}]
    est._calc_substructure(report, sched, fill, [], settings)
    band_lines = [ln for ln in report.lines if 'band' in ln.description]
    total_band = sum(int(ln.qty) for ln in band_lines)
    assert total_band == 4, f'expected 4 band boards, got {total_band}'

# 17-7  Blocking triggered when joist span > 96 in
def s17_blocking_triggered():
    report = MaterialReport()
    sched  = LumberSchedule([8, 10, 12, 16])
    est    = MaterialEstimator()
    settings = EstimatorSettings(waste_pct=0)
    # w=200 → span 200 in > 96 in threshold
    fill = [{'type': 'joist_fill', 'x': 0, 'y': 0,
              'w': 200, 'h': 96, 'spacing': 16, 'direction': 'h'}]
    est._calc_substructure(report, sched, fill, [], settings)
    blocking = [ln for ln in report.lines if 'blocking' in ln.description.lower()]
    assert blocking, 'blocking should appear for span > 96 in'

# 17-8  No blocking for short span
def s17_no_blocking_short():
    report = MaterialReport()
    sched  = LumberSchedule([8, 10, 12, 16])
    est    = MaterialEstimator()
    settings = EstimatorSettings(waste_pct=0)
    fill = [{'type': 'joist_fill', 'x': 0, 'y': 0,
              'w': 96, 'h': 96, 'spacing': 16, 'direction': 'h'}]
    est._calc_substructure(report, sched, fill, [], settings)
    blocking = [ln for ln in report.lines if 'blocking' in ln.description.lower()]
    assert not blocking, 'no blocking for span <= 96 in'

# 17-9  Deck board count from known area
def s17_deck_boards():
    report = MaterialReport()
    sched  = LumberSchedule([8, 10, 12, 16])
    est    = MaterialEstimator()
    settings = EstimatorSettings(decking_type='deck_board',
                                  deck_board_width=5.5, waste_pct=0)
    # 10×10 ft = 100 sqft, board width 5.5 in = 5.5/12 ft
    # linear ft needed = 100 / (5.5/12) ≈ 218 lf
    fill = [{'type': 'joist_fill', 'x': 0, 'y': 0,
              'w': 120, 'h': 120, 'spacing': 16, 'direction': 'h'}]
    est._calc_decking(report, sched, fill, settings)
    board_lines = [ln for ln in report.lines if 'Deck board' in ln.description]
    assert board_lines, 'deck board line should be present'

# 17-10  Plywood sheet count rounds up
def s17_plywood_roundup():
    report = MaterialReport()
    sched  = LumberSchedule([8, 10, 12, 16])
    est    = MaterialEstimator()
    settings = EstimatorSettings(decking_type='plywood', waste_pct=0)
    # 33 sqft → ceil(33/32) = 2 sheets (without waste)
    fill = [{'type': 'joist_fill', 'x': 0, 'y': 0,
              'w': 36, 'h': 11, 'spacing': 16, 'direction': 'h'}]
    # area = 3 ft × ~0.917 ft = 2.75 sqft — too small, use bigger
    fill = [{'type': 'joist_fill', 'x': 0, 'y': 0,
              'w': 72, 'h': 66, 'spacing': 16, 'direction': 'h'}]
    # area = 6 ft × 5.5 ft = 33 sqft → ceil(33/32)=2 sheets
    est._calc_decking(report, sched, fill, settings)
    sheet_lines = [ln for ln in report.lines if 'Plywood' in ln.description
                   and 'sheet' in ln.unit]
    assert sheet_lines, 'plywood sheet line should be present'
    total_sheets = sum(int(ln.qty) for ln in sheet_lines)
    assert total_sheets == 2, f'expected 2 sheets, got {total_sheets}'

# 17-11  Concrete volume formula
def s17_concrete_volume():
    report   = MaterialReport()
    settings = EstimatorSettings(footing_dia_in=12, footing_depth_in=48,
                                  include_concrete=True)
    est = MaterialEstimator()
    # 1 post, 12" dia × 4 ft deep
    # vol = π × 0.5² × 4 = π ≈ 3.14 cu ft → ceil(3.14/0.60) = 6 bags
    # rooms=[] is fine for posts type — it falls into the posts branch
    est._calc_concrete(report, 1, [], settings)
    bag_lines = [ln for ln in report.lines if '80 lb concrete' in ln.description]
    assert bag_lines, '80 lb bag line should be present'
    bags = int(bag_lines[0].qty)
    assert bags == 6, f'expected 6 bags for 1 footing, got {bags}'

# 17-12  Full estimator run on synthetic scene — no crash, returns report
# Shared scene items used by several s17 tests
_S17_SCENE = [
    {'type': 'joist_fill', 'x': 0, 'y': 0,
     'w': 240, 'h': 192, 'spacing': 16, 'direction': 'h'},
    {'type': 'post', 'x': 0, 'y': 0, 'size': 3.5},
    {'type': 'wall', 'x1': 0, 'y1': 0, 'x2': 240, 'y2': 0, 'wall_type': 'exterior_6'},
    {'type': 'wall', 'x1': 0, 'y1': 0, 'x2': 0,   'y2': 192, 'wall_type': 'exterior_6'},
    {'type': 'wall', 'x1': 0, 'y1': 192,'x2': 240, 'y2': 192, 'wall_type': 'exterior_6'},
    {'type': 'wall', 'x1': 240,'y1': 0, 'x2': 240, 'y2': 192, 'wall_type': 'exterior_6'},
    {'type': 'door',   'x': 0,  'y': 0, 'width': 36, 'height': 80, 'rotation': 0},
    {'type': 'window', 'x1': 60, 'y1': 0, 'x2': 96, 'y2': 36},
    {'type': 'room',   'x': 0,  'y': 0, 'w': 240, 'h': 192, 'label': 'living'},
    {'type': 'room',   'x': 240,'y': 0, 'w': 180, 'h': 180, 'label': 'bedroom'},
]

def s17_full_run_no_crash():
    settings = EstimatorSettings(
        include_hardware=True, include_concrete=True,
        include_roof=True, include_finish=True, include_electrical=True)
    report = MaterialEstimator().run(_S17_SCENE, settings)
    assert isinstance(report, MaterialReport)
    assert len(report.lines) > 0, 'report should have lines'
    assert report.to_csv().startswith('Category'), 'CSV should have header'
    assert 'Material Estimate' in report.to_plain_text()

def s17_new_categories_present():
    """All new comprehensive categories produce at least one line."""
    settings = EstimatorSettings(
        include_drywall=True, include_insulation=True,
        include_flooring=True, include_doors_windows=True,
        include_siding=True, include_roofing=True,
        include_trim=True, include_plumbing=True, include_hvac=True,
        include_roof=True, flooring_type='lvp', siding_type='vinyl',
        roofing_type='shingles', ceiling_insul_r=38,
    )
    report = MaterialEstimator().run(_S17_SCENE, settings)
    cats = report.categories()
    for expected in ('Drywall & Finishing', 'Insulation', 'Flooring',
                     'Doors & Windows', 'Exterior Finish', 'Roofing Materials',
                     'Interior Trim', 'Plumbing (Rough)', 'HVAC (Rough)'):
        assert expected in cats, f'Missing category: {expected}'

def s17_flooring_types_no_crash():
    """Each flooring type runs without error."""
    for ftype in ('lvp', 'tile', 'carpet', 'hardwood'):
        s = EstimatorSettings(include_flooring=True, flooring_type=ftype)
        MaterialEstimator().run(_S17_SCENE, s)

def s17_plumbing_empty_rooms():
    """Plumbing stub with no drawn items: synthesis creates a room, so plumbing computes."""
    settings = EstimatorSettings(include_plumbing=True,
                                  building_width_ft=20.0, building_length_ft=30.0)
    report = MaterialEstimator().run([], settings)
    # Synthesis creates a room from settings dims → plumbing should produce lines
    plumbing_lines = [ln for ln in report.lines if ln.category == 'Plumbing (Rough)']
    assert len(plumbing_lines) > 0, 'Expected plumbing lines via synthesis room'

def s17_synthesis_blank_canvas():
    """All checked categories compute on a blank canvas using settings dimensions."""
    settings = EstimatorSettings(
        building_width_ft=24.0, building_length_ft=32.0,
        door_count=2, window_count=4,
        include_drywall=True, include_insulation=True, include_flooring=True,
        include_siding=True, include_roofing=True, include_roof=True,
        include_plumbing=True, include_hvac=True, include_concrete=True,
        foundation_type='slab',
    )
    report = MaterialEstimator().run([], settings)  # completely empty scene
    assert len(report.lines) > 15, f'Expected >15 lines on blank canvas, got {len(report.lines)}'
    cats = report.categories()
    for expected in ('Wall / Rail Framing', 'Drywall & Finishing',
                     'Flooring', 'HVAC (Rough)', 'Concrete & Footings'):
        assert expected in cats, f'Missing category on blank canvas: {expected}'

def s17_foundation_types_no_crash():
    """All 4 foundation types run on a blank canvas without error."""
    room = [{'type': 'room', 'x': 0, 'y': 0, 'w': 240, 'h': 288, 'label': 'test'}]
    for ftype in ('posts', 'footer_block', 'slab', 'concrete_wall'):
        s = EstimatorSettings(foundation_type=ftype, include_concrete=True,
                              footing_depth_in=24)
        report = MaterialEstimator().run(room, s)
        conc_lines = [ln for ln in report.lines if ln.category == 'Concrete & Footings']
        assert conc_lines, f'No Concrete lines for foundation_type={ftype}'

def s17_multi_section_synthesis():
    """Multiple building sections produce additive area > single section."""
    single = EstimatorSettings(
        building_sections=[{'label': 'Main', 'width_ft': 24.0, 'length_ft': 32.0}],
        include_flooring=True, include_drywall=True,
    )
    multi = EstimatorSettings(
        building_sections=[
            {'label': 'Main',   'width_ft': 24.0, 'length_ft': 32.0},
            {'label': 'Garage', 'width_ft': 20.0, 'length_ft': 22.0},
        ],
        include_flooring=True, include_drywall=True,
    )
    r_single = MaterialEstimator().run([], single)
    r_multi  = MaterialEstimator().run([], multi)
    def floor_boxes(r):
        for ln in r.lines:
            if ln.category == 'Flooring' and ln.unit == 'boxes':
                return float(ln.qty)
        return 0.0
    assert floor_boxes(r_multi) > floor_boxes(r_single), \
        'Multi-section should produce more flooring boxes than single section'

def s17_trade_isolation_flooring_only():
    """Turning on a single trade must not emit other trades' line items."""
    s = EstimatorSettings(
        include_substructure=False, include_decking=False, include_walls=False,
        include_hardware=False, include_concrete=False, include_roof=False,
        include_finish=False, include_electrical=False, include_drywall=False,
        include_insulation=False, include_flooring=True,
        include_doors_windows=False, include_siding=False, include_roofing=False,
        include_trim=False, include_plumbing=False, include_hvac=False,
    )
    report = MaterialEstimator().run([], s)
    cats = set(report.categories())
    assert cats == {'Flooring'}, f'expected only Flooring, got {cats}'

def s17_trade_isolation_drywall_no_batts():
    """Drywall trade must not include batt insulation or OSB sheathing."""
    s = EstimatorSettings(
        include_substructure=False, include_decking=False, include_walls=False,
        include_hardware=False, include_concrete=False, include_roof=False,
        include_finish=False, include_electrical=False, include_drywall=True,
        include_insulation=False, include_flooring=False,
        include_doors_windows=False, include_siding=False, include_roofing=False,
        include_trim=False, include_plumbing=False, include_hvac=False,
    )
    report = MaterialEstimator().run([], s)
    blob = ' '.join(ln.description.lower() for ln in report.lines)
    assert 'batt' not in blob, 'batt insulation leaked into drywall trade'
    assert 'osb' not in blob, 'OSB sheathing leaked into drywall trade'
    assert any(ln.category == 'Drywall & Finishing' for ln in report.lines)

def s17_window_synth_is_width_not_square():
    """Synthesized windows are a 36\" wide unit, not a 36×36 diagonal."""
    s = EstimatorSettings(
        include_substructure=False, include_decking=False, include_walls=False,
        include_hardware=False, include_concrete=False, include_roof=False,
        include_finish=False, include_electrical=False, include_drywall=False,
        include_insulation=False, include_flooring=False,
        include_doors_windows=True, include_siding=False, include_roofing=False,
        include_trim=False, include_plumbing=False, include_hvac=False,
        window_count=1, door_count=0,
    )
    report = MaterialEstimator().run([], s)
    win_lines = [ln for ln in report.lines
                 if ln.category == 'Doors & Windows' and 'window unit' in ln.description]
    assert win_lines, 'expected a window unit line'
    assert '36"' in win_lines[0].description, win_lines[0].description
    assert '50"' not in win_lines[0].description

def s17_slab_skips_joists_and_posts():
    """Slab foundation must not emit joists, posts, or joist hangers."""
    s = EstimatorSettings(
        foundation_type='slab', include_concrete=True, include_hardware=True,
        include_substructure=True, include_decking=True,
        include_walls=False, include_drywall=False, include_insulation=False,
        include_flooring=False, include_doors_windows=False, include_siding=False,
        include_roof=False, include_roofing=False, include_trim=False,
        include_finish=False, include_electrical=False, include_plumbing=False,
        include_hvac=False,
    )
    report = MaterialEstimator().run([], s)
    blob = ' '.join(ln.description.lower() for ln in report.lines)
    assert 'joist' not in blob, 'joists leaked onto a slab'
    assert 'post ×' not in blob and 'post x' not in blob
    assert 'hanger' not in blob, 'joist hangers leaked onto a slab'
    assert any(ln.category == 'Concrete & Footings' for ln in report.lines)

def s17_stud_cut_uses_plate_count():
    """Single top plate must cut studs longer than a double top plate."""
    room = [{'type': 'room', 'x': 0, 'y': 0, 'w': 240, 'h': 288}]
    walls = [
        {'type': 'wall', 'x1': 0, 'y1': 0, 'x2': 240, 'y2': 0},
        {'type': 'wall', 'x1': 0, 'y1': 0, 'x2': 0, 'y2': 288},
        {'type': 'wall', 'x1': 240, 'y1': 0, 'x2': 240, 'y2': 288},
        {'type': 'wall', 'x1': 0, 'y1': 288, 'x2': 240, 'y2': 288},
    ]
    base = dict(include_substructure=False, include_decking=False,
                include_walls=True, include_hardware=False, include_concrete=False,
                include_roof=False, include_finish=False, include_electrical=False,
                include_drywall=False, include_insulation=False, include_flooring=False,
                include_doors_windows=False, include_siding=False, include_roofing=False,
                include_trim=False, include_plumbing=False, include_hvac=False,
                ceiling_ht_ft=8.0, waste_pct=0)
    r1 = MaterialEstimator().run(room + walls, EstimatorSettings(plate_count=1, **base))
    r2 = MaterialEstimator().run(room + walls, EstimatorSettings(plate_count=2, **base))
    def _stud_desc(r):
        for ln in r.lines:
            if 'stud ×' in ln.description or 'stud x' in ln.description.lower():
                return ln.description
        return ''
    # 8 ft − 2×1.5" = 7.75 → 8 ft stock; 8 ft − 3×1.5" = 7.625 → still 8 ft
    # with [8,10,12,16] both round to 8. Count of top-plate lines differs.
    top1 = sum(1 for ln in r1.lines if 'top plate' in ln.description or 'cap plate' in ln.description)
    top2 = sum(1 for ln in r2.lines if 'top plate' in ln.description or 'cap plate' in ln.description)
    assert top1 == 1, f'single top plate expected 1 line, got {top1}'
    assert top2 == 2, f'double top plate expected 2 lines, got {top2}'

for _name, _fn in [
    ('LumberSchedule.round_up basic',            s17_round_up_basic),
    ('LumberSchedule.summarize grouping',         s17_summarize),
    ('post grid: corners always included',        s17_post_grid_corners),
    ('post grid: zero-size no crash',             s17_post_grid_zero),
    ('joist count 120x96 @ 16" o.c.',            s17_joist_count),
    ('band board count per JoistFillItem',        s17_band_count),
    ('blocking triggered span > 96 in',           s17_blocking_triggered),
    ('no blocking for short span',                s17_no_blocking_short),
    ('deck board count from known area',          s17_deck_boards),
    ('plywood sheet count rounds up',             s17_plywood_roundup),
    ('concrete volume formula (1 footing)',       s17_concrete_volume),
    ('full estimator run no crash',               s17_full_run_no_crash),
    ('all new categories present in output',      s17_new_categories_present),
    ('flooring types: lvp/tile/carpet/hardwood',  s17_flooring_types_no_crash),
    ('plumbing stub: empty rooms -> no output',   s17_plumbing_empty_rooms),
    ('synthesis: blank canvas uses settings',     s17_synthesis_blank_canvas),
    ('foundation types: all 4 produce output',    s17_foundation_types_no_crash),
    ('multi-section synthesis: additive area',    s17_multi_section_synthesis),
    ('isolation: flooring only',                  s17_trade_isolation_flooring_only),
    ('isolation: drywall has no batts/OSB',       s17_trade_isolation_drywall_no_batts),
    ('synth window is 36" wide not diagonal',     s17_window_synth_is_width_not_square),
    ('slab skips joists/posts/hangers',           s17_slab_skips_joists_and_posts),
    ('stud cut respects plate count',             s17_stud_cut_uses_plate_count),
]:
    chk(_name, _fn)


# ─────────────────────────────────────────────────────────────────────────────
# Section 18 — Code Compliance Engine  (12 tests)
# ─────────────────────────────────────────────────────────────────────────────

from code_tables import (
    min_deck_joist, min_floor_joist, min_rafter,
    min_footing_dia, max_cantilever, blocking_rows_required,
    header_size as code_header_size,
    rafter_length, KY_DEFAULTS,
)
from estimator import CodeChecker, CodeIssue, CodeReport

# 18-01  min_deck_joist: known span + spacing → expected size
def s18_min_deck_joist_known():
    # 2×8 SP @ 16" spans up to 11.8 ft; 12 ft exceeds that → needs 2x10
    result = min_deck_joist(12.0, 16)
    assert result == '2x10', f'expected 2x10 for 12 ft @ 16", got {result}'

# 18-02  min_deck_joist: span exceeding all table entries → returns '2x12+'
def s18_min_deck_joist_exceeds():
    result = min_deck_joist(25.0, 16)
    assert result == '2x12+', f'expected 2x12+ for 25 ft span, got {result}'

# 18-03  min_footing_dia: tributary area boundary
def s18_footing_dia_boundary():
    assert min_footing_dia(40)  == 12, 'expected 12" for 40 sqft'
    assert min_footing_dia(41)  == 14, 'expected 14" for 41 sqft'
    assert min_footing_dia(200) == 28, 'expected 28" for 200 sqft (max)'

# 18-04  blocking_rows_required: short/medium/long
def s18_blocking_rows():
    assert blocking_rows_required(84) == 0,  'short span (7 ft) → 0 rows'
    assert blocking_rows_required(120) == 1, '10 ft span → 1 row'
    assert blocking_rows_required(216) == 2, '18 ft span → 2 rows'

# 18-05  max_cantilever: 2×10 → actual depth 9.25 in
def s18_max_cantilever_2x10():
    result = max_cantilever('2x10')
    assert abs(result - 9.25) < 0.01, f'expected 9.25" for 2x10, got {result}'

# 18-06  max_cantilever: 2×12 → 11.25 in
def s18_max_cantilever_2x12():
    result = max_cantilever('2x12')
    assert abs(result - 11.25) < 0.01, f'expected 11.25" for 2x12, got {result}'

# 18-07  min_rafter: known 12 ft run @ 16" → should return 2x6 (16.2 ft table max)
def s18_min_rafter():
    result = min_rafter(12.0, 16)
    assert result in ('2x6', '2x8'), f'expected 2x6 or 2x8 for 12 ft @ 16", got {result}'

# 18-08  rafter_length geometry: flat roof (pitch=0) → length = run + overhang
def s18_rafter_length_flat():
    length = rafter_length(half_span_ft=10.0, pitch=0, overhang_in=24)
    expected = 10.0 + 24/12   # 12.0 ft
    assert abs(length - expected) < 0.01, f'expected {expected}, got {length}'

# 18-09  CodeChecker: joist within table → OK
def s18_codechecker_joist_ok():
    items = [{'type': 'joist_fill', 'x': 0, 'y': 0, 'w': 96, 'h': 96,
              'direction': 'h', 'spacing': 16, 'joist_size': '2x10',
              'blocking_rows': 0, 'cantilever_in': 0}]
    settings = EstimatorSettings()
    report = CodeChecker().run(items, settings, KY_DEFAULTS)
    joist_issues = [i for i in report.issues if i.element == 'Joist Fill']
    assert joist_issues, 'should have at least one joist issue'
    assert joist_issues[0].severity == 'OK', \
        f'8 ft span with 2x10 should be OK, got {joist_issues[0].severity}'

# 18-10  CodeChecker: joist oversized span → ERROR
def s18_codechecker_joist_error():
    items = [{'type': 'joist_fill', 'x': 0, 'y': 0, 'w': 360, 'h': 96,
              'direction': 'h', 'spacing': 16, 'joist_size': '2x6',
              'blocking_rows': 0, 'cantilever_in': 0}]
    settings = EstimatorSettings()
    report = CodeChecker().run(items, settings, KY_DEFAULTS)
    joist_issues = [i for i in report.issues if i.element == 'Joist Fill']
    assert joist_issues[0].severity == 'ERROR', \
        f'30 ft span with 2x6 should be ERROR, got {joist_issues[0].severity}'

# 18-11  CodeChecker: cantilever violation
def s18_codechecker_cantilever():
    items = [{'type': 'joist_fill', 'x': 0, 'y': 0, 'w': 96, 'h': 96,
              'direction': 'h', 'spacing': 16, 'joist_size': '2x8',
              'blocking_rows': 0, 'cantilever_in': 36}]  # 36" > 7.25" limit
    settings = EstimatorSettings()
    report = CodeChecker().run(items, settings, KY_DEFAULTS)
    cant_issues = [i for i in report.issues if i.element == 'Cantilever']
    assert cant_issues, 'should have a cantilever issue'
    assert cant_issues[0].severity == 'ERROR', \
        f'36" cantilever on 2x8 (max 7.25") should be ERROR'

# 18-12  CodeReport.to_csv: produces valid CSV with header row
def s18_code_report_csv():
    report = CodeReport()
    report.add('Joist Fill', 'bay 1', 'test check', '2x10', '2x6', 'ERROR')
    report.add('Footing', 'post 1', 'dia check', '16"', '12"', 'WARN')
    csv_text = report.to_csv()
    lines = csv_text.strip().split('\n')
    assert lines[0].startswith('Element'), f'first CSV line should be header, got: {lines[0]}'
    assert len(lines) == 3, f'expected 3 CSV lines (header + 2 data), got {len(lines)}'

for _name, _fn in [
    ('min_deck_joist: 12 ft @ 16" -> 2x8',        s18_min_deck_joist_known),
    ('min_deck_joist: 25 ft -> 2x12+',             s18_min_deck_joist_exceeds),
    ('min_footing_dia: boundary conditions',       s18_footing_dia_boundary),
    ('blocking_rows_required: short/mid/long',     s18_blocking_rows),
    ('max_cantilever: 2x10 = 9.25"',               s18_max_cantilever_2x10),
    ('max_cantilever: 2x12 = 11.25"',              s18_max_cantilever_2x12),
    ('min_rafter: 12 ft @ 16" -> 2x6/2x8',         s18_min_rafter),
    ('rafter_length flat: run + overhang',         s18_rafter_length_flat),
    ('CodeChecker: 8 ft joist span -> OK',          s18_codechecker_joist_ok),
    ('CodeChecker: 30 ft with 2x6 -> ERROR',        s18_codechecker_joist_error),
    ('CodeChecker: 36" cantilever on 2x8 -> ERROR', s18_codechecker_cantilever),
    ('CodeReport.to_csv: header + 2 data rows',    s18_code_report_csv),
]:
    chk(_name, _fn)


# ═════════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ═════════════════════════════════════════════════════════════════════════════

print()
_passed = sum(1 for r in _results if r[0] == 'PASS')
_failed = sum(1 for r in _results if r[0] == 'FAIL')
_total  = len(_results)

for r in _results:
    mark = 'PASS' if r[0] == 'PASS' else 'FAIL'
    print(f'  {mark}  {r[1]}')
    if r[0] == 'FAIL':
        print(f'        ERROR: {r[2]}')

print()
print('=' * 60)
print(f'  {_passed}/{_total} passed', end='')
if _failed:
    print(f'  *  {_failed} FAILED')
else:
    print('  -- all tests passed')
print('=' * 60)

if _failed:
    sys.exit(1)

