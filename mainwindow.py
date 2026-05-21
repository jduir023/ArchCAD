"""
ArchCAD — Main window  (Phase 4: Ribbon + Rulers + Scale + Page Boundary)
"""

from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar, QDockWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QMessageBox, QToolButton,
    QButtonGroup, QComboBox, QDoubleSpinBox, QDialog, QFormLayout,
    QDialogButtonBox, QTreeWidget, QTreeWidgetItem, QInputDialog,
    QStackedWidget, QFrame, QGridLayout, QPushButton, QGraphicsItem,
    QScrollArea, QColorDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMenu, QFileDialog, QLineEdit,
)
from PyQt6.QtCore import Qt, QSize, QPointF, QMarginsF, QSizeF, QRectF, QLineF
from PyQt6.QtGui  import QAction, QFont, QKeySequence, QShortcut, QColor, QCursor, QPdfWriter, QPageSize, QPageLayout, QPainter

from canvas import (
    CADCanvas, _MoveCmd, _PropCmd,
    TOOL_SELECT, TOOL_PAN, TOOL_ROOM, TOOL_WALL,
    TOOL_DOOR, TOOL_WINDOW, TOOL_DIMENSION,
    TOOL_POST, TOOL_JOIST, TOOL_SHAPE, TOOL_LINE, TOOL_TEXT,
)
from items  import WALL_TYPES, GroupItem
from rulers import HRuler, VRuler, RULER_W

# ── Scale & paper options ─────────────────────────────────────────────────────
# ratio = scene_inches_per_paper_physical_inch
# (At 1/4"=1ft: 1 drawing-inch represents 4 real feet = 48 real inches → ratio 48)

_SCALE_OPTIONS = [
    ("1\"  = 1'   (1:12)",    12),
    ("1/2\" = 1'   (1:24)",   24),
    ("3/8\" = 1'   (1:32)",   32),
    ("1/4\" = 1'   (1:48)",   48),   # default
    ("3/16\" = 1'  (1:64)",   64),
    ("1/8\" = 1'   (1:96)",   96),
    ("1/16\" = 1'  (1:192)", 192),
]

_PAPER_SIZES = [
    ("Letter  8.5\" × 11\"",   8.5,  11.0),
    ("Legal   8.5\" × 14\"",   8.5,  14.0),
    ("Tabloid 11\" × 17\"",   11.0,  17.0),
    ("Arch B  12\" × 18\"",   12.0,  18.0),
    ("Arch C  18\" × 24\"",   18.0,  24.0),
    ("Arch D  24\" × 36\"",   24.0,  36.0),
    ("Arch E  36\" × 48\"",   36.0,  48.0),
]

# ── Tool registry ─────────────────────────────────────────────────────────────

_TOOLS = [
    (TOOL_SELECT,    'Select',    'S'),
    (TOOL_ROOM,      'Room',      'R'),
    (TOOL_WALL,      'Wall',      'W'),
    (TOOL_DOOR,      'Door',      'D'),
    (TOOL_WINDOW,    'Window',    'N'),
    (TOOL_DIMENSION, 'Dimension', 'E'),
    (TOOL_POST,      'Post',      'P'),
    (TOOL_JOIST,     'Joists',    'J'),
    (TOOL_SHAPE,     'Shape',     'F'),
    (TOOL_LINE,      'Line',      'L'),
    (TOOL_TEXT,      'Text',      'T'),
]

_HINT = ("S/R/W/D/N/E/P/J/F/L/T = tools  |  Middle-drag = pan  |  "
         "Scroll = zoom  |  Del = delete  |  Esc = cancel")

# ── Presets ───────────────────────────────────────────────────────────────────

_PRESETS = {
    'Doors': [
        ("2'-0\"  (24\")", TOOL_DOOR,  {'door_width': 24}),
        ("2'-6\"  (30\")", TOOL_DOOR,  {'door_width': 30}),
        ("2'-8\"  (32\")", TOOL_DOOR,  {'door_width': 32}),
        ("3'-0\"  (36\")", TOOL_DOOR,  {'door_width': 36}),
        ("3'-6\"  (42\")", TOOL_DOOR,  {'door_width': 42}),
        ("6'-0\"  Double", TOOL_DOOR,  {'door_width': 72}),
    ],
    'Windows': [
        ("24\"  (2'-0\")", TOOL_WINDOW, {}),
        ("30\"  (2'-6\")", TOOL_WINDOW, {}),
        ("36\"  (3'-0\")", TOOL_WINDOW, {}),
        ("48\"  (4'-0\")", TOOL_WINDOW, {}),
        ("60\"  (5'-0\")", TOOL_WINDOW, {}),
        ("72\"  (6'-0\")", TOOL_WINDOW, {}),
    ],
    'Posts': [
        ('4×4  (3.5")',  TOOL_POST, {'post_size': 3.5}),
        ('6×6  (5.5")',  TOOL_POST, {'post_size': 5.5}),
        ('8×8  (7.5")',  TOOL_POST, {'post_size': 7.5}),
    ],
    'Joists': [
        ('12"  o.c.  H',   TOOL_JOIST, {'spacing': 12,   'direction': 'h'}),
        ('16"  o.c.  H',   TOOL_JOIST, {'spacing': 16,   'direction': 'h'}),
        ('19.2"  o.c.  H', TOOL_JOIST, {'spacing': 19.2, 'direction': 'h'}),
        ('24"  o.c.  H',   TOOL_JOIST, {'spacing': 24,   'direction': 'h'}),
        ('16"  o.c.  V',   TOOL_JOIST, {'spacing': 16,   'direction': 'v'}),
        ('24"  o.c.  V',   TOOL_JOIST, {'spacing': 24,   'direction': 'v'}),
    ],
}

_SNAP_IN     = [3, 6, 12, 24]
_DOOR_W_IN   = [24, 30, 32, 36, 42, 72]
_JOIST_SP_IN = [12, 16, 19.2, 24]
_POST_SIZES  = [3.5, 5.5, 7.5]

# ── Ribbon styling ────────────────────────────────────────────────────────────

_RIBBON_CSS = """
QWidget#ribbon_root {
    background: #252f3e;
    border-bottom: 2px solid #111820;
}
QWidget#tab_row {
    background: #1a2333;
    border-bottom: 1px solid #111820;
}
QPushButton#tab_btn {
    background: transparent;
    border: none;
    border-right: 1px solid #2a3548;
    padding: 3px 18px;
    font-size: 9pt;
    font-family: 'Segoe UI';
    color: #8a9ab0;
    min-height: 22px;
}
QPushButton#tab_btn:checked {
    background: #252f3e;
    border-top: 3px solid #5a9adc;
    border-bottom: none;
    font-weight: bold;
    color: #7eb8f0;
}
QPushButton#tab_btn:hover:!checked { background: #1e2d40; }
QToolButton#rbtn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 2px 8px;
    font-size: 8.5pt;
    font-family: 'Segoe UI';
    color: #c0d0e0;
    min-width: 38px;
}
QToolButton#rbtn:hover        { background: #2d4a6e; border: 1px solid #4a6a9e; }
QToolButton#rbtn:pressed      { background: #1e3558; border: 1px solid #3a6090; }
QToolButton#rbtn:checked      { background: #1e3a5a; border: 1px solid #5a90c0; font-weight: bold; }
QLabel#grp_lbl {
    color: #6a7a8a; font-size: 7pt; font-family: 'Segoe UI';
}
"""

# ── Ribbon helpers ────────────────────────────────────────────────────────────

def _rbtn(text: str, tip: str = '', checkable: bool = False) -> QToolButton:
    b = QToolButton()
    b.setText(text)
    b.setObjectName('rbtn')
    b.setToolTip(tip)
    b.setCheckable(checkable)
    b.setMinimumWidth(42)
    return b


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet('color: #b0bccc; margin: 4px 2px;')
    f.setFixedWidth(5)
    return f


def _grp(label: str, *widgets) -> QWidget:
    """Named group: widgets in a row with a label below."""
    w   = QWidget()
    lay = QVBoxLayout(w)
    lay.setSpacing(2)
    lay.setContentsMargins(4, 2, 4, 1)
    row = QHBoxLayout()
    row.setSpacing(2)
    for ww in widgets:
        row.addWidget(ww)
    lay.addLayout(row)
    lbl = QLabel(label)
    lbl.setObjectName('grp_lbl')
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(lbl)
    return w


# ─────────────────────────────────────────────────────────────────────────────
# Collapsible section widget (left presets panel)
# ─────────────────────────────────────────────────────────────────────────────

class _CollapsibleSection(QWidget):
    """SmartDraw-style collapsible section for the left presets panel."""

    _HDR_CSS = (
        "QPushButton {"
        "  background: #2c4a6e; border: none;"
        "  border-bottom: 1px solid #1a3050;"
        "  padding: 3px 6px; text-align: left;"
        "  font-size: 9pt; font-weight: bold; color: #ffffff;"
        "}"
        "QPushButton:hover { background: #3a5a80; }"
    )
    _ITEM_CSS = (
        "QPushButton {"
        "  background: transparent; border: none;"
        "  border-bottom: 1px solid #2a3850;"
        "  padding: 3px 12px; text-align: left;"
        "  font-size: 8.5pt; color: #dce8f5;"
        "}"
        "QPushButton:hover   { background: #2d4a6e; }"
        "QPushButton:pressed { background: #1e3558; }"
    )

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title    = title
        self._expanded = True
        vl = QVBoxLayout(self)
        vl.setSpacing(0)
        vl.setContentsMargins(0, 0, 0, 0)
        self._hdr = QPushButton(f'▼  {title}')
        self._hdr.setStyleSheet(self._HDR_CSS)
        self._hdr.setFixedHeight(24)
        self._hdr.clicked.connect(self._toggle)
        self._body = QWidget()
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setSpacing(0)
        self._body_lay.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(self._hdr)
        vl.addWidget(self._body)

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        arrow = '▼' if self._expanded else '▶'
        self._hdr.setText(f'{arrow}  {self._title}')

    def add_item(self, text: str, callback):
        btn = QPushButton(text)
        btn.setStyleSheet(self._ITEM_CSS)
        btn.setFixedHeight(24)
        btn.clicked.connect(callback)
        self._body_lay.addWidget(btn)

    def add_label(self, text: str):
        """Insert a non-clickable category label inside the section body."""
        lbl = QLabel(text)
        lbl.setStyleSheet(
            'QLabel { color: #7a9abf; font-size: 7.5pt; font-style: italic;'
            ' padding: 5px 10px 2px 10px; background: transparent; }')
        self._body_lay.addWidget(lbl)


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle('ArchCAD  —  Untitled')
        self.setMinimumSize(1100, 700)
        self.resize(1440, 880)

        self._canvas = CADCanvas(self)

        self._build_menu()
        self._build_ribbon()       # sets up _tab_stack, all combos/buttons
        self._build_canvas_area()  # grid + rulers → setCentralWidget
        self._build_presets_dock()
        self._build_properties_dock()
        self._build_layers_dock()
        self._build_status_bar()

        # Wire signals
        self._canvas.status_message.connect(self._status.showMessage)
        self._canvas.selection_changed.connect(self._on_selection_changed)
        self._canvas.scale_changed.connect(self._on_canvas_scale_changed)
        self._canvas.layers_changed.connect(self._refresh_layers_ui)

        # Apply initial page settings (status bar must exist first)
        self._apply_page_defaults()

        # Clipboard & context menu
        self._clipboard: list = []
        self._props_updating: bool = False
        self._canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._canvas.customContextMenuRequested.connect(self._show_canvas_context_menu)

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        fm = mb.addMenu('&File')
        for lbl, key, slot in [
            ('&New',       QKeySequence.StandardKey.New,    self._act_new),
            ('&Open…',     QKeySequence.StandardKey.Open,   self._act_open),
            ('&Save',      QKeySequence.StandardKey.Save,   self._act_save),
            ('Save &As…',  QKeySequence.StandardKey.SaveAs, self._act_save_as),
        ]:
            a = QAction(lbl, self); a.setShortcut(key)
            a.triggered.connect(slot); fm.addAction(a)
        fm.addSeparator()
        a = QAction('Export &PNG…', self)
        a.triggered.connect(self._canvas.export_png); fm.addAction(a)
        a = QAction('Export &PDF…', self)
        a.setShortcut('Ctrl+Shift+P')
        a.triggered.connect(self._act_export_pdf); fm.addAction(a)
        fm.addSeparator()
        a = QAction('E&xit', self)
        a.setShortcut('Alt+F4'); a.triggered.connect(self.close); fm.addAction(a)

        em = mb.addMenu('&Edit')
        ua = QAction('&Undo', self)
        ua.setShortcut(QKeySequence.StandardKey.Undo)
        ua.triggered.connect(self._canvas._undo_stack.undo)
        em.addAction(ua)
        ra = QAction('&Redo', self)
        ra.setShortcut(QKeySequence.StandardKey.Redo)
        ra.triggered.connect(self._canvas._undo_stack.redo)
        em.addAction(ra)
        em.addSeparator()
        for lbl, key, slot in [
            ('Cu&t',       'Ctrl+X', self._cut_selected),
            ('&Copy',      'Ctrl+C', self._copy_selected),
            ('&Paste',     'Ctrl+V', self._paste_from_clipboard),
            ('D&uplicate', 'Ctrl+D', self._duplicate_selected),
        ]:
            a = QAction(lbl, self); a.setShortcut(key)
            a.triggered.connect(slot); em.addAction(a)
        em.addSeparator()
        for lbl, key, slot in [
            ('&Group',   'Ctrl+G',       self._group_selected),
            ('&Ungroup', 'Ctrl+Shift+G', self._ungroup_selected),
        ]:
            a = QAction(lbl, self); a.setShortcut(key)
            a.triggered.connect(slot); em.addAction(a)

        vm = mb.addMenu('&View')
        for lbl, key, slot in [
            ('Zoom &In',  QKeySequence.StandardKey.ZoomIn,
             lambda: self._canvas.scale(1.25, 1.25)),
            ('Zoom &Out', QKeySequence.StandardKey.ZoomOut,
             lambda: self._canvas.scale(1 / 1.25, 1 / 1.25)),
            ('Fit &All',  'Ctrl+0', self._canvas.zoom_fit),
        ]:
            a = QAction(lbl, self); a.setShortcut(key)
            a.triggered.connect(slot); vm.addAction(a)

        tm = mb.addMenu('&Tools')
        a = QAction('Auto-fill &Posts…', self)
        a.triggered.connect(self._act_auto_posts); tm.addAction(a)

    # ── Ribbon ────────────────────────────────────────────────────────────────

    def _build_ribbon(self):
        tb = QToolBar('Ribbon', self)
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)

        root = QWidget()
        root.setObjectName('ribbon_root')
        root.setStyleSheet(_RIBBON_CSS)

        vlay = QVBoxLayout(root)
        vlay.setSpacing(0)
        vlay.setContentsMargins(0, 0, 0, 0)

        # ── Tab bar ───────────────────────────────────────────────────────────
        tab_row = QWidget()
        tab_row.setObjectName('tab_row')
        tab_row.setFixedHeight(26)
        tlay = QHBoxLayout(tab_row)
        tlay.setSpacing(0)
        tlay.setContentsMargins(4, 0, 0, 0)

        self._tab_grp   = QButtonGroup(self)
        self._tab_stack = QStackedWidget()

        for idx, name in enumerate(['Home', 'Design', 'Page']):
            btn = QPushButton(name)
            btn.setObjectName('tab_btn')
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            btn.clicked.connect(lambda _, i=idx: self._tab_stack.setCurrentIndex(i))
            self._tab_grp.addButton(btn, idx)
            tlay.addWidget(btn)
        self._tab_grp.button(0).setChecked(True)
        tlay.addStretch()
        vlay.addWidget(tab_row)

        # ── Ribbon content ────────────────────────────────────────────────────
        self._tab_stack.addWidget(self._build_home_tab())
        self._tab_stack.addWidget(self._build_design_tab())
        self._tab_stack.addWidget(self._build_page_tab())
        vlay.addWidget(self._tab_stack)

        TAB_H    = 26
        CONTENT_H = 56
        root.setFixedHeight(TAB_H + CONTENT_H)
        tb.addWidget(root)
        tb.setFixedHeight(TAB_H + CONTENT_H + 2)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

    # ── Home tab ──────────────────────────────────────────────────────────────

    def _build_home_tab(self) -> QWidget:
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.setSpacing(0)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # File group
        bn = _rbtn('New',        'New project  (Ctrl+N)')
        bo = _rbtn('Open…',      'Open project  (Ctrl+O)')
        bs = _rbtn('Save',       'Save  (Ctrl+S)')
        ba = _rbtn('Save As…',   'Save As…')
        be  = _rbtn('Export PNG…','Export drawing to PNG')
        bpdf = _rbtn('Export PDF…','Export drawing to PDF  (Ctrl+Shift+P)')
        bn.clicked.connect(self._act_new)
        bo.clicked.connect(self._act_open)
        bs.clicked.connect(self._act_save)
        ba.clicked.connect(self._act_save_as)
        be.clicked.connect(self._canvas.export_png)
        bpdf.clicked.connect(self._act_export_pdf)
        lay.addWidget(_grp('File', bn, bo, bs, ba, be, bpdf))
        lay.addWidget(_sep())

        # View group
        bf  = _rbtn('Fit All',  'Fit all items  (Ctrl+0)')
        bzi = _rbtn('Zoom +',   'Zoom in')
        bzo = _rbtn('Zoom −',   'Zoom out')
        bf.clicked.connect(self._canvas.zoom_fit)
        bzi.clicked.connect(lambda: self._canvas.scale(1.25, 1.25))
        bzo.clicked.connect(lambda: self._canvas.scale(1 / 1.25, 1 / 1.25))
        bgrid = _rbtn('Grid', 'Toggle grid', checkable=True)
        bgrid.setChecked(True)
        bgrid.toggled.connect(self._canvas.toggle_grid)
        bun = _rbtn('Undo', 'Undo  (Ctrl+Z)')
        brd = _rbtn('Redo', 'Redo  (Ctrl+Y)')
        bun.clicked.connect(self._canvas._undo_stack.undo)
        brd.clicked.connect(self._canvas._undo_stack.redo)
        lay.addWidget(_grp('View', bf, bzi, bzo, bgrid))
        lay.addWidget(_grp('History', bun, brd))
        lay.addWidget(_sep())

        # Tools group
        self._tool_btns: dict[str, QToolButton] = {}
        tbgrp = QButtonGroup(self)
        tbgrp.setExclusive(True)
        tool_widgets = []
        for tool, label, key in _TOOLS:
            b = _rbtn(f'{label} [{key}]', f'{label}  (key: {key})', checkable=True)
            b.clicked.connect(lambda _, t=tool: self._set_tool(t))
            tbgrp.addButton(b)
            self._tool_btns[tool] = b
            tool_widgets.append(b)
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(lambda t=tool: self._set_tool(t))
        self._tool_btns[TOOL_SELECT].setChecked(True)
        lay.addWidget(_grp('Tools', *tool_widgets))
        lay.addStretch()
        return w

    # ── Design tab ────────────────────────────────────────────────────────────

    def _build_design_tab(self) -> QWidget:
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.setSpacing(0)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Snap
        self._snap_combo = QComboBox()
        self._snap_combo.addItems(["3\"", "6\"", "12\"  (1')", "24\"  (2')"])
        self._snap_combo.setCurrentIndex(2)
        self._snap_combo.setFixedWidth(112)
        self._snap_combo.currentIndexChanged.connect(self._on_snap_changed)
        lay.addWidget(_grp('Snap Grid', self._snap_combo))
        lay.addWidget(_sep())

        # Wall type
        self._cmb_wall = QComboBox()
        for _k, _v in WALL_TYPES.items():
            self._cmb_wall.addItem(_v[0])
        self._cmb_wall.setCurrentIndex(0)
        self._cmb_wall.setFixedWidth(155)
        self._cmb_wall.currentIndexChanged.connect(self._on_wall_type_changed)
        lay.addWidget(_grp('Wall Type', self._cmb_wall))
        lay.addWidget(_sep())

        # Door width
        self._cmb_door = QComboBox()
        self._cmb_door.addItems(["2'-0\"  (24\")", "2'-6\"  (30\")", "2'-8\"  (32\")",
                                  "3'-0\"  (36\")", "3'-6\"  (42\")", "6'-0\"  Dbl"])
        self._cmb_door.setCurrentIndex(3)
        self._cmb_door.setFixedWidth(130)
        self._cmb_door.currentIndexChanged.connect(self._on_door_width_changed)
        lay.addWidget(_grp('Door Width', self._cmb_door))
        lay.addWidget(_sep())

        # Joist spacing + direction
        self._cmb_joist_sp = QComboBox()
        self._cmb_joist_sp.addItems(['12"  o.c.', '16"  o.c.', '19.2"  o.c.', '24"  o.c.'])
        self._cmb_joist_sp.setCurrentIndex(1)
        self._cmb_joist_sp.setFixedWidth(115)
        self._cmb_joist_sp.currentIndexChanged.connect(self._on_joist_sp_changed)

        self._cmb_joist_dir = QComboBox()
        self._cmb_joist_dir.addItems(['Horizontal', 'Vertical'])
        self._cmb_joist_dir.setFixedWidth(100)
        self._cmb_joist_dir.currentIndexChanged.connect(self._on_joist_dir_changed)
        lay.addWidget(_grp('Joist Spacing', self._cmb_joist_sp))
        lay.addWidget(_grp('Direction', self._cmb_joist_dir))
        lay.addWidget(_sep())

        # Post size
        self._cmb_post = QComboBox()
        self._cmb_post.addItems(['4×4  (3.5")', '6×6  (5.5")', '8×8  (7.5")', 'Custom…'])
        self._cmb_post.setFixedWidth(120)
        self._cmb_post.currentIndexChanged.connect(self._on_post_size_changed)
        lay.addWidget(_grp('Post Size', self._cmb_post))
        lay.addWidget(_sep())

        # Shape type
        self._cmb_shape_type = QComboBox()
        self._cmb_shape_type.addItems(['Rectangle', 'Ellipse'])
        self._cmb_shape_type.setFixedWidth(105)
        self._cmb_shape_type.currentIndexChanged.connect(self._on_shape_type_changed)
        lay.addWidget(_grp('Shape Type', self._cmb_shape_type))

        # Line style
        self._cmb_line_style = QComboBox()
        self._cmb_line_style.addItems(['Solid', 'Dashed', 'Dotted'])
        self._cmb_line_style.setFixedWidth(90)
        self._cmb_line_style.currentIndexChanged.connect(self._on_line_style_changed)
        lay.addWidget(_grp('Line Style', self._cmb_line_style))

        # Text font size
        self._cmb_text_size = QComboBox()
        self._cmb_text_size.addItems(['6pt', '8pt', '10pt', '12pt', '14pt', '18pt', '24pt', '36pt'])
        self._cmb_text_size.setCurrentIndex(3)   # 12pt default
        self._cmb_text_size.setFixedWidth(80)
        self._cmb_text_size.currentIndexChanged.connect(self._on_text_size_changed)
        lay.addWidget(_grp('Text Size', self._cmb_text_size))
        lay.addWidget(_sep())

        # Selection actions
        bsa  = _rbtn('Select All',  'Select all items  (Ctrl+A)')
        bsl  = _rbtn('All Lines',   'Select all lines')
        bdel = _rbtn('Delete Sel',  'Delete selected  (Del)')
        bsa.clicked.connect(self._select_all)
        bsl.clicked.connect(self._select_all_lines)
        bdel.clicked.connect(self._delete_selected)
        bgr  = _rbtn('Group',   'Group selected items  (Ctrl+G)')
        bung = _rbtn('Ungroup', 'Ungroup selected group (Ctrl+Shift+G)')
        bgr.clicked.connect(self._group_selected)
        bung.clicked.connect(self._ungroup_selected)
        lay.addWidget(_grp('Selection', bsa, bsl, bdel, bgr, bung))
        lay.addWidget(_sep())

        # Align group — 2×4 grid of compact buttons
        _AM = [
            ('← L',  'Align Left edges',           'left'),
            ('↔ H',  'Center on vertical axis',     'center_h'),
            ('R →',  'Align Right edges',           'right'),
            ('⟺ H',  'Distribute Horizontally',     'dist_h'),
            ('↑ T',  'Align Top edges',             'top'),
            ('↕ V',  'Center on horizontal axis',   'center_v'),
            ('B ↓',  'Align Bottom edges',          'bottom'),
            ('⟳ V',  'Distribute Vertically',       'dist_v'),
        ]
        agw = QWidget()
        agl = QVBoxLayout(agw); agl.setSpacing(2); agl.setContentsMargins(4, 2, 4, 1)
        ar1 = QHBoxLayout(); ar1.setSpacing(2)
        ar2 = QHBoxLayout(); ar2.setSpacing(2)
        for i, (lbl, tip, mode) in enumerate(_AM):
            b = _rbtn(lbl, tip); b.setMinimumWidth(34)
            b.clicked.connect(lambda _, m=mode: self._align_items(m))
            (ar1 if i < 4 else ar2).addWidget(b)
        agl.addLayout(ar1); agl.addLayout(ar2)
        albl = QLabel('Align'); albl.setObjectName('grp_lbl')
        albl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        agl.addWidget(albl)
        lay.addWidget(agw)

        # Active Layer
        self._layer_combo = QComboBox()
        self._layer_combo.setFixedWidth(130)
        self._layer_combo.addItem('Layer 0')
        self._layer_combo.currentIndexChanged.connect(
            lambda idx: self._canvas.set_active_layer(idx))
        lay.addWidget(_grp('Active Layer', self._layer_combo))
        lay.addStretch()
        return w

    # ── Page tab ──────────────────────────────────────────────────────────────

    def _build_page_tab(self) -> QWidget:
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.setSpacing(0)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Paper size
        self._cmb_paper = QComboBox()
        for name, *_ in _PAPER_SIZES:
            self._cmb_paper.addItem(name)
        self._cmb_paper.setFixedWidth(172)
        # Signal connected below after orient buttons exist

        # Orientation
        self._btn_port = _rbtn('Portrait',  'Portrait',  checkable=True)
        self._btn_land = _rbtn('Landscape', 'Landscape', checkable=True)
        self._btn_port.setChecked(True)
        og = QButtonGroup(self)
        og.setExclusive(True)
        og.addButton(self._btn_port)
        og.addButton(self._btn_land)
        self._btn_port.toggled.connect(self._on_orient_changed)

        # Connect paper combo now that orient buttons exist
        self._cmb_paper.currentIndexChanged.connect(self._on_paper_changed)

        lay.addWidget(_grp('Paper Size', self._cmb_paper))
        lay.addWidget(_grp('Orientation', self._btn_port, self._btn_land))
        lay.addWidget(_sep())

        # Drawing scale
        self._cmb_scale = QComboBox()
        for name, _ in _SCALE_OPTIONS:
            self._cmb_scale.addItem(name)
        self._cmb_scale.setFixedWidth(185)
        self._cmb_scale.currentIndexChanged.connect(self._on_scale_changed)
        lay.addWidget(_grp('Drawing Scale', self._cmb_scale))
        lay.addWidget(_sep())

        # Display toggles
        self._btn_rulers = _rbtn('Rulers',       'Show/hide rulers',        checkable=True)
        self._btn_pgrid  = _rbtn('Grid',          'Show/hide grid',          checkable=True)
        self._btn_pbnd   = _rbtn('Page Boundary', 'Show/hide page boundary', checkable=True)
        self._btn_psnap  = _rbtn('Snap',          'Enable/disable snap',     checkable=True)
        for b in (self._btn_rulers, self._btn_pgrid, self._btn_pbnd, self._btn_psnap):
            b.setChecked(True)
        self._btn_rulers.toggled.connect(self._on_rulers_toggled)
        self._btn_pgrid.toggled.connect(self._canvas.toggle_grid)
        self._btn_pbnd.toggled.connect(self._canvas.set_show_page_boundary)
        self._btn_psnap.toggled.connect(self._on_snap_toggle)
        lay.addWidget(_grp('Display',
                           self._btn_rulers, self._btn_pgrid,
                           self._btn_pbnd,   self._btn_psnap))
        lay.addStretch()
        return w

    # ── Canvas area (rulers + grid layout) ───────────────────────────────────

    def _build_canvas_area(self):
        container = QWidget()
        grid      = QGridLayout(container)
        grid.setSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)

        self._ruler_corner = QWidget()
        self._ruler_corner.setFixedSize(RULER_W, RULER_W)
        self._ruler_corner.setStyleSheet(
            f'background:#1e2533;border-right:1px solid #2a3548;border-bottom:1px solid #2a3548;')

        self._h_ruler = HRuler(self._canvas, container)
        self._v_ruler = VRuler(self._canvas, container)

        grid.addWidget(self._ruler_corner, 0, 0)
        grid.addWidget(self._h_ruler,      0, 1)
        grid.addWidget(self._v_ruler,      1, 0)
        grid.addWidget(self._canvas,       1, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(1, 1)

        self.setCentralWidget(container)

    # ── Left presets dock ─────────────────────────────────────────────────────

    def _build_presets_dock(self):
        dock = QDockWidget('Elements', self)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setMinimumWidth(185)
        dock.setMaximumWidth(240)

        _CMB_CSS = """
            QComboBox {
                background: #1e2d40;
                color: #dce8f5;
                border: 1px solid #3a4f68;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 8.5pt;
                font-family: 'Segoe UI';
            }
            QComboBox:hover { border-color: #5a80aa; background: #253548; }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox QAbstractItemView {
                background: #1a2333;
                color: #dce8f5;
                selection-background-color: #2d4a6e;
                border: 1px solid #3a4f68;
                outline: none;
            }
        """
        _LBL_CSS = ('color: #7a9abf; font-size: 7.5pt; font-style: italic; '
                    'padding: 0px; margin-top: 8px; background: transparent;')

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            'QScrollArea { border: none; background: #1a2333; } '
            'QWidget#presets_body { background: #1a2333; }')

        body = QWidget()
        body.setObjectName('presets_body')
        vl = QVBoxLayout(body)
        vl.setSpacing(4)
        vl.setContentsMargins(10, 10, 10, 10)
        vl.setAlignment(Qt.AlignmentFlag.AlignTop)

        def _grp(label: str, items: list, on_activate) -> QComboBox:
            lbl = QLabel(label)
            lbl.setStyleSheet(_LBL_CSS)
            cmb = QComboBox()
            cmb.addItems(items)
            cmb.setStyleSheet(_CMB_CSS)
            cmb.activated.connect(on_activate)
            vl.addWidget(lbl)
            vl.addWidget(cmb)
            return cmb

        # ── Walls ─────────────────────────────────────────────────────────────
        _wall_keys   = list(WALL_TYPES.keys())
        _wall_labels = [WALL_TYPES[k][0] for k in _wall_keys]
        def _wall_act(idx):
            key = _wall_keys[idx]
            self._cmb_wall.setCurrentIndex(idx)
            self._canvas._wall_type = key
            self._set_tool(TOOL_WALL)
        _grp('Wall Type', _wall_labels, _wall_act)

        # ── Doors ─────────────────────────────────────────────────────────────
        _door_entries = [
            ("2'-0\"  (24\")", 24), ("2'-6\"  (30\")", 30),
            ("2'-8\"  (32\")", 32), ("3'-0\"  (36\")", 36),
            ("3'-6\"  (42\")", 42), ("6'-0\"  Double",  72),
        ]
        def _door_act(idx):
            dw = _door_entries[idx][1]
            _i = min(range(len(_DOOR_W_IN)), key=lambda i: abs(_DOOR_W_IN[i] - dw))
            self._cmb_door.setCurrentIndex(_i)
            self._canvas._door_width = dw
            self._set_tool(TOOL_DOOR)
        _grp('Door Width', [e[0] for e in _door_entries], _door_act)

        # ── Windows ───────────────────────────────────────────────────────────
        _win_widths = [24, 30, 36, 48, 60, 72]
        _win_labels = [f"{w}\"  ({w // 12}'-{w % 12:02d}\")" for w in _win_widths]
        def _win_act(idx):
            self._canvas._door_width = _win_widths[idx]
            self._set_tool(TOOL_WINDOW)
        _grp('Window Width', _win_labels, _win_act)

        # ── Posts ─────────────────────────────────────────────────────────────
        _post_entries = [('4×4  (3.5")', 3.5), ('6×6  (5.5")', 5.5), ('8×8  (7.5")', 7.5)]
        def _post_act(idx):
            sz = _post_entries[idx][1]
            _i = min(range(len(_POST_SIZES)), key=lambda i: abs(_POST_SIZES[i] - sz))
            self._cmb_post.setCurrentIndex(_i)
            self._canvas._post_size = sz
            self._set_tool(TOOL_POST)
        _grp('Post Size', [e[0] for e in _post_entries], _post_act)

        # ── Joists ────────────────────────────────────────────────────────────
        _joist_entries = [
            ('12"  o.c.  Horiz',    12,   'h'),
            ('16"  o.c.  Horiz',    16,   'h'),
            ('19.2"  o.c.  Horiz',  19.2, 'h'),
            ('24"  o.c.  Horiz',    24,   'h'),
            ('16"  o.c.  Vert',     16,   'v'),
            ('24"  o.c.  Vert',     24,   'v'),
        ]
        def _joist_act(idx):
            _, sp, dr = _joist_entries[idx]
            _i = min(range(len(_JOIST_SP_IN)), key=lambda i: abs(_JOIST_SP_IN[i] - sp))
            self._cmb_joist_sp.setCurrentIndex(_i)
            self._cmb_joist_dir.setCurrentIndex(0 if dr == 'h' else 1)
            self._canvas._joist_spacing   = sp
            self._canvas._joist_direction = dr
            self._set_tool(TOOL_JOIST)
        _grp('Joist Spacing', [e[0] for e in _joist_entries], _joist_act)

        # ── Shapes ────────────────────────────────────────────────────────────
        def _shape_act(idx):
            t = 'rect' if idx == 0 else 'ellipse'
            self._cmb_shape_type.setCurrentIndex(idx)
            self._canvas._shape_type = t
            self._set_tool(TOOL_SHAPE)
        _grp('Shape Type', ['Rectangle', 'Ellipse'], _shape_act)

        # ── Lines ─────────────────────────────────────────────────────────────
        _line_entries = [('Solid Line', 'solid', 0), ('Dashed Line', 'dash', 1), ('Dotted Line', 'dot', 2)]
        def _line_act(idx):
            _, s, i = _line_entries[idx]
            self._cmb_line_style.setCurrentIndex(i)
            self._canvas._line_style = s
            self._set_tool(TOOL_LINE)
        _grp('Line Style', [e[0] for e in _line_entries], _line_act)

        # ── Text ──────────────────────────────────────────────────────────────
        _TEXT_SIZES  = [6, 8, 10, 12, 14, 18, 24, 36]
        _text_labels = ['Tiny  (6pt)', 'Small  (8pt)', 'Normal  (10pt)', 'Normal  (12pt)',
                        'Large  (14pt)', 'Large  (18pt)', 'Title  (24pt)', 'Title  (36pt)']
        def _text_act(idx):
            self._cmb_text_size.setCurrentIndex(idx)
            self._canvas._text_size = _TEXT_SIZES[idx]
            self._set_tool(TOOL_TEXT)
        _grp('Text Size', _text_labels, _text_act)

        vl.addStretch()

        # ── Tool shortcuts bar ────────────────────────────────────────────────
        _BTN_CSS = """
            QPushButton {
                background: #1e2d40; color: #dce8f5;
                border: 1px solid #3a4f68; border-radius: 3px;
                padding: 5px 4px; font-size: 8pt;
            }
            QPushButton:hover   { background: #253548; border-color: #5a80aa; }
            QPushButton:pressed { background: #1e3558; }
            QPushButton:checked { background: #1e3a5a; border-color: #5a90c0;
                                  font-weight: bold; }
        """
        tool_row = QHBoxLayout()
        tool_row.setSpacing(4)
        btn_sel = QPushButton('\u2196  Select')
        btn_pan = QPushButton('\u270b  Pan')
        btn_sel.setCheckable(True)
        btn_pan.setCheckable(True)
        btn_sel.setChecked(True)
        for b in (btn_sel, btn_pan):
            b.setStyleSheet(_BTN_CSS)
        def _set_sel():
            btn_sel.setChecked(True); btn_pan.setChecked(False)
            self._set_tool(TOOL_SELECT)
        def _set_pan():
            btn_pan.setChecked(True); btn_sel.setChecked(False)
            self._set_tool(TOOL_PAN)
        btn_sel.clicked.connect(_set_sel)
        btn_pan.clicked.connect(_set_pan)
        tool_row.addWidget(btn_sel)
        tool_row.addWidget(btn_pan)
        vl.addLayout(tool_row)
        self._preset_btn_sel = btn_sel
        self._preset_btn_pan = btn_pan

        scroll.setWidget(body)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    # ── Properties dock ───────────────────────────────────────────────────────

    def _build_properties_dock(self):
        dock = QDockWidget('Properties', self)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setMinimumWidth(190)
        dock.setMaximumWidth(260)

        def _sep_h():
            s = QFrame(); s.setFrameShape(QFrame.Shape.HLine)
            s.setStyleSheet('color:#d0d0cc; margin:0;'); return s

        def _sec(text):
            lbl = QLabel(f'<b>{text}</b>')
            lbl.setStyleSheet('color:#7eb8f0; font-size:10px; margin-top:4px;')
            return lbl

        def _dbl(lo=-9999.0, hi=9999.0, dec=2, suf=''):
            sb = QDoubleSpinBox(); sb.setRange(lo, hi)
            sb.setDecimals(dec); sb.setSuffix(suf)
            sb.setFixedWidth(108); return sb

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        pw  = QWidget()
        pvl = QVBoxLayout(pw)
        pvl.setContentsMargins(6, 6, 6, 6)
        pvl.setSpacing(4)
        pvl.setAlignment(Qt.AlignmentFlag.AlignTop)

        # — Info label —
        self._prop_info = QLabel('No selection')
        self._prop_info.setWordWrap(True)
        self._prop_info.setFont(QFont('Courier New', 9))
        pvl.addWidget(self._prop_info)
        pvl.addWidget(_sep_h())

        # — Position —
        self._prop_pos_frame = QFrame()
        pf = QVBoxLayout(self._prop_pos_frame)
        pf.setContentsMargins(0, 0, 0, 0); pf.setSpacing(3)
        pf.addWidget(_sec('Position'))
        pfm = QFormLayout(); pfm.setSpacing(3)
        self._prop_x = _dbl(suf=' in')
        self._prop_y = _dbl(suf=' in')
        pfm.addRow('X:', self._prop_x)
        pfm.addRow('Y:', self._prop_y)
        pf.addLayout(pfm)
        pvl.addWidget(self._prop_pos_frame)

        # — Size —
        self._prop_size_frame = QFrame()
        sf = QVBoxLayout(self._prop_size_frame)
        sf.setContentsMargins(0, 0, 0, 0); sf.setSpacing(3)
        sf.addWidget(_sec('Size'))
        sfm = QFormLayout(); sfm.setSpacing(3)
        self._prop_w = _dbl(lo=0.5, suf=' in')
        self._prop_h = _dbl(lo=0.5, suf=' in')
        sfm.addRow('W:', self._prop_w)
        sfm.addRow('H:', self._prop_h)
        sf.addLayout(sfm)
        pvl.addWidget(self._prop_size_frame)

        # — Line length —
        self._prop_line_frame = QFrame()
        lf = QVBoxLayout(self._prop_line_frame)
        lf.setContentsMargins(0, 0, 0, 0); lf.setSpacing(3)
        lf.addWidget(_sec('Line'))
        lfm = QFormLayout(); lfm.setSpacing(3)
        self._prop_line_length = QLineEdit()
        self._prop_line_length.setFixedWidth(108)
        self._prop_line_length.setPlaceholderText("e.g. 10' 6\"")
        lfm.addRow('Length:', self._prop_line_length)
        lf.addLayout(lfm)
        pvl.addWidget(self._prop_line_frame)

        # — Text —
        self._prop_text_frame = QFrame()
        tf = QVBoxLayout(self._prop_text_frame)
        tf.setContentsMargins(0, 0, 0, 0); tf.setSpacing(3)
        tf.addWidget(_sec('Text'))
        tfm = QFormLayout(); tfm.setSpacing(3)
        self._prop_text_edit = QLineEdit()
        self._prop_font_size = _dbl(lo=4, hi=200, dec=0, suf=' pt')
        tfm.addRow('Content:',   self._prop_text_edit)
        tfm.addRow('Font size:', self._prop_font_size)
        tf.addLayout(tfm)
        pvl.addWidget(self._prop_text_frame)

        pvl.addWidget(_sep_h())
        self._btn_style = QPushButton('Style…')
        self._btn_style.setToolTip('Change color / style (Shape, Line, Text)')
        self._btn_style.clicked.connect(self._act_style_dialog)
        pvl.addWidget(self._btn_style)
        self._btn_lock = QPushButton('🔓  Lock')
        self._btn_lock.setToolTip('Lock selected items so they cannot be moved')
        self._btn_lock.clicked.connect(self._prop_commit_lock)
        pvl.addWidget(self._btn_lock)
        pvl.addStretch()

        scroll.setWidget(pw)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        # Wire commit signals
        self._prop_x.editingFinished.connect(self._prop_commit_xy)
        self._prop_y.editingFinished.connect(self._prop_commit_xy)
        self._prop_w.editingFinished.connect(self._prop_commit_wh)
        self._prop_h.editingFinished.connect(self._prop_commit_wh)
        self._prop_text_edit.editingFinished.connect(self._prop_commit_text)
        self._prop_font_size.editingFinished.connect(self._prop_commit_font)
        self._prop_line_length.editingFinished.connect(self._prop_commit_line_length)

        # Initially hidden
        self._prop_pos_frame.setVisible(False)
        self._prop_size_frame.setVisible(False)
        self._prop_text_frame.setVisible(False)
        self._prop_line_frame.setVisible(False)

    def _build_layers_dock(self):
        dock = QDockWidget('Layers', self)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        dock.setMinimumWidth(170)
        dock.setMaximumWidth(260)

        w  = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(4, 4, 4, 4)
        vl.setSpacing(4)

        # Toolbar: + − rename
        hbar = QHBoxLayout()
        hbar.setSpacing(2)
        self._btn_add_layer = QPushButton('+')
        self._btn_del_layer = QPushButton('\u2212')
        self._btn_ren_layer = QPushButton('\u270e')
        for b in (self._btn_add_layer, self._btn_del_layer, self._btn_ren_layer):
            b.setFixedSize(24, 24)
        hbar.addStretch()
        hbar.addWidget(self._btn_add_layer)
        hbar.addWidget(self._btn_del_layer)
        hbar.addWidget(self._btn_ren_layer)
        vl.addLayout(hbar)

        # Layer table: 👁 | 🔒 | Name
        self._layer_tbl = QTableWidget(0, 3)
        self._layer_tbl.setHorizontalHeaderLabels(['\U0001f441', '\U0001f512', 'Name'])
        hh = self._layer_tbl.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._layer_tbl.setColumnWidth(0, 26)
        self._layer_tbl.setColumnWidth(1, 26)
        self._layer_tbl.verticalHeader().hide()
        self._layer_tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._layer_tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._layer_tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        vl.addWidget(self._layer_tbl)

        dock.setWidget(w)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        self._btn_add_layer.clicked.connect(self._act_add_layer)
        self._btn_del_layer.clicked.connect(self._act_del_layer)
        self._btn_ren_layer.clicked.connect(self._act_ren_layer)
        self._layer_tbl.currentCellChanged.connect(
            lambda row, col, prow, pcol: self._on_layer_row_changed(row))
        self._layer_tbl.itemChanged.connect(self._on_layer_item_changed)
        self._layer_tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._layer_tbl.customContextMenuRequested.connect(self._show_layers_context_menu)

    def _refresh_layers_ui(self):
        if not hasattr(self, '_layer_tbl'):
            return
        layers = self._canvas.get_layers()
        active = self._canvas._active_layer
        tbl    = self._layer_tbl
        tbl.blockSignals(True)
        tbl.setRowCount(0)
        for i, layer in enumerate(layers):
            tbl.insertRow(i)
            tbl.setRowHeight(i, 22)

            v = QTableWidgetItem()
            v.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            v.setCheckState(Qt.CheckState.Checked if layer['visible']
                            else Qt.CheckState.Unchecked)
            v.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tbl.setItem(i, 0, v)

            lk = QTableWidgetItem()
            lk.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            lk.setCheckState(Qt.CheckState.Checked if layer['locked']
                             else Qt.CheckState.Unchecked)
            lk.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tbl.setItem(i, 1, lk)

            nm = QTableWidgetItem(layer['name'])
            nm.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            if i == active:
                f = nm.font(); f.setBold(True); nm.setFont(f)
            tbl.setItem(i, 2, nm)

        tbl.blockSignals(False)
        tbl.selectRow(active)

        if hasattr(self, '_layer_combo'):
            self._layer_combo.blockSignals(True)
            self._layer_combo.clear()
            for layer in layers:
                self._layer_combo.addItem(layer['name'])
            self._layer_combo.setCurrentIndex(active)
            self._layer_combo.blockSignals(False)

    def _on_layer_row_changed(self, row: int):
        if row < 0:
            return
        self._canvas.set_active_layer(row)
        tbl = self._layer_tbl
        tbl.blockSignals(True)
        for i in range(tbl.rowCount()):
            nm = tbl.item(i, 2)
            if nm:
                f = nm.font(); f.setBold(i == row); nm.setFont(f)
        tbl.blockSignals(False)
        if hasattr(self, '_layer_combo'):
            self._layer_combo.blockSignals(True)
            self._layer_combo.setCurrentIndex(row)
            self._layer_combo.blockSignals(False)

    def _on_layer_item_changed(self, item: QTableWidgetItem):
        row = item.row()
        col = item.column()
        if col == 0:
            self._canvas.set_layer_visible(row,
                item.checkState() == Qt.CheckState.Checked)
        elif col == 1:
            self._canvas.set_layer_locked(row,
                item.checkState() == Qt.CheckState.Checked)

    def _act_add_layer(self):
        name, ok = QInputDialog.getText(
            self, 'Add Layer', 'Layer name:',
            text=f'Layer {len(self._canvas.get_layers())}')
        if ok and name.strip():
            self._canvas.add_layer(name.strip())

    def _act_del_layer(self):
        row = self._layer_tbl.currentRow()
        if row <= 0:
            QMessageBox.information(self, 'Delete Layer',
                                    'Cannot delete Layer 0.')
            return
        layer_name = self._canvas.get_layers()[row]['name']
        if (QMessageBox.question(
                self, 'Delete Layer',
                f'Delete \u201c{layer_name}\u201d? Items on it will move to Layer 0.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                == QMessageBox.StandardButton.Yes):
            self._canvas.delete_layer(row)

    def _act_ren_layer(self):
        row = self._layer_tbl.currentRow()
        if row < 0:
            return
        old  = self._canvas.get_layers()[row]['name']
        name, ok = QInputDialog.getText(self, 'Rename Layer', 'New name:', text=old)
        if ok and name.strip():
            self._canvas.rename_layer(row, name.strip())

    # ── Properties dock ──────────────────────────────────────────────────────────

    def _on_selection_changed(self, items: list):
        from items import RoomItem, ShapeItem, TextItem
        self._props_updating = True
        try:
            if not items:
                self._prop_info.setText('No selection')
                self._prop_pos_frame.setVisible(False)
                self._prop_size_frame.setVisible(False)
                self._prop_text_frame.setVisible(False)
                self._prop_line_frame.setVisible(False)
                self._btn_lock.setText('\U0001f513  Lock')
                self._btn_lock.setEnabled(False)
                return

            if len(items) == 1:
                item = items[0]
                self._prop_info.setText(
                    item.info_str() if hasattr(item, 'info_str')
                    else type(item).__name__)

                # Position
                p = item.pos()
                self._prop_x.setValue(p.x())
                self._prop_y.setValue(p.y())
                self._prop_pos_frame.setVisible(True)

                # Size
                if isinstance(item, RoomItem):
                    r = item.rect()
                    self._prop_w.setValue(r.width())
                    self._prop_h.setValue(r.height())
                    self._prop_size_frame.setVisible(True)
                elif isinstance(item, ShapeItem):
                    self._prop_w.setValue(item.w)
                    self._prop_h.setValue(item.h)
                    self._prop_size_frame.setVisible(True)
                else:
                    self._prop_size_frame.setVisible(False)

                # Line length
                from items import LineItem as _LineItem, _ft as _ft_fn
                if isinstance(item, _LineItem):
                    ln = item.line()
                    p  = item.pos()
                    L  = QLineF(p.x() + ln.x1(), p.y() + ln.y1(),
                                p.x() + ln.x2(), p.y() + ln.y2()).length()
                    self._prop_line_length.setText(_ft_fn(L / 12))
                    self._prop_line_frame.setVisible(True)
                else:
                    self._prop_line_frame.setVisible(False)

                # Text
                if isinstance(item, TextItem):
                    self._prop_text_edit.setText(item.text)
                    self._prop_font_size.setValue(item.font_size)
                    self._prop_text_frame.setVisible(True)
                else:
                    self._prop_text_frame.setVisible(False)

                # Lock button
                lk = getattr(item, '_locked', False)
                self._btn_lock.setText('\U0001f512  Unlock' if lk else '\U0001f513  Lock')
                self._btn_lock.setEnabled(True)

            else:
                lines = [f'{len(items)} item(s) selected']
                for it in items[:5]:
                    if hasattr(it, 'info_str'):
                        lines.append('  ' + it.info_str().split('\n')[0])
                if len(items) > 5:
                    lines.append(f'  … +{len(items) - 5} more')
                self._prop_info.setText('\n'.join(lines))
                self._prop_pos_frame.setVisible(False)
                self._prop_size_frame.setVisible(False)
                self._prop_text_frame.setVisible(False)
                self._prop_line_frame.setVisible(False)

                # Lock button
                any_locked = any(getattr(it, '_locked', False) for it in items)
                self._btn_lock.setText('\U0001f512  Unlock' if any_locked else '\U0001f513  Lock')
                self._btn_lock.setEnabled(True)
        finally:
            self._props_updating = False

    def _prop_commit_xy(self):
        if self._props_updating:
            return
        items = self._canvas.scene().selectedItems()
        if len(items) != 1:
            return
        item = items[0]
        old  = item.pos()
        new  = QPointF(self._prop_x.value(), self._prop_y.value())
        if old != new:
            self._canvas._undo_stack.push(_MoveCmd([(item, old, new)]))

    def _prop_commit_wh(self):
        if self._props_updating:
            return
        from items import RoomItem, ShapeItem
        items = self._canvas.scene().selectedItems()
        if len(items) != 1:
            return
        item = items[0]
        nw, nh = self._prop_w.value(), self._prop_h.value()
        if isinstance(item, RoomItem):
            r = item.rect()
            ow, oh = r.width(), r.height()
            if ow != nw or oh != nh:
                def _a(item=item, nw=nw, nh=nh): item.setRect(0, 0, nw, nh); item.update()
                def _r(item=item, ow=ow, oh=oh): item.setRect(0, 0, ow, oh); item.update()
                _a()  # apply immediately
                self._canvas._undo_stack.push(_PropCmd('Resize', _a, _r))
        elif isinstance(item, ShapeItem):
            ow, oh = item.w, item.h
            if ow != nw or oh != nh:
                def _a(item=item, nw=nw, nh=nh): item.w = nw; item.h = nh; item.update()
                def _r(item=item, ow=ow, oh=oh): item.w = ow; item.h = oh; item.update()
                _a()  # apply immediately
                self._canvas._undo_stack.push(_PropCmd('Resize', _a, _r))

    def _prop_commit_text(self):
        if self._props_updating:
            return
        from items import TextItem
        items = self._canvas.scene().selectedItems()
        if len(items) != 1 or not isinstance(items[0], TextItem):
            return
        item     = items[0]
        old_text = item.text
        new_text = self._prop_text_edit.text()
        if old_text != new_text:
            def _a(item=item, t=new_text): item.text = t; item.update()
            def _r(item=item, t=old_text): item.text = t; item.update()
            _a()  # apply immediately
            self._canvas._undo_stack.push(_PropCmd('Edit Text', _a, _r))

    def _prop_commit_font(self):
        if self._props_updating:
            return
        from items import TextItem
        items = self._canvas.scene().selectedItems()
        if len(items) != 1 or not isinstance(items[0], TextItem):
            return
        item     = items[0]
        old_size = item.font_size
        new_size = int(self._prop_font_size.value())
        if old_size != new_size:
            def _a(item=item, s=new_size): item.font_size = s; item.update()
            def _r(item=item, s=old_size): item.font_size = s; item.update()
            _a()  # apply immediately
            self._canvas._undo_stack.push(_PropCmd('Font Size', _a, _r))

    # ── helpers ───────────────────────────────────────────────────────────────

    def _prop_commit_lock(self):
        """Toggle lock/unlock on all selected items (undoable)."""
        items = self._canvas.scene().selectedItems()
        if not items:
            return
        # Determine target state: if any are unlocked, lock all; else unlock all
        any_unlocked = any(not getattr(i, '_locked', False) for i in items)
        new_locked   = any_unlocked
        locked_items = [(i, getattr(i, '_locked', False)) for i in items
                        if hasattr(i, 'set_locked')]
        if not locked_items:
            return

        def _apply(state=new_locked):
            for item, _ in locked_items:
                item.set_locked(state)
            lbl = '\U0001f512  Unlock' if state else '\U0001f513  Lock'
            self._btn_lock.setText(lbl)

        def _revert():
            for item, old in locked_items:
                item.set_locked(old)
            any_locked = any(old for _, old in locked_items)
            lbl = '\U0001f512  Unlock' if any_locked else '\U0001f513  Lock'
            self._btn_lock.setText(lbl)

        verb = 'Lock' if new_locked else 'Unlock'
        _apply()                                                   # apply immediately
        self._canvas._undo_stack.push(_PropCmd(verb, _apply, _revert))

    @staticmethod
    def _parse_length_to_inches(s: str):
        """Parse a measurement string to total inches.

        Accepted forms (case-insensitive, spaces optional):
          60' 9 3/4"   60'9"   9 3/4"   60'   9"   3/4"   729.75
        Returns float inches, or None on parse failure.
        """
        import re, math
        s = s.strip().replace('\u201c', '"').replace('\u201d', '"')
        pat = re.compile(
            r"""^\s*
            (?:(\d+(?:\.\d+)?)\s*')?      # optional feet
            \s*
            (?:
              (\d+(?:\.\d+)?)\s+(\d+)/(\d+)\s*"   # whole-inches + fraction
            | (\d+(?:\.\d+)?)\s*/\s*(\d+)\s*"     # fraction only (no whole)
            | (\d+(?:\.\d+)?)\s*"                  # decimal / whole inches
            )?
            \s*$""", re.VERBOSE)
        m = pat.match(s)
        if not m:
            try:
                return float(s)    # bare number → inches
            except ValueError:
                return None
        total = 0.0
        if m.group(1) is not None:
            total += float(m.group(1)) * 12.0
        if m.group(2) is not None:                         # whole + fraction
            total += float(m.group(2)) + float(m.group(3)) / float(m.group(4))
        elif m.group(5) is not None:                       # fraction only
            total += float(m.group(5)) / float(m.group(6))
        elif m.group(7) is not None:                       # decimal/whole
            total += float(m.group(7))
        return total if total > 0 else None

    def _prop_commit_line_length(self):
        if self._props_updating:
            return
        from items import LineItem as _LineItem, _LineResizeCmd
        items = self._canvas.scene().selectedItems()
        if len(items) != 1 or not isinstance(items[0], _LineItem):
            return
        item  = items[0]
        text  = self._prop_line_length.text().strip()
        new_inches = self._parse_length_to_inches(text)
        if new_inches is None or new_inches <= 0:
            # restore display to current value
            from items import _ft as _ft_fn
            ln = item.line()
            p  = item.pos()
            L  = QLineF(p.x() + ln.x1(), p.y() + ln.y1(),
                        p.x() + ln.x2(), p.y() + ln.y2()).length()
            self._prop_line_length.setText(_ft_fn(L / 12))
            return
        old_ln = QLineF(item.line())
        # Direction: keep p1 fixed, move p2
        angle  = old_ln.angle()            # degrees from +x axis
        import math
        rad    = math.radians(angle)
        dx     = math.cos(rad) * new_inches
        dy     = -math.sin(rad) * new_inches   # Qt y-axis is flipped
        new_ln = QLineF(old_ln.p1(), old_ln.p1() + QPointF(dx, dy))
        if abs(new_ln.length() - old_ln.length()) > 0.01:
            self._canvas._undo_stack.push(_LineResizeCmd(item, old_ln, new_ln))
            from items import _ft as _ft_fn
            self._props_updating = True
            self._prop_line_length.setText(_ft_fn(new_inches / 12))
            self._props_updating = False

    def _act_style_dialog(self):
        from items import ShapeItem, LineItem, TextItem
        sel    = self._canvas.scene().selectedItems()
        shapes = [i for i in sel if isinstance(i, ShapeItem)]
        lines_ = [i for i in sel if isinstance(i, LineItem)]
        texts  = [i for i in sel if isinstance(i, TextItem)]
        if not (shapes or lines_ or texts):
            QMessageBox.information(
                self, 'Style', 'Select Shape, Line, or Text items first.')
            return

        dlg = QDialog(self)
        dlg.setWindowTitle('Item Style')
        dlg.setMinimumWidth(260)
        lay = QFormLayout(dlg)
        lay.setSpacing(8)
        lay.setContentsMargins(12, 12, 12, 12)

        def _color_btn(hex_val: str) -> QPushButton:
            btn = QPushButton()
            btn.setFixedSize(80, 22)
            btn._hex = hex_val
            btn.setStyleSheet(f'background:{hex_val}; border:1px solid #888;')
            def _pick(_, b=btn):
                c = QColorDialog.getColor(QColor(b._hex), dlg)
                if c.isValid():
                    b._hex = c.name()
                    b.setStyleSheet(f'background:{b._hex}; border:1px solid #888;')
            btn.clicked.connect(_pick)
            return btn

        fill_btn = border_btn = line_btn = text_btn = None
        if shapes:
            fill_btn   = _color_btn(shapes[0].fill)
            border_btn = _color_btn(shapes[0].border)
            lay.addRow('Fill:', fill_btn)
            lay.addRow('Border:', border_btn)
        if lines_:
            line_btn = _color_btn(lines_[0].line_color)
            lay.addRow('Line Color:', line_btn)
        if texts:
            text_btn = _color_btn(texts[0].color)
            lay.addRow('Text Color:', text_btn)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addRow(bb)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            if fill_btn:
                for s in shapes:
                    s.fill = fill_btn._hex
                    s.update()
            if border_btn:
                for s in shapes:
                    s.border = border_btn._hex
                    s.update()
            if line_btn:
                for li in lines_:
                    li.line_color = line_btn._hex
                    li._apply_pen()
            if text_btn:
                for t in texts:
                    t.color = text_btn._hex
                    t.update()
    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._scale_lbl = QLabel("Scale: 1/4\" = 1'")
        self._scale_lbl.setStyleSheet('color:#666;font-size:8pt;margin-right:10px;')
        self._status.addPermanentWidget(self._scale_lbl)
        self._status.showMessage(_HINT)

    # ── Tool switching ────────────────────────────────────────────────────────

    def _set_tool(self, tool: str):
        self._canvas.set_tool(tool)
        btn = self._tool_btns.get(tool)
        if btn:
            btn.setChecked(True)

    # ── Design tab callbacks ──────────────────────────────────────────────────

    def _on_snap_changed(self, idx: int):
        self._canvas._snap = _SNAP_IN[idx] if idx < len(_SNAP_IN) else 12

    def _on_snap_toggle(self, on: bool):
        self._canvas._snap_enabled = on

    def _on_wall_type_changed(self, idx: int):
        keys = list(WALL_TYPES.keys())
        self._canvas._wall_type = keys[idx] if idx < len(keys) else 'interior'

    def _on_shape_type_changed(self, idx: int):
        self._canvas._shape_type = 'ellipse' if idx == 1 else 'rect'

    def _on_line_style_changed(self, idx: int):
        styles = ['solid', 'dash', 'dot']
        self._canvas._line_style = styles[idx] if idx < len(styles) else 'solid'

    def _on_text_size_changed(self, idx: int):
        sizes = [6, 8, 10, 12, 14, 18, 24, 36]
        self._canvas._text_size = sizes[idx] if idx < len(sizes) else 12

    def _on_door_width_changed(self, idx: int):
        self._canvas._door_width = _DOOR_W_IN[idx] if idx < len(_DOOR_W_IN) else 36

    def _on_joist_sp_changed(self, idx: int):
        self._canvas._joist_spacing = _JOIST_SP_IN[idx] if idx < len(_JOIST_SP_IN) else 16

    def _on_joist_dir_changed(self, idx: int):
        self._canvas._joist_direction = 'h' if idx == 0 else 'v'

    def _on_post_size_changed(self, idx: int):
        if idx == 3:
            val, ok = QInputDialog.getDouble(
                self, 'Post Size', 'Enter post size (inches):', 3.5, 0.5, 48, 2)
            if ok:
                self._canvas._post_size = val
        else:
            self._canvas._post_size = _POST_SIZES[idx] if idx < len(_POST_SIZES) else 3.5

    # ── Page tab callbacks ────────────────────────────────────────────────────

    def _apply_page_defaults(self):
        """Called once after all widgets exist to push initial scale/paper."""
        self._cmb_scale.setCurrentIndex(3)   # 1/4"=1ft
        self._cmb_paper.setCurrentIndex(0)   # Letter
        # Push to canvas (signals may not fire if indices were already at these values)
        self._on_scale_changed(3)
        self._on_paper_changed(0)

    def _on_scale_changed(self, idx: int):
        name, ratio = _SCALE_OPTIONS[idx]
        self._canvas.set_scale(ratio)
        short = name.split('(')[0].strip()
        if hasattr(self, '_scale_lbl'):
            self._scale_lbl.setText(f'Scale: {short}')

    def _on_paper_changed(self, idx: int):
        _, pw, ph = _PAPER_SIZES[idx]
        if hasattr(self, '_btn_land') and self._btn_land.isChecked():
            pw, ph = ph, pw
        self._canvas.set_paper(pw, ph)

    def _on_orient_changed(self, _portrait: bool):
        self._on_paper_changed(self._cmb_paper.currentIndex())

    def _on_rulers_toggled(self, visible: bool):
        self._h_ruler.setVisible(visible)
        self._v_ruler.setVisible(visible)
        self._ruler_corner.setVisible(visible)

    def _on_canvas_scale_changed(self, ratio: float):
        """Update scale combo when canvas scale changes (e.g. after file load)."""
        for i, (_, r) in enumerate(_SCALE_OPTIONS):
            if abs(r - ratio) < 0.01:
                self._cmb_scale.blockSignals(True)
                self._cmb_scale.setCurrentIndex(i)
                self._cmb_scale.blockSignals(False)
                break
        short = next((n.split('(')[0].strip() for n, r in _SCALE_OPTIONS
                      if abs(r - ratio) < 0.01), f'1:{ratio:.0f}')
        if hasattr(self, '_scale_lbl'):
            self._scale_lbl.setText(f'Scale: {short}')

    # ── Selection helpers ─────────────────────────────────────────────────────

    def _select_all(self):
        for item in self._canvas.scene().items():
            if item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable:
                item.setSelected(True)

    def _select_all_lines(self):
        from items import WallItem, DimensionItem
        for item in self._canvas.scene().items():
            item.setSelected(isinstance(item, (WallItem, DimensionItem)))

    def _group_selected(self):
        self._canvas.group_selected()

    def _ungroup_selected(self):
        self._canvas.ungroup_selected()

    def _delete_selected(self):
        self._canvas.delete_selected()

    # ── Alignment & distribution ───────────────────────────────────────────────

    def _align_items(self, mode: str):
        """Align or distribute selected items.
        mode: left | right | top | bottom | center_h | center_v | dist_h | dist_v
        """
        items = [i for i in self._canvas.scene().selectedItems()
                 if hasattr(i, 'to_dict')]
        if len(items) < 2:
            return
        if mode in ('dist_h', 'dist_v') and len(items) < 3:
            return

        rects    = [item.sceneBoundingRect() for item in items]
        old_pos  = [item.pos() for item in items]
        new_pos  = list(old_pos)          # will be replaced per-mode

        if mode == 'left':
            tx = min(r.left() for r in rects)
            new_pos = [p + QPointF(tx - r.left(), 0)
                       for p, r in zip(old_pos, rects)]

        elif mode == 'right':
            tx = max(r.right() for r in rects)
            new_pos = [p + QPointF(tx - r.right(), 0)
                       for p, r in zip(old_pos, rects)]

        elif mode == 'top':
            ty = min(r.top() for r in rects)
            new_pos = [p + QPointF(0, ty - r.top())
                       for p, r in zip(old_pos, rects)]

        elif mode == 'bottom':
            ty = max(r.bottom() for r in rects)
            new_pos = [p + QPointF(0, ty - r.bottom())
                       for p, r in zip(old_pos, rects)]

        elif mode == 'center_h':
            tx = sum(r.center().x() for r in rects) / len(rects)
            new_pos = [p + QPointF(tx - r.center().x(), 0)
                       for p, r in zip(old_pos, rects)]

        elif mode == 'center_v':
            ty = sum(r.center().y() for r in rects) / len(rects)
            new_pos = [p + QPointF(0, ty - r.center().y())
                       for p, r in zip(old_pos, rects)]

        elif mode == 'dist_h':
            order  = sorted(range(len(items)), key=lambda i: rects[i].left())
            s_it   = [items[i] for i in order]
            s_rc   = [rects[i] for i in order]
            s_op   = [old_pos[i] for i in order]
            span   = s_rc[-1].right() - s_rc[0].left()
            tw     = sum(r.width() for r in s_rc)
            gap    = (span - tw) / (len(s_it) - 1)
            cur_x  = s_rc[0].left()
            new_pos_map = {}
            for it, rc, op in zip(s_it, s_rc, s_op):
                new_pos_map[id(it)] = op + QPointF(cur_x - rc.left(), 0)
                cur_x += rc.width() + gap
            new_pos = [new_pos_map[id(it)] for it in items]

        elif mode == 'dist_v':
            order  = sorted(range(len(items)), key=lambda i: rects[i].top())
            s_it   = [items[i] for i in order]
            s_rc   = [rects[i] for i in order]
            s_op   = [old_pos[i] for i in order]
            span   = s_rc[-1].bottom() - s_rc[0].top()
            th     = sum(r.height() for r in s_rc)
            gap    = (span - th) / (len(s_it) - 1)
            cur_y  = s_rc[0].top()
            new_pos_map = {}
            for it, rc, op in zip(s_it, s_rc, s_op):
                new_pos_map[id(it)] = op + QPointF(0, cur_y - rc.top())
                cur_y += rc.height() + gap
            new_pos = [new_pos_map[id(it)] for it in items]

        data = [(it, op, np) for it, op, np in zip(items, old_pos, new_pos)
                if op != np]
        if data:
            self._canvas._undo_stack.push(_MoveCmd(data))

    # ── Clipboard ────────────────────────────────────────────────────────────────

    def _copy_selected(self):
        sel = self._canvas.scene().selectedItems()
        if not sel:
            return
        self._clipboard = []
        for item in sel:
            if hasattr(item, 'to_dict'):
                d = item.to_dict()
                d['layer_idx'] = getattr(item, '_layer_idx', 0)
                self._clipboard.append(d)

    def _cut_selected(self):
        self._copy_selected()
        self._canvas.delete_selected()

    def _paste_from_clipboard(self):
        if self._clipboard:
            self._canvas.paste_items(self._clipboard)

    def _duplicate_selected(self):
        self._copy_selected()
        self._paste_from_clipboard()

    # ── Z-order / layer assignment ─────────────────────────────────────────────────

    def _bring_to_front(self):
        items = self._canvas.scene().selectedItems()
        if not items:
            return
        max_z = max((i.zValue() for i in self._canvas.scene().items()), default=0)
        for item in items:
            item.setZValue(max_z + 1)

    def _send_to_back(self):
        items = self._canvas.scene().selectedItems()
        if not items:
            return
        min_z = min((i.zValue() for i in self._canvas.scene().items()), default=0)
        for item in items:
            item.setZValue(min_z - 1)

    def _move_selected_to_layer(self, idx: int):
        layers = self._canvas.get_layers()
        if idx < 0 or idx >= len(layers):
            return
        layer = layers[idx]
        for item in self._canvas.scene().selectedItems():
            item._layer_idx = idx
            item.setVisible(layer['visible'])
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,
                         not layer['locked'])
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,
                         not layer['locked'])

    # ── Context menus ──────────────────────────────────────────────────────────────

    def _show_canvas_context_menu(self, pos):
        # Auto-select item under cursor if nothing is already selected
        scene_pos = self._canvas.mapToScene(pos)
        hit = self._canvas.scene().itemAt(scene_pos, self._canvas.transform())
        if hit and hasattr(hit, 'to_dict') and not hit.isSelected():
            self._canvas.scene().clearSelection()
            hit.setSelected(True)

        from items import ShapeItem, LineItem, TextItem
        selected = self._canvas.scene().selectedItems()
        menu     = QMenu(self)

        if selected:
            menu.addAction('Cu&t',       self._cut_selected).setShortcut('Ctrl+X')
            menu.addAction('&Copy',      self._copy_selected).setShortcut('Ctrl+C')
            pa = menu.addAction('&Paste', self._paste_from_clipboard)
            pa.setShortcut('Ctrl+V')
            pa.setEnabled(bool(self._clipboard))
            menu.addAction('D&uplicate', self._duplicate_selected).setShortcut('Ctrl+D')
            menu.addSeparator()
            menu.addAction('&Delete',    self._delete_selected).setShortcut('Del')
            menu.addSeparator()

            # Move to Layer submenu
            lm = menu.addMenu('Move to &Layer')
            for i, layer in enumerate(self._canvas.get_layers()):
                lm.addAction(layer['name']).triggered.connect(
                    lambda _, idx=i: self._move_selected_to_layer(idx))
            menu.addSeparator()

            menu.addAction('Bring to &Front', self._bring_to_front)
            menu.addAction('Send to &Back',   self._send_to_back)

            # Align submenu (only useful with ≥2 items selected)
            if len(selected) >= 2:
                menu.addSeparator()
                am = menu.addMenu('&Align / Distribute')
                for lbl, mode in [
                    ('Align &Left',               'left'),
                    ('Align &Right',              'right'),
                    ('Align &Top',                'top'),
                    ('Align &Bottom',             'bottom'),
                    ('Center on &Vertical Axis',  'center_h'),
                    ('Center on &Horizontal Axis','center_v'),
                    (None, None),
                    ('Distribute &Horizontally',  'dist_h'),
                    ('Distribute &Vertically',    'dist_v'),
                ]:
                    if lbl is None:
                        am.addSeparator()
                    else:
                        act = am.addAction(lbl)
                        act.triggered.connect(lambda _, m=mode: self._align_items(m))
                        if mode in ('dist_h', 'dist_v'):
                            act.setEnabled(len(selected) >= 3)

            has_style = any(isinstance(i, (ShapeItem, LineItem, TextItem))
                            for i in selected)
            if has_style:
                menu.addSeparator()
                menu.addAction('St&yle…', self._act_style_dialog)

            # Group / Ungroup
            menu.addSeparator()
            has_groups    = any(isinstance(i, GroupItem) for i in selected)
            non_group_cnt = sum(1 for i in selected
                                if not isinstance(i.parentItem(), GroupItem))
            if non_group_cnt >= 2:
                menu.addAction('&Group', self._group_selected).setShortcut('Ctrl+G')
            if has_groups:
                menu.addAction('&Ungroup', self._ungroup_selected).setShortcut('Ctrl+Shift+G')
        else:
            pa = menu.addAction('&Paste', self._paste_from_clipboard)
            pa.setShortcut('Ctrl+V')
            pa.setEnabled(bool(self._clipboard))
            menu.addSeparator()
            menu.addAction('Select &All', self._select_all).setShortcut('Ctrl+A')
            menu.addSeparator()
            menu.addAction('Zoom &In',
                           lambda: self._canvas.scale(1.25, 1.25))
            menu.addAction('Zoom &Out',
                           lambda: self._canvas.scale(1/1.25, 1/1.25))
            menu.addAction('&Fit All', self._canvas.zoom_fit).setShortcut('Ctrl+0')
            menu.addSeparator()
            menu.addAction('Toggle &Grid', self._canvas.toggle_grid)

        menu.exec(QCursor.pos())

    def _show_layers_context_menu(self, pos):
        row = self._layer_tbl.rowAt(pos.y())
        if row >= 0:
            self._layer_tbl.selectRow(row)
        menu = QMenu(self)
        if row >= 0:
            menu.addAction('Set &Active', lambda: (
                self._canvas.set_active_layer(row),
                self._refresh_layers_ui()))
            menu.addSeparator()
        menu.addAction('&Add Layer',   self._act_add_layer)
        if row > 0:
            menu.addAction('Re&name Layer', self._act_ren_layer)
            menu.addAction('&Delete Layer', self._act_del_layer)
        menu.exec(QCursor.pos())

    # ── File actions ──────────────────────────────────────────────────────────

    def _act_new(self):
        if QMessageBox.question(
                self, 'New Project', 'Start a new project? Unsaved changes will be lost.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self._canvas.new_project()
            self.setWindowTitle('ArchCAD  —  Untitled')

    def _act_open(self):
        if self._canvas.open_project():
            self._sync_title()

    def _act_save(self):
        if self._canvas.save_project():
            self._sync_title()

    def _act_save_as(self):
        if self._canvas.save_project(force_dialog=True):
            self._sync_title()

    def _act_export_pdf(self):
        """Render the drawing page to a PDF file."""
        path, _ = QFileDialog.getSaveFileName(
            self, 'Export PDF', '', 'PDF Files (*.pdf);;All Files (*)')
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'

        canvas  = self._canvas
        pw_in   = canvas._paper_phys_w      # physical paper width  (inches)
        ph_in   = canvas._paper_phys_h      # physical paper height (inches)
        scale   = canvas.scale_ratio        # scene units per paper inch

        writer = QPdfWriter(path)
        writer.setResolution(150)           # DPI for raster content
        writer.setPageSize(
            QPageSize(QSizeF(pw_in * 25.4, ph_in * 25.4),
                      QPageSize.Unit.Millimeter))
        writer.setPageMargins(QMarginsF(0, 0, 0, 0),
                              QPageLayout.Unit.Millimeter)

        painter = QPainter(writer)
        source  = QRectF(0, 0, pw_in * scale, ph_in * scale)
        target  = QRectF(painter.viewport())
        canvas.scene().render(painter, target, source)
        painter.end()

        QMessageBox.information(self, 'PDF Export', f'Saved:\n{path}')

    def _sync_title(self):
        p = self._canvas.project_path or 'Untitled'
        self.setWindowTitle(f'ArchCAD  —  {p}')

    # ── Auto-fill posts dialog ────────────────────────────────────────────────

    def _act_auto_posts(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('Auto-fill Posts')
        dlg.setFixedWidth(330)
        lay = QFormLayout(dlg)

        def _dsb(val, lo=-9999, hi=9999, suf=' ft', dec=1):
            sb = QDoubleSpinBox()
            sb.setRange(lo, hi); sb.setValue(val)
            sb.setSuffix(suf);   sb.setDecimals(dec)
            return sb

        ox = _dsb(0);  oy = _dsb(0)
        rw = _dsb(20, 1); rh = _dsb(20, 1)
        sx = _dsb(8, 1);  sy = _dsb(8, 1)
        lay.addRow('Origin X (ft):',       ox)
        lay.addRow('Origin Y (ft):',       oy)
        lay.addRow('Region Width (ft):',   rw)
        lay.addRow('Region Height (ft):',  rh)
        lay.addRow('Column Spacing X (ft):', sx)
        lay.addRow('Column Spacing Y (ft):', sy)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        lay.addRow(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._canvas.place_post_grid(
                ox.value() * 12, oy.value() * 12,
                rw.value() * 12, rh.value() * 12,
                sx.value() * 12, sy.value() * 12,
                self._canvas._post_size,
            )


