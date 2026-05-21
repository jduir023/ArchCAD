"""
ArchCAD — Comprehensive Smoke Test  (116 tests, 16 sections)
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
  9.  Paste / duplicate                ( 3 tests)
 10.  MainWindow selection + panels    ( 9 tests)
 11.  Property commits XY/WH/text/font ( 5 tests)
 12.  Lock toggle                      ( 4 tests)
 13.  Alignment operations             ( 7 tests)
 14.  Z-order, select-all, move-layer  ( 5 tests)
 15.  Scale / paper / page / post-grid ( 5 tests)
 16.  Item flags + uniqueness          ( 3 tests)
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

for _name, _fn in [
    ('paste: offset + fresh ID',       s9_paste_offset_and_fresh_id),
    ('paste: multiple item types',     s9_paste_multiple),
    ('paste: undo is one macro step',  s9_paste_undo_macro),
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

