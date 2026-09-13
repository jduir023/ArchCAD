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
from PyQt6.QtGui  import (
    QAction, QFont, QKeySequence, QShortcut, QColor, QCursor,
    QPdfWriter, QPageSize, QPageLayout, QPainter,
)

from canvas import (
    CADCanvas, _MoveCmd, _PropCmd,
    TOOL_SELECT, TOOL_PAN, TOOL_ROOM, TOOL_WALL,
    TOOL_DOOR, TOOL_WINDOW, TOOL_DIMENSION,
    TOOL_POST, TOOL_JOIST, TOOL_SHAPE, TOOL_LINE, TOOL_TEXT,
    TOOL_FIXTURE,
)
from items  import WALL_TYPES, GroupItem
from rulers import HRuler, VRuler, RULER_W
from fixture_panel import FixturePanel
from estimator import EstimatorSettings, MaterialEstimator, CodeChecker, CodeReport

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
    (TOOL_SELECT,    '🖱️ Select', 'S'),
    (TOOL_ROOM,      '🏠 Room',   'M'),
    (TOOL_WALL,      '🧱 Wall',   'W'),
    (TOOL_DOOR,      '🚪 Door',   'D'),
    (TOOL_WINDOW,    '🪟 Window', 'N'),
    (TOOL_DIMENSION, '📏 Dim',    'E'),
    (TOOL_POST,      '🪵 Post',   'P'),
    (TOOL_JOIST,     '📐 Joists', 'J'),
    (TOOL_SHAPE,     '⬜ Shape',  'F'),
    (TOOL_LINE,      '✏️ Line',   'L'),
    (TOOL_TEXT,      '🔤 Text',   'T'),
]

_HINT = ("S/M/W/D/N/E/P/J/F/L/T = tools  |  Middle-drag = pan  |  "
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
    background: #111111;
    border-bottom: 2px solid #000000;
}
QWidget#tab_row {
    background: #050505;
    border-bottom: 1px solid #1a1a1a;
}
QPushButton#tab_btn {
    background: transparent;
    border: none;
    border-right: 1px solid #222;
    padding: 3px 18px;
    font-size: 9pt;
    font-family: 'Segoe UI';
    color: #888888;
    min-height: 22px;
}
QPushButton#tab_btn:checked {
    background: #111111;
    border-top: 3px solid #c85a14;
    border-bottom: none;
    font-weight: bold;
    color: #ff8833;
}
QPushButton#tab_btn:hover:!checked { background: #1a1a1a; }
QToolButton#rbtn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 2px 8px;
    font-size: 8.5pt;
    font-family: 'Segoe UI';
    color: #dddddd;
    min-width: 38px;
}
QToolButton#rbtn:hover        { background: #222; border: 1px solid #444; }
QToolButton#rbtn:pressed      { background: #1a1a1a; border: 1px solid #555; }
QToolButton#rbtn:checked      { background: #2a1a0e; border: 1px solid #c85a14; font-weight: bold; }
QLabel#grp_lbl {
    color: #666666; font-size: 7pt; font-family: 'Segoe UI';
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
        "  background: #1a1a1a; border: none;"
        "  border-bottom: 1px solid #111;"
        "  padding: 3px 6px; text-align: left;"
        "  font-size: 9pt; font-weight: bold; color: #ffffff;"
        "}"
        "QPushButton:hover { background: #2a2a2a; }"
    )
    _ITEM_CSS = (
        "QPushButton {"
        "  background: transparent; border: none;"
        "  border-bottom: 1px solid #1a1a1a;"
        "  padding: 3px 12px; text-align: left;"
        "  font-size: 8.5pt; color: #dddddd;"
        "}"
        "QPushButton:hover   { background: #222; }"
        "QPushButton:pressed { background: #111; }"
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
            'QLabel { color: #888; font-size: 7.5pt; font-style: italic;'
            ' padding: 5px 10px 2px 10px; background: transparent; }')
        self._body_lay.addWidget(lbl)


# ─────────────────────────────────────────────────────────────────────────────
# Estimator dock chrome — Redock instead of Close when floating
# ─────────────────────────────────────────────────────────────────────────────

class _DockChrome(QWidget):
    """Title bar for a dock: Undock while docked, Redock while floating. No close."""

    _CSS = """
        QWidget#dock_chrome { background: #111; }
        QLabel#dock_chrome_title {
            color: #ff8833; font-weight: bold; font-size: 9pt;
            background: transparent;
        }
        QPushButton#dock_chrome_btn {
            background: #1a1a1a; color: #e6e6e6;
            border: 1px solid #333; border-radius: 3px;
            padding: 2px 10px; font-size: 8pt;
        }
        QPushButton#dock_chrome_btn:hover {
            background: #2a1a0e; border-color: #c85a14; color: #ff8833;
        }
    """

    def __init__(self, dock: QDockWidget, title: str):
        super().__init__(dock)
        self.setObjectName('dock_chrome')
        self.setStyleSheet(self._CSS)
        self._dock = dock
        self._drag_offset = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 3, 4, 3)
        lay.setSpacing(6)
        lbl = QLabel(title)
        lbl.setObjectName('dock_chrome_title')
        self._btn = QPushButton('Undock')
        self._btn.setObjectName('dock_chrome_btn')
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setToolTip('Pop the estimator out into a floating window')
        self._btn.clicked.connect(self._toggle)
        lay.addWidget(lbl)
        lay.addStretch()
        lay.addWidget(self._btn)
        dock.topLevelChanged.connect(self._on_floating)
        self._on_floating(dock.isFloating())

    def _on_floating(self, floating: bool):
        if floating:
            self._btn.setText('Redock')
            self._btn.setToolTip('Snap the estimator back into the main layout')
            self._dock.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
            self._dock.show()
        else:
            self._btn.setText('Undock')
            self._btn.setToolTip('Pop the estimator out into a floating window')

    def _toggle(self):
        dock = self._dock
        if dock.isFloating():
            mw = dock.parent()
            while mw is not None and not isinstance(mw, QMainWindow):
                mw = mw.parent()
            if isinstance(mw, QMainWindow):
                area = getattr(dock, '_home_area',
                               Qt.DockWidgetArea.RightDockWidgetArea)
                mw.addDockWidget(area, dock)
            dock.setFloating(False)
            dock.show()
            dock.raise_()
        else:
            dock.setFloating(True)
            dock.resize(max(dock.width(), 320), max(dock.height(), 520))
            dock.show()
            dock.raise_()

    def mouseDoubleClickEvent(self, event):
        self._toggle()
        event.accept()

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.LeftButton
                and self._dock.isFloating()):
            gp = event.globalPosition().toPoint()
            self._drag_offset = gp - self._dock.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._drag_offset is not None
                and event.buttons() & Qt.MouseButton.LeftButton
                and self._dock.isFloating()):
            self._dock.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)


class _EstimatorDock(QDockWidget):
    """Estimator panel: can float, but Close always redocks instead of hiding."""

    def __init__(self, title: str, parent, home_area):
        super().__init__(title, parent)
        self._home_area = home_area
        self.setObjectName('estimator_dock')
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.setTitleBarWidget(_DockChrome(self, title))

    def closeEvent(self, event):
        # Native close (Alt+F4 on the floating window, etc.) snaps back.
        chrome = self.titleBarWidget()
        if chrome is not None and hasattr(chrome, '_toggle') and self.isFloating():
            chrome._toggle()
        else:
            self.setFloating(False)
            self.show()
        event.ignore()


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
        self._build_estimator_dock()
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
        a = QAction('🖨️  &Print…', self)
        a.setShortcut(QKeySequence.StandardKey.Print)
        a.triggered.connect(self._act_print); fm.addAction(a)
        a = QAction('Print Pre&view…', self)
        a.triggered.connect(self._act_print_preview); fm.addAction(a)
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
        a = QAction('Select &All', self)
        a.setShortcut(QKeySequence.StandardKey.SelectAll)
        a.triggered.connect(self._select_all); em.addAction(a)
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
        tm.addSeparator()
        a = QAction('Estimate &Materials…', self)
        a.setShortcut('Ctrl+E')
        a.triggered.connect(self._act_calculate_materials); tm.addAction(a)

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
        bn = _rbtn('📄 New',       'New project  (Ctrl+N)')
        bo = _rbtn('📂 Open…',     'Open project  (Ctrl+O)')
        bs = _rbtn('💾 Save',      'Save  (Ctrl+S)')
        ba = _rbtn('Save As…',     'Save As…')
        be  = _rbtn('Export PNG…', 'Export drawing to PNG')
        bpdf = _rbtn('Export PDF…','Export drawing to PDF  (Ctrl+Shift+P)')
        bpr = _rbtn('🖨️ Print',    'Print drawing  (Ctrl+P)')
        bpv = _rbtn('Preview',     'Print preview')
        bn.clicked.connect(self._act_new)
        bo.clicked.connect(self._act_open)
        bs.clicked.connect(self._act_save)
        ba.clicked.connect(self._act_save_as)
        be.clicked.connect(self._canvas.export_png)
        bpdf.clicked.connect(self._act_export_pdf)
        bpr.clicked.connect(self._act_print)
        bpv.clicked.connect(self._act_print_preview)
        lay.addWidget(_grp('File', bn, bo, bs, ba, be, bpdf, bpr, bpv))
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
        for b in (self._btn_rulers, self._btn_pgrid, self._btn_psnap):
            b.setChecked(True)
        self._btn_pbnd.setChecked(False)
        self._btn_rulers.toggled.connect(self._on_rulers_toggled)
        self._btn_pgrid.toggled.connect(self._canvas.toggle_grid)
        self._btn_pbnd.toggled.connect(self._canvas.set_show_page_boundary)
        self._btn_psnap.toggled.connect(self._on_snap_toggle)
        lay.addWidget(_grp('Display',
                           self._btn_rulers, self._btn_pgrid,
                           self._btn_pbnd,   self._btn_psnap))
        lay.addWidget(_sep())
        bprint = _rbtn('🖨️ Print', 'Print drawing  (Ctrl+P)')
        bprev  = _rbtn('Preview',  'Print preview')
        bprint.clicked.connect(self._act_print)
        bprev.clicked.connect(self._act_print_preview)
        lay.addWidget(_grp('Print', bprint, bprev))
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
            'background:#0a0a0a;border-right:1px solid #2a2a2a;border-bottom:1px solid #2a2a2a;')

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
                background: #141414;
                color: #e6e6e6;
                border: 1px solid #333;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 8.5pt;
                font-family: 'Segoe UI';
            }
            QComboBox:hover { border-color: #555; background: #1a1a1a; }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox QAbstractItemView {
                background: #111;
                color: #e6e6e6;
                selection-background-color: #c85a14;
                border: 1px solid #333;
                outline: none;
            }
        """
        _LBL_CSS = ('color: #888; font-size: 7.5pt; font-style: italic; '
                    'padding: 0px; margin-top: 8px; background: transparent;')

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            'QScrollArea { border: none; background: #0d0d0d; } '
            'QWidget#presets_body { background: #0d0d0d; }')

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
        _grp('🧱  Wall Type', _wall_labels, _wall_act)

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
        _grp('🚪  Door Width', [e[0] for e in _door_entries], _door_act)

        # ── Windows ───────────────────────────────────────────────────────────
        _win_widths = [24, 30, 36, 48, 60, 72]
        _win_labels = [f"{w}\"  ({w // 12}'-{w % 12:02d}\")" for w in _win_widths]
        def _win_act(idx):
            self._canvas._window_width = _win_widths[idx]
            self._set_tool(TOOL_WINDOW)
        _grp('🪟  Window Width', _win_labels, _win_act)

        # ── Posts ─────────────────────────────────────────────────────────────
        _post_entries = [('4×4  (3.5")', 3.5), ('6×6  (5.5")', 5.5), ('8×8  (7.5")', 7.5)]
        def _post_act(idx):
            sz = _post_entries[idx][1]
            _i = min(range(len(_POST_SIZES)), key=lambda i: abs(_POST_SIZES[i] - sz))
            self._cmb_post.setCurrentIndex(_i)
            self._canvas._post_size = sz
            self._set_tool(TOOL_POST)
        _grp('🪵  Post Size', [e[0] for e in _post_entries], _post_act)

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
        _grp('📐  Joist Spacing', [e[0] for e in _joist_entries], _joist_act)

        # ── Shapes ────────────────────────────────────────────────────────────
        def _shape_act(idx):
            t = 'rect' if idx == 0 else 'ellipse'
            self._cmb_shape_type.setCurrentIndex(idx)
            self._canvas._shape_type = t
            self._set_tool(TOOL_SHAPE)
        _grp('⬜  Shape Type', ['Rectangle', 'Ellipse'], _shape_act)

        # ── Lines ─────────────────────────────────────────────────────────────
        _line_entries = [('Solid Line', 'solid', 0), ('Dashed Line', 'dash', 1), ('Dotted Line', 'dot', 2)]
        def _line_act(idx):
            _, s, i = _line_entries[idx]
            self._cmb_line_style.setCurrentIndex(i)
            self._canvas._line_style = s
            self._set_tool(TOOL_LINE)
        _grp('✏️  Line Style', [e[0] for e in _line_entries], _line_act)

        # ── Text ──────────────────────────────────────────────────────────────
        _TEXT_SIZES  = [6, 8, 10, 12, 14, 18, 24, 36]
        _text_labels = ['Tiny  (6pt)', 'Small  (8pt)', 'Normal  (10pt)', 'Normal  (12pt)',
                        'Large  (14pt)', 'Large  (18pt)', 'Title  (24pt)', 'Title  (36pt)']
        def _text_act(idx):
            self._cmb_text_size.setCurrentIndex(idx)
            self._canvas._text_size = _TEXT_SIZES[idx]
            self._set_tool(TOOL_TEXT)
        _grp('🔤  Text Size', _text_labels, _text_act)

        # ── Fixture / Symbol Library ──────────────────────────────────────────
        sep = QFrame()
        sep.setStyleSheet('background: #222; min-height: 2px; max-height: 2px;'
                          ' margin: 6px 0px 2px 0px;')
        vl.addWidget(sep)

        hdr_fix = QLabel('  Fixtures & Symbols')
        hdr_fix.setStyleSheet(
            'color: #cccccc; font-size: 9pt; font-weight: bold;'
            ' font-family: "Segoe UI"; padding: 4px 6px 2px 6px;'
            ' background: transparent;'
        )
        vl.addWidget(hdr_fix)

        self._fixture_panel = FixturePanel()
        vl.addWidget(self._fixture_panel)

        def _on_fixture_selected(key: str):
            self._canvas._fixture_type = key
            self._set_tool(TOOL_FIXTURE)

        self._fixture_panel.fixture_selected.connect(_on_fixture_selected)

        vl.addStretch()

        # ── Tool shortcuts bar ────────────────────────────────────────────────
        _BTN_CSS = """
            QPushButton {
                background: #141414; color: #e6e6e6;
                border: 1px solid #333; border-radius: 3px;
                padding: 5px 4px; font-size: 8pt;
            }
            QPushButton:hover   { background: #222; border-color: #555; }
            QPushButton:pressed { background: #111; }
            QPushButton:checked { background: #2a1a0e; border-color: #c85a14;
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
            lbl.setStyleSheet('color:#ff8833; font-size:10px; margin-top:4px;')
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

        # — Rotation —
        self._prop_rotation_frame = QFrame()
        rotf = QVBoxLayout(self._prop_rotation_frame)
        rotf.setContentsMargins(0, 0, 0, 0); rotf.setSpacing(3)
        rotf.addWidget(_sec('Rotation'))
        rotfm = QFormLayout(); rotfm.setSpacing(3)
        self._prop_rotation = _dbl(lo=-360.0, hi=360.0, dec=1, suf='°')
        self._prop_rotation.setSingleStep(15.0)
        rotfm.addRow('Angle:', self._prop_rotation)
        rotf.addLayout(rotfm)
        pvl.addWidget(self._prop_rotation_frame)

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
        self._prop_rotation.editingFinished.connect(self._prop_commit_rotation)

        # Initially hidden
        self._prop_pos_frame.setVisible(False)
        self._prop_size_frame.setVisible(False)
        self._prop_text_frame.setVisible(False)
        self._prop_line_frame.setVisible(False)
        self._prop_rotation_frame.setVisible(False)

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

    # ── Estimator dock ────────────────────────────────────────────────────────

    def _build_estimator_dock(self):
        from PyQt6.QtWidgets import QCheckBox, QSpinBox, QSizePolicy
        dock = _EstimatorDock(
            '📊  Estimator', self, Qt.DockWidgetArea.RightDockWidgetArea)
        dock.setMinimumWidth(240)

        root = QWidget()
        vl   = QVBoxLayout(root)
        vl.setSpacing(4)
        vl.setContentsMargins(6, 6, 6, 6)

        def _label(txt):
            lb = QLabel(txt)
            lb.setStyleSheet('font-weight: bold; font-size: 10px;')
            return lb

        def _row(label_txt, widget):
            row = QWidget()
            hl  = QHBoxLayout(row)
            hl.setContentsMargins(0, 0, 0, 0)
            lb = QLabel(label_txt)
            lb.setFixedWidth(132)
            hl.addWidget(lb)
            hl.addWidget(widget)
            return row

        def _dsb(val, lo=0.0, hi=9999.0, step=0.5, dec=1, suffix=''):
            sb = QDoubleSpinBox()
            sb.setRange(lo, hi); sb.setValue(val)
            sb.setSingleStep(step); sb.setDecimals(dec)
            if suffix: sb.setSuffix(suffix)
            return sb

        def _combo(items, current=''):
            cb = QComboBox()
            cb.addItems(items)
            if current in items:
                cb.setCurrentText(current)
            return cb

        def _chk(txt, checked=True):
            cb = QCheckBox(txt)
            cb.setChecked(checked)
            return cb

        # ── Settings section ──────────────────────────────────────────────────
        vl.addWidget(_label('── 🏠  Building ──'))

        # Building type selector — drives which sub-settings are visible
        self._est_bldg_type = _combo(['Building', 'Deck', 'Pole Barn'], 'Building')
        vl.addWidget(_row('🏠  Type:', self._est_bldg_type))

        # Detect-from-drawing button
        self._est_detect_btn = QPushButton('🔍  Detect from Drawing')
        self._est_detect_btn.setToolTip(
            'Scans the drawing for Room items (or JoistFill areas as fallback)\n'
            'and populates the section list below with their dimensions.\n\n'
            'To add a section: select the Room tool (M), then click-drag\n'
            'a rectangle on the canvas.  Double-click a room to set its label.')
        self._est_detect_btn.clicked.connect(self._est_detect_sections)
        vl.addWidget(self._est_detect_btn)

        # Dynamic sections container
        self._est_sections_rows: list[dict] = []          # [{label, w, l, widget}]
        self._est_sections_vl   = QVBoxLayout()
        self._est_sections_vl.setSpacing(2)
        self._est_sections_vl.setContentsMargins(0, 0, 0, 0)
        sections_wrapper = QWidget()
        sections_wrapper.setLayout(self._est_sections_vl)
        vl.addWidget(sections_wrapper)

        # Add-section button
        self._est_add_section_btn = QPushButton('➕  Add Section')
        self._est_add_section_btn.clicked.connect(
            lambda: self._est_add_section_row())
        vl.addWidget(self._est_add_section_btn)

        # Seed with one default section
        self._est_add_section_row('Main', 20.0, 30.0)

        self._est_door_count  = QSpinBox()
        self._est_door_count.setRange(0, 50); self._est_door_count.setValue(2)
        self._est_win_count   = QSpinBox()
        self._est_win_count.setRange(0, 50); self._est_win_count.setValue(4)
        self._est_door_row = _row('🚪  Door count:',   self._est_door_count)
        self._est_win_row  = _row('🪟  Window count:', self._est_win_count)
        vl.addWidget(self._est_door_row)
        vl.addWidget(self._est_win_row)

        # Wire type combo AFTER all widgets exist
        self._est_bldg_type.currentTextChanged.connect(self._est_on_type_changed)

        self._est_lbl_substructure = _label('── 🏗️  Substructure ──')
        vl.addWidget(self._est_lbl_substructure)
        self._est_foundation = _combo(
            ['Posts (4x4)', 'Posts (6x6)', 'Footer & CMU Block',
             'Concrete Pad (Slab)', 'Poured Concrete Wall'],
            'Posts (4x4)')
        self._est_post_sx   = _dsb(8.0, 1, 50, 0.5, 1, ' ft')
        self._est_post_sy   = _dsb(8.0, 1, 50, 0.5, 1, ' ft')
        self._est_post_ht   = _dsb(3.0, 1, 30, 0.5, 1, ' ft')
        self._est_crawl_ht  = _dsb(30.0, 18, 72, 6, 0, '"')
        self._est_joist_sz  = _combo(['2x6','2x8','2x10','2x12'], '2x10')
        self._est_fdn_row      = _row('🏗️  Foundation:',   self._est_foundation)
        self._est_crawl_row    = _row('⬇️  Crawl space:',  self._est_crawl_ht)
        self._est_post_sx_row  = _row('↔️  Post space X:', self._est_post_sx)
        self._est_post_sy_row  = _row('↕️  Post space Y:', self._est_post_sy)
        self._est_post_ht_row  = _row('📏  Post height:',  self._est_post_ht)
        self._est_joist_sz_row = _row('🪵  Joist size:',    self._est_joist_sz)
        vl.addWidget(self._est_fdn_row)
        vl.addWidget(self._est_post_sx_row)
        vl.addWidget(self._est_post_sy_row)
        vl.addWidget(self._est_post_ht_row)
        vl.addWidget(self._est_crawl_row)
        vl.addWidget(self._est_joist_sz_row)

        # ── Pole Barn settings (KY Ag/Commercial, IBC 2018 / KBC) ────────────
        self._est_lbl_pb = _label('── 🏚️  Pole Barn (KY) ──')
        vl.addWidget(self._est_lbl_pb)
        # Column: buried timber or embedded steel — 6x6 min per KBC
        self._est_pb_col_size  = _combo(['6x6','6x8','8x8','8x10','W6x9 steel'],
                                        '6x6')
        # Column spacing: 8, 10, 12 ft typical; KBC allows up to 12 ft
        self._est_pb_col_sp    = _dsb(10.0, 6, 20, 2, 0, ' ft')
        # Column embedment depth (KY frost 24"; rule-of-thumb = building ht/5 + 2 ft)
        self._est_pb_col_embed = _dsb(4.0, 2, 8, 0.5, 1, ' ft')
        # Column height above grade
        self._est_pb_col_ht    = _dsb(12.0, 8, 30, 1, 0, ' ft')
        # Girt (horizontal siding nailer) spacing
        self._est_pb_girt_sp   = _combo(['24" o.c.', '48" o.c.', '60" o.c.'], '48" o.c.')
        # Truss/rafter spacing
        self._est_pb_truss_sp  = _combo(['4 ft', '8 ft', '10 ft', '12 ft'], '4 ft')
        # Purlin spacing (roof nailer)
        self._est_pb_purlin_sp = _combo(['24" o.c.', '36" o.c.'], '24" o.c.')
        # Roofing type for pole barn
        self._est_pb_roof_type = _combo(['Metal panels', 'Shingles'], 'Metal panels')
        # Siding type for pole barn
        self._est_pb_siding    = _combo(['Metal panels', 'Board & batten', 'LP SmartSide'],
                                        'Metal panels')
        # Concrete apron / skirt board
        self._est_pb_skirt     = _combo(['Pressure-treated skirt board',
                                         'Concrete grade beam', 'None'],
                                        'Pressure-treated skirt board')
        # Concrete floor slab (optional)
        self._est_pb_slab      = _combo(['Full concrete floor', 'Gravel floor', 'None'],
                                        'Gravel floor')
        self._est_pb_col_size_row  = _row('🪵  Column size:',    self._est_pb_col_size)
        self._est_pb_col_sp_row    = _row('↔️  Column spacing:', self._est_pb_col_sp)
        self._est_pb_col_embed_row = _row('⬇️  Embed depth:',    self._est_pb_col_embed)
        self._est_pb_col_ht_row    = _row('📏  Column height:',  self._est_pb_col_ht)
        self._est_pb_girt_sp_row   = _row('➖  Girt spacing:',   self._est_pb_girt_sp)
        self._est_pb_truss_sp_row  = _row('🔺  Truss spacing:',  self._est_pb_truss_sp)
        self._est_pb_purlin_sp_row = _row('➖  Purlin spacing:', self._est_pb_purlin_sp)
        self._est_pb_roof_row      = _row('🏠  Roof cladding:',  self._est_pb_roof_type)
        self._est_pb_siding_row    = _row('🧱  Wall cladding:',  self._est_pb_siding)
        self._est_pb_skirt_row     = _row('🔲  Perimeter:',      self._est_pb_skirt)
        self._est_pb_slab_row      = _row('🪨  Floor:',          self._est_pb_slab)
        for r in (self._est_pb_col_size_row, self._est_pb_col_sp_row,
                  self._est_pb_col_embed_row, self._est_pb_col_ht_row,
                  self._est_pb_girt_sp_row,   self._est_pb_truss_sp_row,
                  self._est_pb_purlin_sp_row, self._est_pb_roof_row,
                  self._est_pb_siding_row,    self._est_pb_skirt_row,
                  self._est_pb_slab_row):
            vl.addWidget(r)

        self._est_lbl_decking = _label('── 🪵  Decking / Subfloor ──')
        vl.addWidget(self._est_lbl_decking)
        self._est_deck_type  = _combo(['Deck boards','Plywood / OSB'], 'Deck boards')
        self._est_brd_width  = _dsb(5.5, 1, 12, 0.25, 2, '"')
        self._est_deck_type_row = _row('🪵  Surface type:', self._est_deck_type)
        self._est_brd_width_row = _row('📏  Board width:',  self._est_brd_width)
        vl.addWidget(self._est_deck_type_row)
        vl.addWidget(self._est_brd_width_row)

        self._est_lbl_wall_framing = _label('── 🧱  Wall / Rail Framing ──')
        vl.addWidget(self._est_lbl_wall_framing)
        self._est_surface_mode = _combo(['Walls','Rails'], 'Walls')
        self._est_stud_sp      = _combo(['16" o.c.','24" o.c.'], '16" o.c.')
        self._est_stud_sz      = _combo(['2x4','2x6'], '2x4')
        self._est_ceil_ht      = _dsb(8.0, 6, 20, 0.5, 1, ' ft')
        self._est_plates       = _combo(['Single (1)','Double (2)'], 'Double (2)')
        self._est_wall_mode_row  = _row('🔀  Mode:',          self._est_surface_mode)
        self._est_stud_sp_row   = _row('↔️  Stud spacing:',  self._est_stud_sp)
        self._est_stud_sz_row   = _row('🪵  Stud size:',     self._est_stud_sz)
        self._est_ceil_ht_row   = _row('⬆️  Ceiling ht:',    self._est_ceil_ht)
        self._est_plates_row    = _row('📑  Top plates:',    self._est_plates)
        vl.addWidget(self._est_wall_mode_row)
        vl.addWidget(self._est_stud_sp_row)
        vl.addWidget(self._est_stud_sz_row)
        vl.addWidget(self._est_ceil_ht_row)
        vl.addWidget(self._est_plates_row)

        self._est_lbl_concrete = _label('── 🪨  Concrete & Footings ──')
        vl.addWidget(self._est_lbl_concrete)
        self._est_ftg_dia   = _combo(['8"','10"','12"','16"'], '12"')
        self._est_ftg_depth = _dsb(42, 12, 96, 6, 0, '"')
        self._est_ftg_dia_row   = _row('⭕  Footing dia:',   self._est_ftg_dia)
        self._est_ftg_depth_row = _row('⬇️  Footing depth:', self._est_ftg_depth)
        vl.addWidget(self._est_ftg_dia_row)
        vl.addWidget(self._est_ftg_depth_row)

        self._est_lbl_roof = _label('── 🏠  Roof Framing ──')
        vl.addWidget(self._est_lbl_roof)
        self._est_pitch     = _combo(['3/12','4/12','5/12','6/12','8/12','12/12'], '4/12')
        self._est_rafter_overhang = QSpinBox()
        self._est_rafter_overhang.setRange(12, 96)
        self._est_rafter_overhang.setValue(24)
        self._est_rafter_overhang.setSuffix('"')
        self._est_rafter_sp = _combo(['12" o.c.','16" o.c.','19.2" o.c.','24" o.c.'], '16" o.c.')
        self._est_pitch_row    = _row('📐  Roof pitch:',     self._est_pitch)
        self._est_overhang_row = _row('➡️  Eave overhang:',  self._est_rafter_overhang)
        self._est_rafter_row   = _row('🪵  Rafter spacing:', self._est_rafter_sp)
        vl.addWidget(self._est_pitch_row)
        vl.addWidget(self._est_overhang_row)
        vl.addWidget(self._est_rafter_row)

        vl.addWidget(_label('── 📘  Kentucky / IRC 2021 ──'))
        self._est_ky_snow  = _combo(['20 psf (central KY)','25 psf','30 psf'],
                                    '20 psf (central KY)')
        self._est_ky_soil  = _combo(['1500 psf (default)','2000 psf','3000 psf'],
                                    '1500 psf (default)')
        self._est_ky_frost = _combo(['24" (most of KY)','18"','30"'],
                                    '24" (most of KY)')
        vl.addWidget(_row('❄️  Ground snow:', self._est_ky_snow))
        vl.addWidget(_row('🌍  Soil bearing:', self._est_ky_soil))
        vl.addWidget(_row('❄️  Frost depth:',  self._est_ky_frost))

        vl.addWidget(_label('── ⚙️  General ──'))
        self._est_waste     = _dsb(10, 0, 50, 5, 0, '%')
        self._est_stock     = _combo(['8,10,12,16 ft','8,10,12,14,16 ft',
                                      '8,10,12,14,16,18,20 ft'],
                                     '8,10,12,16 ft')
        vl.addWidget(_row('♻️  Waste factor:',  self._est_waste))
        vl.addWidget(_row('📦  Stock lengths:', self._est_stock))

        vl.addWidget(_label('── ✅  Include (each trade is separate) ──'))
        self._est_chk_substructure  = _chk('🪵  Substructure (joists/posts)', True)
        self._est_chk_decking       = _chk('🪵  Decking / subfloor',        True)
        self._est_chk_walls         = _chk('🧱  Wall / rail framing',       True)
        self._est_chk_hardware      = _chk('🔩  Structural hardware',       True)
        self._est_chk_concrete      = _chk('🪨  Concrete & footings',       True)
        self._est_chk_drywall       = _chk('🧱  Drywall (hang/tape/mud)',   True)
        self._est_chk_insulation    = _chk('🧥  Insulation (walls + attic)', True)
        self._est_chk_flooring      = _chk('🪵  Flooring',                  True)
        self._est_chk_doors_windows = _chk('🚪  Doors & windows',           True)
        self._est_chk_siding        = _chk('🏠  Exterior siding',           True)
        self._est_chk_roof          = _chk('🔺  Roof framing',              False)
        self._est_chk_roofing       = _chk('🏠  Roofing materials',         False)
        self._est_chk_trim          = _chk('🖼️  Interior trim',             False)
        self._est_chk_finish        = _chk('🎨  Finish & paint',            False)
        self._est_chk_electrical    = _chk('⚡  Electrical rough-in',       False)
        self._est_chk_plumbing      = _chk('🚿  Plumbing rough-in',         False)
        self._est_chk_hvac          = _chk('❄️  HVAC rough-in',             False)
        for chk in (self._est_chk_substructure, self._est_chk_decking,
                    self._est_chk_walls, self._est_chk_hardware,
                    self._est_chk_concrete,
                    self._est_chk_drywall, self._est_chk_insulation,
                    self._est_chk_flooring, self._est_chk_doors_windows,
                    self._est_chk_siding, self._est_chk_roof,
                    self._est_chk_roofing, self._est_chk_trim,
                    self._est_chk_finish, self._est_chk_electrical,
                    self._est_chk_plumbing, self._est_chk_hvac):
            vl.addWidget(chk)

        self._est_lbl_mat_types = _label('── 🎨  Material Types ──')
        vl.addWidget(self._est_lbl_mat_types)
        self._est_flooring_type = _combo(['LVP', 'Tile', 'Carpet', 'Hardwood'], 'LVP')
        self._est_siding_type = _combo(['Vinyl', 'Hardie / fiber cement', 'Wood'], 'Vinyl')
        self._est_roofing_type = _combo(['Shingles', 'Metal'], 'Shingles')
        self._est_ceiling_insul = _combo(['R-30', 'R-38', 'R-49'], 'R-38')
        self._est_flooring_type_row  = _row('🪵  Flooring:',    self._est_flooring_type)
        self._est_siding_type_row    = _row('🏠  Siding:',      self._est_siding_type)
        self._est_roofing_type_row   = _row('🔺  Roofing:',     self._est_roofing_type)
        self._est_ceiling_insul_row  = _row('🧥  Ceiling insul:', self._est_ceiling_insul)
        vl.addWidget(self._est_flooring_type_row)
        vl.addWidget(self._est_siding_type_row)
        vl.addWidget(self._est_roofing_type_row)
        vl.addWidget(self._est_ceiling_insul_row)

        # ── Scope & calculate ─────────────────────────────────────────────────
        vl.addWidget(_label('── 🎯  Scope ──'))
        self._est_scope = _combo(['Full project','Selection only'], 'Full project')
        vl.addWidget(self._est_scope)

        calc_btn = QPushButton('🧮  Calculate Materials')
        calc_btn.setStyleSheet('font-weight: bold; padding: 6px;')
        calc_btn.clicked.connect(self._act_calculate_materials)
        vl.addWidget(calc_btn)

        code_btn = QPushButton('📘  Run Code Check  (KY / IRC 2021)')
        code_btn.setStyleSheet('font-weight: bold; padding: 6px; color: #7eb8f0;')
        code_btn.clicked.connect(self._act_run_code_check)
        vl.addWidget(code_btn)

        # ── Results ───────────────────────────────────────────────────────────
        vl.addWidget(_label('── 📋  Results ──'))
        cat_row = QWidget()
        cat_hl  = QHBoxLayout(cat_row)
        cat_hl.setContentsMargins(0, 0, 0, 0)
        cat_hl.addWidget(QLabel('Category:'))
        self._est_cat_combo = QComboBox()
        self._est_cat_combo.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        cat_hl.addWidget(self._est_cat_combo)
        vl.addWidget(cat_row)
        self._est_cat_combo.currentTextChanged.connect(self._est_filter_results)

        self._est_table = QTableWidget(0, 4)
        self._est_table.setHorizontalHeaderLabels(['Description', 'Qty', 'Unit', 'Notes'])
        self._est_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._est_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self._est_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self._est_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents)
        self._est_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._est_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._est_table.verticalHeader().hide()
        self._est_table.setMinimumHeight(180)
        vl.addWidget(self._est_table)

        # Export / copy buttons
        btn_row = QWidget()
        btn_hl  = QHBoxLayout(btn_row)
        btn_hl.setContentsMargins(0, 0, 0, 0)
        exp_btn  = QPushButton('📤  Export CSV')
        copy_btn = QPushButton('📋  Copy List')
        exp_btn.clicked.connect(self._est_export_csv)
        copy_btn.clicked.connect(self._est_copy_clipboard)
        btn_hl.addWidget(exp_btn)
        btn_hl.addWidget(copy_btn)
        vl.addWidget(btn_row)

        # ── Code compliance results ───────────────────────────────────────────
        vl.addWidget(_label('── ✅  Code Compliance (KY/IRC 2021) ──'))
        self._code_table = QTableWidget(0, 4)
        self._code_table.setHorizontalHeaderLabels(['Element', 'Required', 'Provided', 'Status'])
        self._code_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self._code_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self._code_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents)
        self._code_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents)
        self._code_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._code_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._code_table.verticalHeader().hide()
        self._code_table.setMinimumHeight(140)
        vl.addWidget(self._code_table)

        auto_draw_btn = QPushButton('✏️  Auto-Draw Missing Elements')
        auto_draw_btn.setStyleSheet('font-weight: bold; padding: 6px; color: #7dcc7d;')
        auto_draw_btn.clicked.connect(self._act_auto_draw_missing)
        vl.addWidget(auto_draw_btn)

        code_export_btn = QPushButton('📤  Export Code Report CSV')
        code_export_btn.clicked.connect(self._est_export_code_csv)
        vl.addWidget(code_export_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(root)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._estimator_dock   = dock
        self._estimator_report = None   # holds last MaterialReport
        self._code_report      = None   # holds last CodeReport
        self._est_on_type_changed(self._est_bldg_type.currentText())

    def _act_calculate_materials(self):
        """Build EstimatorSettings from dock widgets and run the estimator."""
        c = self._canvas

        stock_map = {
            '8,10,12,16 ft':          [8, 10, 12, 16],
            '8,10,12,14,16 ft':       [8, 10, 12, 14, 16],
            '8,10,12,14,16,18,20 ft': [8, 10, 12, 14, 16, 18, 20],
        }
        stud_sp_map = {'16" o.c.': 16, '24" o.c.': 24}
        ftg_dia_map = {'8"': 8, '10"': 10, '12"': 12, '16"': 16}
        pitch_map   = {'3/12': 3, '4/12': 4, '5/12': 5,
                       '6/12': 6, '8/12': 8, '12/12': 12}
        plates_map  = {'Single (1)': 1, 'Double (2)': 2}
        fdn_map     = {
            'Posts (4x4)':          ('posts', '4x4'),
            'Posts (6x6)':          ('posts', '6x6'),
            'Footer & CMU Block':   ('footer_block', '4x4'),
            'Concrete Pad (Slab)':  ('slab', '4x4'),
            'Poured Concrete Wall': ('concrete_wall', '4x4'),
        }
        fdn_type, post_sz = fdn_map.get(self._est_foundation.currentText(), ('posts', '4x4'))
        pb_cladding_map = {
            'Metal panels': 'metal', 'Board & batten': 'board_batten',
            'LP SmartSide': 'lp_smartside',
        }
        pb_skirt_map = {
            'Pressure-treated skirt board': 'pt_skirt',
            'Concrete grade beam': 'grade_beam', 'None': 'none',
        }
        pb_floor_map = {
            'Full concrete floor': 'concrete', 'Gravel floor': 'gravel', 'None': 'none',
        }
        btype_raw = self._est_bldg_type.currentText()
        btype_key = {'Building': 'building', 'Deck': 'deck',
                     'Pole Barn': 'pole_barn'}.get(btype_raw, 'building')
        pb_truss_map = {'4 ft': 4.0, '8 ft': 8.0, '10 ft': 10.0, '12 ft': 12.0}
        pb_girt_map  = {'24" o.c.': 24.0, '48" o.c.': 48.0, '60" o.c.': 60.0}
        pb_purlin_map = {'24" o.c.': 24.0, '36" o.c.': 36.0}

        settings = EstimatorSettings(
            building_sections   = self._est_get_sections(),
            door_count          = self._est_door_count.value(),
            window_count        = self._est_win_count.value(),
            foundation_type     = fdn_type,
            post_size           = post_sz,
            crawl_space_ht_in   = self._est_crawl_ht.value(),
            post_spacing_x_ft   = self._est_post_sx.value(),
            post_spacing_y_ft   = self._est_post_sy.value(),
            post_height_ft      = self._est_post_ht.value(),
            joist_size          = self._est_joist_sz.currentText(),
            decking_type        = ('plywood' if 'Plywood' in self._est_deck_type.currentText()
                                   else 'deck_board'),
            deck_board_width    = self._est_brd_width.value(),
            waste_pct           = self._est_waste.value(),
            surface_mode        = ('rails' if self._est_surface_mode.currentText() == 'Rails'
                                   else 'walls'),
            stud_spacing        = stud_sp_map.get(self._est_stud_sp.currentText(), 16),
            stud_size           = self._est_stud_sz.currentText(),
            plate_count         = plates_map.get(self._est_plates.currentText(), 2),
            ceiling_ht_ft       = self._est_ceil_ht.value(),
            roof_pitch          = pitch_map.get(self._est_pitch.currentText(), 4),
            rafter_spacing      = int(float(self._est_rafter_sp.currentText().split('"')[0])),
            rafter_overhang_ft  = self._est_rafter_overhang.value() / 12.0,
            footing_dia_in      = ftg_dia_map.get(self._est_ftg_dia.currentText(), 12),
            footing_depth_in    = int(self._est_ftg_depth.value()),
            include_substructure = self._est_chk_substructure.isChecked(),
            include_decking     = self._est_chk_decking.isChecked(),
            include_walls       = self._est_chk_walls.isChecked(),
            include_hardware    = self._est_chk_hardware.isChecked(),
            include_concrete    = self._est_chk_concrete.isChecked(),
            include_roof        = self._est_chk_roof.isChecked(),
            include_finish      = self._est_chk_finish.isChecked(),
            include_electrical  = self._est_chk_electrical.isChecked(),
            include_drywall     = self._est_chk_drywall.isChecked(),
            include_insulation  = self._est_chk_insulation.isChecked(),
            include_flooring    = self._est_chk_flooring.isChecked(),
            include_doors_windows = self._est_chk_doors_windows.isChecked(),
            include_siding      = self._est_chk_siding.isChecked(),
            include_roofing     = self._est_chk_roofing.isChecked(),
            include_trim        = self._est_chk_trim.isChecked(),
            include_plumbing    = self._est_chk_plumbing.isChecked(),
            include_hvac        = self._est_chk_hvac.isChecked(),
            flooring_type       = self._est_flooring_type.currentText().split()[0].lower(),
            siding_type         = ('hardie' if 'Hardie' in self._est_siding_type.currentText()
                                   else self._est_siding_type.currentText().lower()),
            roofing_type        = self._est_roofing_type.currentText().lower(),
            ceiling_insul_r     = int(self._est_ceiling_insul.currentText().replace('R-', '')),
            stock_lengths_ft    = stock_map.get(
                self._est_stock.currentText(), [8, 10, 12, 16]),
            building_type       = btype_key,
            pb_col_size         = self._est_pb_col_size.currentText(),
            pb_col_spacing_ft   = self._est_pb_col_sp.value(),
            pb_col_embed_ft     = self._est_pb_col_embed.value(),
            pb_col_height_ft    = self._est_pb_col_ht.value(),
            pb_girt_spacing_in  = pb_girt_map.get(self._est_pb_girt_sp.currentText(), 48.0),
            pb_truss_spacing_ft = pb_truss_map.get(self._est_pb_truss_sp.currentText(), 4.0),
            pb_purlin_spacing_in= pb_purlin_map.get(self._est_pb_purlin_sp.currentText(), 24.0),
            pb_roof_cladding    = pb_cladding_map.get(self._est_pb_roof_type.currentText(), 'metal'),
            pb_wall_cladding    = pb_cladding_map.get(self._est_pb_siding.currentText(), 'metal'),
            pb_skirt_type       = pb_skirt_map.get(self._est_pb_skirt.currentText(), 'pt_skirt'),
            pb_floor_type       = pb_floor_map.get(self._est_pb_slab.currentText(), 'gravel'),
        )

        # Collect scene items — auto-detect sections from drawn rooms first
        scene = c.scene()
        from items import GroupItem, RoomItem, JoistFillItem, WallItem, LineItem, ShapeItem

        def _cad_items(source):
            """All CAD items from source, including group children (skip group containers)."""
            result = []
            for i in source:
                if not hasattr(i, 'to_dict'):
                    continue
                if isinstance(i, GroupItem):
                    continue
                result.append(i)
            return result

        if self._est_scope.currentText() == 'Selection only':
            raw_items = _cad_items(scene.selectedItems())
        else:
            raw_items = _cad_items(scene.items())

        item_dicts = [i.to_dict() for i in raw_items]

        # If drawn rooms/joistfills exist, sync the section widgets so the panel
        # reflects reality, then rebuild settings from the updated rows.
        drawn_rooms  = [d for d in item_dicts if d.get('type') == 'room']
        drawn_joists = [d for d in item_dicts if d.get('type') == 'joist_fill']
        drawn_walls_i = [i for i in raw_items if isinstance(i, WallItem)]
        drawn_lines_i = [i for i in raw_items if isinstance(i, LineItem)]

        detected = []
        if drawn_rooms:
            detected = drawn_rooms
        elif drawn_joists:
            detected = [{'label': d.get('label', '') or f'Section {idx+1}',
                         'w': d['w'], 'h': d['h']}
                        for idx, d in enumerate(drawn_joists)]
        elif drawn_walls_i:
            wds = [i.to_dict() for i in drawn_walls_i]
            xs = [d['x1'] for d in wds] + [d['x2'] for d in wds]
            ys = [d['y1'] for d in wds] + [d['y2'] for d in wds]
            detected = [{'label': 'Building',
                         'w': max(xs) - min(xs), 'h': max(ys) - min(ys)}]
        elif drawn_lines_i:
            lds = [i.to_dict() for i in drawn_lines_i]
            xs = [d['x1'] for d in lds] + [d['x2'] for d in lds]
            ys = [d['y1'] for d in lds] + [d['y2'] for d in lds]
            detected = [{'label': 'Building',
                         'w': max(xs) - min(xs), 'h': max(ys) - min(ys)}]
        else:
            # Shape items — one section per shape
            drawn_shapes_i = [i for i in raw_items if isinstance(i, ShapeItem)]
            if drawn_shapes_i:
                detected = [{'label': f'Section {idx+1}',
                             'w': i.w, 'h': i.h}
                            for idx, i in enumerate(drawn_shapes_i)]
            else:
                # Ultimate fallback: scene bounding box
                br = scene.itemsBoundingRect()
                if br.width() > 1 and br.height() > 1:
                    detected = [{'label': 'Building',
                                 'w': br.width(), 'h': br.height()}]

        if detected:
            for rd in list(self._est_sections_rows):
                rd['widget'].setParent(None)
                rd['widget'].deleteLater()
            self._est_sections_rows.clear()
            for rd in detected:
                name = rd.get('label') or 'Section'
                self._est_add_section_row(
                    name,
                    round(rd.get('w', 240) / 12, 1),
                    round(rd.get('h', 288) / 12, 1))
            settings = self._build_est_settings()

        report = MaterialEstimator().run(item_dicts, settings)
        self._estimator_report = report

        # Populate category drop-down
        cats = ['All'] + report.categories()
        self._est_cat_combo.blockSignals(True)
        self._est_cat_combo.clear()
        self._est_cat_combo.addItems(cats)
        self._est_cat_combo.blockSignals(False)
        self._est_cat_combo.setCurrentText('All')

        self._est_populate_table(report.filtered())

    def _est_filter_results(self, category: str):
        if self._estimator_report is None:
            return
        self._est_populate_table(
            self._estimator_report.filtered(category))

    def _est_populate_table(self, lines):
        from PyQt6.QtGui import QFont, QColor
        tbl = self._est_table
        tbl.setRowCount(0)
        current_cat = None
        header_bg   = QColor('#1a1a1a')
        header_fg   = QColor('#ff8833')
        bold        = QFont()
        bold.setBold(True)
        for ln in lines:
            # ── Category header row ─────────────────────────────────────────
            if ln.category != current_cat:
                current_cat = ln.category
                hrow = tbl.rowCount()
                tbl.insertRow(hrow)
                tbl.setRowHeight(hrow, 22)
                label = QTableWidgetItem(f'  {current_cat}')
                label.setFont(bold)
                label.setForeground(header_fg)
                label.setBackground(header_bg)
                label.setFlags(Qt.ItemFlag.ItemIsEnabled)   # not selectable
                tbl.setItem(hrow, 0, label)
                for col in range(1, 4):
                    filler = QTableWidgetItem('')
                    filler.setBackground(header_bg)
                    filler.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    tbl.setItem(hrow, col, filler)
                tbl.setSpan(hrow, 0, 1, 4)
            # ── Data row ────────────────────────────────────────────────────
            row = tbl.rowCount()
            tbl.insertRow(row)
            tbl.setRowHeight(row, 20)
            tbl.setItem(row, 0, QTableWidgetItem(ln.description))
            qty_item = QTableWidgetItem(ln.qty_str())
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight |
                                      Qt.AlignmentFlag.AlignVCenter)
            tbl.setItem(row, 1, qty_item)
            tbl.setItem(row, 2, QTableWidgetItem(ln.unit))
            tbl.setItem(row, 3, QTableWidgetItem(ln.notes))

    def _est_export_csv(self):
        if not self._estimator_report:
            QMessageBox.information(self, 'Estimator', 'Run Calculate first.')
            return
        path, _ = QFileDialog.getSaveFileName(
            self, 'Export Material List', '', 'CSV Files (*.csv);;All Files (*)')
        if not path:
            return
        if not path.lower().endswith('.csv'):
            path += '.csv'
        with open(path, 'w', newline='', encoding='utf-8') as f:
            f.write(self._estimator_report.to_csv())
        QMessageBox.information(self, 'Estimator', f'Saved: {path}')

    def _est_copy_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        if not self._estimator_report:
            QMessageBox.information(self, 'Estimator', 'Run Calculate first.')
            return
        QApplication.clipboard().setText(
            self._estimator_report.to_plain_text())

    # ── Building type toggle ──────────────────────────────────────────────────

    def _est_on_type_changed(self, btype: str):
        """Show/hide settings rows based on Building / Deck / Pole Barn."""
        is_bldg = (btype == 'Building')
        is_deck = (btype == 'Deck')
        is_pb   = (btype == 'Pole Barn')

        # ── Sections header label ────────────────────────────────────────
        self._est_door_row.setVisible(is_bldg)
        self._est_win_row.setVisible(is_bldg)

        # ── Substructure ────────────────────────────────────────────────
        # Pole barn has its own column system — hide standard substructure
        self._est_lbl_substructure.setVisible(not is_pb)
        self._est_fdn_row.setVisible(not is_pb)
        self._est_post_sx_row.setVisible(not is_pb)
        self._est_post_sy_row.setVisible(not is_pb)
        self._est_post_ht_row.setVisible(not is_pb)
        self._est_crawl_row.setVisible(is_bldg)   # crawl space: building only
        self._est_joist_sz_row.setVisible(not is_pb)

        # Foundation options vary by type
        fdn_options = {
            'Building': ['Posts (4x4)', 'Posts (6x6)', 'Footer & CMU Block',
                         'Concrete Pad (Slab)', 'Poured Concrete Wall'],
            'Deck':     ['Posts (4x4)', 'Posts (6x6)', 'Concrete Pad (Slab)'],
            'Pole Barn': [],
        }
        self._est_foundation.blockSignals(True)
        cur = self._est_foundation.currentText()
        self._est_foundation.clear()
        opts = fdn_options.get(btype, [])
        if opts:
            self._est_foundation.addItems(opts)
            if cur in opts:
                self._est_foundation.setCurrentText(cur)
        self._est_foundation.blockSignals(False)

        # ── Pole Barn fields ─────────────────────────────────────────────
        self._est_lbl_pb.setVisible(is_pb)
        for r in (self._est_pb_col_size_row, self._est_pb_col_sp_row,
                  self._est_pb_col_embed_row, self._est_pb_col_ht_row,
                  self._est_pb_girt_sp_row,   self._est_pb_truss_sp_row,
                  self._est_pb_purlin_sp_row, self._est_pb_roof_row,
                  self._est_pb_siding_row,    self._est_pb_skirt_row,
                  self._est_pb_slab_row):
            r.setVisible(is_pb)

        # ── Decking / Subfloor ───────────────────────────────────────────
        self._est_lbl_decking.setVisible(not is_pb)
        self._est_deck_type_row.setVisible(not is_pb)
        self._est_brd_width_row.setVisible(not is_pb)

        # ── Wall / Rail Framing ──────────────────────────────────────────
        self._est_lbl_wall_framing.setVisible(not is_pb)
        self._est_wall_mode_row.setVisible(not is_pb)
        if is_deck:
            self._est_surface_mode.setCurrentText('Rails')
        elif is_bldg:
            self._est_surface_mode.setCurrentText('Walls')
        # Stud/ceiling settings: building only
        self._est_stud_sp_row.setVisible(is_bldg)
        self._est_stud_sz_row.setVisible(is_bldg)
        self._est_ceil_ht_row.setVisible(is_bldg)
        self._est_plates_row.setVisible(is_bldg)

        # ── Concrete & Footings ──────────────────────────────────────────
        # Pole barn uses embedded columns, no separate footing calc needed
        self._est_lbl_concrete.setVisible(not is_pb)
        self._est_ftg_dia_row.setVisible(not is_pb)
        self._est_ftg_depth_row.setVisible(not is_pb)

        # ── Roof Framing ─────────────────────────────────────────────────
        # Pole barn uses purlins/trusses — hide standard rafter spacing
        self._est_lbl_roof.setVisible(not is_pb)
        self._est_pitch_row.setVisible(not is_pb)
        self._est_overhang_row.setVisible(not is_pb)
        self._est_rafter_row.setVisible(not is_pb)

        # ── Material Types ───────────────────────────────────────────────
        # Only relevant for residential building type
        for w in (self._est_lbl_mat_types, self._est_flooring_type_row,
                  self._est_siding_type_row, self._est_roofing_type_row,
                  self._est_ceiling_insul_row):
            w.setVisible(is_bldg)

        # ── Include checkboxes ────────────────────────────────────────────
        # building-only interior trades
        interior_checks = [
            self._est_chk_drywall, self._est_chk_insulation,
            self._est_chk_plumbing, self._est_chk_hvac,
            self._est_chk_electrical, self._est_chk_flooring,
            self._est_chk_siding, self._est_chk_trim,
        ]
        for chk in interior_checks:
            if is_bldg:
                chk.setEnabled(True)
            else:
                chk.setChecked(False)
                chk.setEnabled(False)

    # ── Building section helpers ──────────────────────────────────────────────

    def _est_add_section_row(self, label: str = '', w: float = 20.0, l: float = 30.0):
        """Append one section row (label + W + L + remove button) to the dynamic list."""
        row_widget = QWidget()
        hl = QHBoxLayout(row_widget)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(3)

        lbl_edit = QLineEdit(label or f'Section {len(self._est_sections_rows) + 1}')
        lbl_edit.setPlaceholderText('Name')
        lbl_edit.setMaximumWidth(80)

        w_spin = QDoubleSpinBox()
        w_spin.setRange(4, 999); w_spin.setSingleStep(1)
        w_spin.setDecimals(0);   w_spin.setSuffix(' ft')
        w_spin.setValue(w);      w_spin.setMaximumWidth(72)

        l_spin = QDoubleSpinBox()
        l_spin.setRange(4, 999); l_spin.setSingleStep(1)
        l_spin.setDecimals(0);   l_spin.setSuffix(' ft')
        l_spin.setValue(l);      l_spin.setMaximumWidth(72)

        rm_btn = QPushButton('✕')
        rm_btn.setMaximumWidth(22)
        rm_btn.setToolTip('Remove section')

        hl.addWidget(lbl_edit)
        hl.addWidget(QLabel('W'))
        hl.addWidget(w_spin)
        hl.addWidget(QLabel('L'))
        hl.addWidget(l_spin)
        hl.addWidget(rm_btn)

        row_data = {'label': lbl_edit, 'w': w_spin, 'l': l_spin, 'widget': row_widget}
        self._est_sections_rows.append(row_data)
        rm_btn.clicked.connect(lambda: self._est_remove_section_row(row_data))

        self._est_sections_vl.addWidget(row_widget)

    def _est_remove_section_row(self, row_data: dict):
        """Remove a section row; always keep at least one."""
        if len(self._est_sections_rows) <= 1:
            return
        self._est_sections_rows.remove(row_data)
        row_data['widget'].setParent(None)
        row_data['widget'].deleteLater()

    def _est_detect_sections(self):
        """Read geometry from the current drawing and repopulate section rows."""
        scene = self._canvas.scene()
        from items import (GroupItem, RoomItem, JoistFillItem,
                           WallItem, LineItem, ShapeItem)

        # All CAD items — include group children, skip group containers
        all_items = [i for i in scene.items()
                     if hasattr(i, 'to_dict') and not isinstance(i, GroupItem)]

        room_dicts = []

        # ── 1. RoomItem — best source (has explicit w/h and label) ────────
        rooms = [i for i in all_items if isinstance(i, RoomItem)]
        if rooms:
            room_dicts = [i.to_dict() for i in rooms]

        # ── 2. JoistFill — each area = one section ────────────────────────
        if not room_dicts:
            joists = [i for i in all_items if isinstance(i, JoistFillItem)]
            if joists:
                room_dicts = [
                    {'label': getattr(i, 'label', '') or f'Section {idx+1}',
                     'w': i.w, 'h': i.h}
                    for idx, i in enumerate(joists)
                ]

        # ── 3-5. Bounding-box fallbacks (Wall → Line → Shape) ─────────────
        def _bbox_from(items_list, key_x1, key_y1, key_x2, key_y2):
            dcts = [i.to_dict() for i in items_list]
            xs = [d[key_x1] for d in dcts] + [d[key_x2] for d in dcts]
            ys = [d[key_y1] for d in dcts] + [d[key_y2] for d in dcts]
            return max(xs) - min(xs), max(ys) - min(ys)

        if not room_dicts:
            walls = [i for i in all_items if isinstance(i, WallItem)]
            if walls:
                w, h = _bbox_from(walls, 'x1', 'y1', 'x2', 'y2')
                room_dicts = [{'label': 'Building', 'w': w, 'h': h}]

        if not room_dicts:
            lines = [i for i in all_items if isinstance(i, LineItem)]
            if lines:
                w, h = _bbox_from(lines, 'x1', 'y1', 'x2', 'y2')
                room_dicts = [{'label': 'Building', 'w': w, 'h': h}]

        if not room_dicts:
            shapes = [i for i in all_items if isinstance(i, ShapeItem)]
            if shapes:
                room_dicts = [
                    {'label': f'Section {idx+1}',
                     'w': i.w, 'h': i.h}
                    for idx, i in enumerate(shapes)
                ]

        # ── 6. Ultimate fallback — bounding box of everything visible ──────
        if not room_dicts and all_items:
            br = scene.itemsBoundingRect()
            if br.width() > 1 and br.height() > 1:
                room_dicts = [{'label': 'Building',
                               'w': br.width(), 'h': br.height()}]

        if not room_dicts:
            QMessageBox.information(
                self, 'Detect Sections',
                'The drawing appears to be empty.\n\n'
                'Draw a rectangle with the Room tool (shortcut M),\n'
                'then click Detect again.')
            return

        # Remove existing rows and repopulate
        for rd in list(self._est_sections_rows):
            rd['widget'].setParent(None)
            rd['widget'].deleteLater()
        self._est_sections_rows.clear()

        for rd in room_dicts:
            name = rd.get('label') or 'Section'
            w_ft = round(rd.get('w', 240) / 12, 1)
            l_ft = round(rd.get('h', 288) / 12, 1)
            self._est_add_section_row(name, w_ft, l_ft)

    def _est_get_sections(self) -> list[dict]:
        """Return section list from current UI rows."""
        return [
            {'label': r['label'].text() or f'Section {i+1}',
             'width_ft':  r['w'].value(),
             'length_ft': r['l'].value()}
            for i, r in enumerate(self._est_sections_rows)
        ]

    # ── Code Compliance actions ───────────────────────────────────────────────

    def _build_ky_settings(self) -> dict:
        """Read KY regional settings from dock widgets."""
        snow_map  = {'20 psf (central KY)': 20, '25 psf': 25, '30 psf': 30}
        soil_map  = {'1500 psf (default)': 1500, '2000 psf': 2000, '3000 psf': 3000}
        frost_map = {'24" (most of KY)': 24, '18"': 18, '30"': 30}
        from code_tables import KY_DEFAULTS
        ky = KY_DEFAULTS.copy()
        ky['ground_snow_psf']  = snow_map.get(self._est_ky_snow.currentText(),  20)
        ky['soil_bearing_psf'] = soil_map.get(self._est_ky_soil.currentText(), 1500)
        ky['frost_depth_in']   = frost_map.get(self._est_ky_frost.currentText(), 24)
        return ky

    def _collect_item_dicts(self) -> list[dict]:
        """Return serialised scene items honoring current scope selection."""
        c = self._canvas
        scene = c.scene()
        from items import GroupItem
        if self._est_scope.currentText() == 'Selection only':
            raw = [i for i in scene.selectedItems() if hasattr(i, 'to_dict')]
        else:
            raw = [i for i in scene.items() if hasattr(i, 'to_dict')]
        return [i.to_dict() for i in raw
                if not isinstance(i.parentItem(), GroupItem)]

    def _build_est_settings(self) -> 'EstimatorSettings':
        """Build an EstimatorSettings from current dock values."""
        stock_map   = {
            '8,10,12,16 ft':          [8, 10, 12, 16],
            '8,10,12,14,16 ft':       [8, 10, 12, 14, 16],
            '8,10,12,14,16,18,20 ft': [8, 10, 12, 14, 16, 18, 20],
        }
        stud_sp_map = {'16" o.c.': 16, '24" o.c.': 24}
        ftg_dia_map = {'8"': 8, '10"': 10, '12"': 12, '16"': 16}
        pitch_map   = {'3/12': 3, '4/12': 4, '5/12': 5,
                       '6/12': 6, '8/12': 8, '12/12': 12}
        plates_map  = {'Single (1)': 1, 'Double (2)': 2}
        fdn_map     = {
            'Posts (4x4)':          ('posts', '4x4'),
            'Posts (6x6)':          ('posts', '6x6'),
            'Footer & CMU Block':   ('footer_block', '4x4'),
            'Concrete Pad (Slab)':  ('slab', '4x4'),
            'Poured Concrete Wall': ('concrete_wall', '4x4'),
        }
        pb_cladding_map = {
            'Metal panels': 'metal', 'Board & batten': 'board_batten',
            'LP SmartSide': 'lp_smartside',
        }
        pb_skirt_map = {
            'Pressure-treated skirt board': 'pt_skirt',
            'Concrete grade beam': 'grade_beam', 'None': 'none',
        }
        pb_floor_map = {
            'Full concrete floor': 'concrete', 'Gravel floor': 'gravel', 'None': 'none',
        }
        btype_raw = self._est_bldg_type.currentText()
        btype_key = {'Building': 'building', 'Deck': 'deck',
                     'Pole Barn': 'pole_barn'}.get(btype_raw, 'building')
        pb_truss_map = {'4 ft': 4.0, '8 ft': 8.0, '10 ft': 10.0, '12 ft': 12.0}
        pb_girt_map  = {'24" o.c.': 24.0, '48" o.c.': 48.0, '60" o.c.': 60.0}
        pb_purlin_map = {'24" o.c.': 24.0, '36" o.c.': 36.0}
        return EstimatorSettings(
            post_spacing_x_ft  = self._est_post_sx.value(),
            post_spacing_y_ft  = self._est_post_sy.value(),
            post_height_ft     = self._est_post_ht.value(),
            joist_size         = self._est_joist_sz.currentText(),
            decking_type       = ('plywood' if 'Plywood' in self._est_deck_type.currentText()
                                  else 'deck_board'),
            deck_board_width   = self._est_brd_width.value(),
            waste_pct          = self._est_waste.value(),
            surface_mode       = ('rails' if self._est_surface_mode.currentText() == 'Rails'
                                  else 'walls'),
            stud_spacing       = stud_sp_map.get(self._est_stud_sp.currentText(), 16),
            stud_size          = self._est_stud_sz.currentText(),
            plate_count        = plates_map.get(self._est_plates.currentText(), 2),
            ceiling_ht_ft      = self._est_ceil_ht.value(),
            roof_pitch         = pitch_map.get(self._est_pitch.currentText(), 4),
            rafter_spacing     = int(float(self._est_rafter_sp.currentText().split('"')[0])),
            rafter_overhang_ft = self._est_rafter_overhang.value() / 12.0,
            footing_dia_in     = ftg_dia_map.get(self._est_ftg_dia.currentText(), 12),
            footing_depth_in   = int(self._est_ftg_depth.value()),
            building_sections  = self._est_get_sections(),
            door_count         = self._est_door_count.value(),
            window_count       = self._est_win_count.value(),
            foundation_type    = fdn_map.get(self._est_foundation.currentText(), ('posts','4x4'))[0],
            post_size          = fdn_map.get(self._est_foundation.currentText(), ('posts','4x4'))[1],
            crawl_space_ht_in  = self._est_crawl_ht.value(),
            building_type      = btype_key,
            pb_col_size        = self._est_pb_col_size.currentText(),
            pb_col_spacing_ft  = self._est_pb_col_sp.value(),
            pb_col_embed_ft    = self._est_pb_col_embed.value(),
            pb_col_height_ft   = self._est_pb_col_ht.value(),
            pb_girt_spacing_in = pb_girt_map.get(self._est_pb_girt_sp.currentText(), 48.0),
            pb_truss_spacing_ft= pb_truss_map.get(self._est_pb_truss_sp.currentText(), 4.0),
            pb_purlin_spacing_in=pb_purlin_map.get(self._est_pb_purlin_sp.currentText(), 24.0),
            pb_roof_cladding   = pb_cladding_map.get(self._est_pb_roof_type.currentText(), 'metal'),
            pb_wall_cladding   = pb_cladding_map.get(self._est_pb_siding.currentText(), 'metal'),
            pb_skirt_type      = pb_skirt_map.get(self._est_pb_skirt.currentText(), 'pt_skirt'),
            pb_floor_type      = pb_floor_map.get(self._est_pb_slab.currentText(), 'gravel'),
            include_substructure = self._est_chk_substructure.isChecked(),
            include_decking    = self._est_chk_decking.isChecked(),
            include_walls      = self._est_chk_walls.isChecked(),
            include_hardware   = self._est_chk_hardware.isChecked(),
            include_concrete   = self._est_chk_concrete.isChecked(),
            include_roof       = self._est_chk_roof.isChecked(),
            include_finish     = self._est_chk_finish.isChecked(),
            include_electrical = self._est_chk_electrical.isChecked(),
            include_drywall    = self._est_chk_drywall.isChecked(),
            include_insulation = self._est_chk_insulation.isChecked(),
            include_flooring   = self._est_chk_flooring.isChecked(),
            include_doors_windows = self._est_chk_doors_windows.isChecked(),
            include_siding     = self._est_chk_siding.isChecked(),
            include_roofing    = self._est_chk_roofing.isChecked(),
            include_trim       = self._est_chk_trim.isChecked(),
            include_plumbing   = self._est_chk_plumbing.isChecked(),
            include_hvac       = self._est_chk_hvac.isChecked(),
            flooring_type      = self._est_flooring_type.currentText().split()[0].lower(),
            siding_type        = ('hardie' if 'Hardie' in self._est_siding_type.currentText()
                                  else self._est_siding_type.currentText().lower()),
            roofing_type       = self._est_roofing_type.currentText().lower(),
            ceiling_insul_r    = int(self._est_ceiling_insul.currentText().replace('R-', '')),
            stock_lengths_ft   = stock_map.get(self._est_stock.currentText(), [8, 10, 12, 16]),
        )

    def _act_run_code_check(self):
        """Run CodeChecker on current scene and populate compliance table."""
        from PyQt6.QtGui import QColor
        item_dicts = self._collect_item_dicts()
        settings   = self._build_est_settings()
        ky         = self._build_ky_settings()

        report = CodeChecker().run(item_dicts, settings, ky)
        self._code_report = report

        tbl = self._code_table
        tbl.setRowCount(0)

        sev_colors = {
            'OK':    QColor('#1a3a1a'),
            'WARN':  QColor('#3a3210'),
            'ERROR': QColor('#3a1518'),
        }

        for issue in report.issues:
            row = tbl.rowCount()
            tbl.insertRow(row)
            tbl.setRowHeight(row, 20)
            tbl.setItem(row, 0, QTableWidgetItem(f'{issue.element} — {issue.location}'))
            tbl.setItem(row, 1, QTableWidgetItem(issue.required))
            tbl.setItem(row, 2, QTableWidgetItem(issue.provided))
            status_item = QTableWidgetItem(issue.severity)
            bg = sev_colors.get(issue.severity, QColor('#1a1a1a'))
            status_item.setBackground(bg)
            tbl.setItem(row, 3, status_item)

        errors   = len(report.errors())
        warnings = len(report.warnings())
        ok_count = len(report.ok_items())
        QMessageBox.information(
            self, 'Code Check Complete (KY / IRC 2021)',
            f'{errors} ERROR(s)   {warnings} WARNING(s)   {ok_count} PASSING\n\n'
            f'Results shown in the Code Compliance table below.\n'
            f'Click "Auto-Draw Missing Elements" to fix auto-fixable issues.'
        )

    def _est_export_code_csv(self):
        """Export the last code compliance report to a CSV file."""
        if not self._code_report:
            QMessageBox.information(self, 'Code Check', 'Run Code Check first.')
            return
        path, _ = QFileDialog.getSaveFileName(
            self, 'Export Code Report', '', 'CSV Files (*.csv);;All Files (*)')
        if not path:
            return
        if not path.lower().endswith('.csv'):
            path += '.csv'
        with open(path, 'w', newline='', encoding='utf-8') as f:
            f.write(self._code_report.to_csv())
        QMessageBox.information(self, 'Code Check', f'Saved: {path}')

    def _act_auto_draw_missing(self):
        """Auto-draw all auto_fixable issues from the last code report."""
        if not self._code_report:
            QMessageBox.information(self, 'Auto-Draw', 'Run Code Check first.')
            return

        fixable = [i for i in self._code_report.issues if i.auto_fixable]
        if not fixable:
            QMessageBox.information(self, 'Auto-Draw',
                                    'No auto-fixable issues found.\n'
                                    'All items either pass or require manual upgrade.')
            return

        from auto_draw import AutoDrawEngine
        item_dicts = self._collect_item_dicts()
        settings   = self._build_est_settings()
        drawn      = AutoDrawEngine().run(self._canvas, self._code_report, settings)

        QMessageBox.information(
            self, 'Auto-Draw Complete',
            f'{drawn} element(s) added to the drawing.\n'
            f'Use Ctrl+Z to undo all auto-drawn items at once.'
        )
        # Re-run code check to refresh compliance table
        self._act_run_code_check()

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
        from fixtures import FixtureItem as _FixItem
        self._props_updating = True
        try:
            if not items:
                self._prop_info.setText('No selection')
                self._prop_pos_frame.setVisible(False)
                self._prop_size_frame.setVisible(False)
                self._prop_text_frame.setVisible(False)
                self._prop_line_frame.setVisible(False)
                self._prop_rotation_frame.setVisible(False)
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
                elif isinstance(item, _FixItem):
                    self._prop_w.setValue(item._w)
                    self._prop_h.setValue(item._h)
                    self._prop_size_frame.setVisible(True)
                else:
                    self._prop_size_frame.setVisible(False)

                # Rotation
                import math as _math
                from items import DoorItem as _DoorItem, WindowItem as _WinItem
                if isinstance(item, (_DoorItem, _FixItem)):
                    self._prop_rotation.setValue(item.rotation())
                    self._prop_rotation_frame.setVisible(True)
                elif isinstance(item, _WinItem):
                    angle = _math.degrees(_math.atan2(item.dy, item.dx))
                    self._prop_rotation.setValue(round(angle, 1))
                    self._prop_rotation_frame.setVisible(True)
                else:
                    self._prop_rotation_frame.setVisible(False)

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
                self._prop_rotation_frame.setVisible(False)

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
        from items    import RoomItem, ShapeItem
        from fixtures import FixtureItem as _FixItem
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
        elif isinstance(item, _FixItem):
            ow, oh = item._w, item._h
            if ow != nw or oh != nh:
                def _a(item=item, nw=nw, nh=nh):
                    item.prepareGeometryChange()
                    item._w = nw; item._h = nh
                    item._update_transform_origin()
                    item.update()
                def _r(item=item, ow=ow, oh=oh):
                    item.prepareGeometryChange()
                    item._w = ow; item._h = oh
                    item._update_transform_origin()
                    item.update()
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

    def _prop_commit_rotation(self):
        if self._props_updating:
            return
        import math as _math
        from items    import DoorItem as _DoorItem, WindowItem as _WinItem
        from fixtures import FixtureItem as _FixItem
        items = self._canvas.scene().selectedItems()
        if len(items) != 1:
            return
        item  = items[0]
        angle = self._prop_rotation.value()
        if isinstance(item, (_DoorItem, _FixItem)):
            old = item.rotation()
            if old != angle:
                def _a(it=item, a=angle): it.setRotation(a)
                def _r(it=item, a=old):   it.setRotation(a)
                _a()
                self._canvas._undo_stack.push(_PropCmd('Rotate', _a, _r))
        elif isinstance(item, _WinItem):
            old_dx, old_dy = item.dx, item.dy
            L = _math.hypot(old_dx, old_dy)
            if L < 0.1:
                return
            new_dx = L * _math.cos(_math.radians(angle))
            new_dy = L * _math.sin(_math.radians(angle))
            if (old_dx, old_dy) != (new_dx, new_dy):
                def _a(it=item, dx=new_dx, dy=new_dy):
                    it.prepareGeometryChange(); it.dx = dx; it.dy = dy; it.update()
                def _r(it=item, dx=old_dx, dy=old_dy):
                    it.prepareGeometryChange(); it.dx = dx; it.dy = dy; it.update()
                _a()
                self._canvas._undo_stack.push(_PropCmd('Rotate', _a, _r))

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
            stk = self._canvas._undo_stack
            stk.beginMacro('Style change')
            for s in shapes:
                old_fill   = s.fill
                old_border = s.border
                new_fill   = fill_btn._hex   if fill_btn   else s.fill
                new_border = border_btn._hex if border_btn else s.border
                def _a(it=s, f=new_fill, b=new_border):
                    it.fill = f; it.border = b; it.update()
                def _r(it=s, f=old_fill, b=old_border):
                    it.fill = f; it.border = b; it.update()
                _a()
                stk.push(_PropCmd('Style', _a, _r))
            for li in lines_:
                old_c = li.line_color
                new_c = line_btn._hex if line_btn else li.line_color
                def _a(it=li, c=new_c):
                    it.line_color = c; it._apply_pen()
                def _r(it=li, c=old_c):
                    it.line_color = c; it._apply_pen()
                _a()
                stk.push(_PropCmd('Style', _a, _r))
            for t in texts:
                old_c = t.color
                new_c = text_btn._hex if text_btn else t.color
                def _a(it=t, c=new_c):
                    it.color = c; it.update()
                def _r(it=t, c=old_c):
                    it.color = c; it.update()
                _a()
                stk.push(_PropCmd('Style', _a, _r))
            stk.endMacro()
    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._scale_lbl = QLabel("Scale: 1/4\" = 1'")
        self._scale_lbl.setStyleSheet('color:#888;font-size:8pt;margin-right:10px;background:transparent;')
        self._status.addPermanentWidget(self._scale_lbl)
        self._status.showMessage(_HINT)

    # ── Tool switching ────────────────────────────────────────────────────────

    def _set_tool(self, tool: str):
        self._canvas.set_tool(tool)
        btn = self._tool_btns.get(tool)
        if btn:
            btn.setChecked(True)
        # Deselect fixture tiles when switching to any non-fixture tool
        if tool != TOOL_FIXTURE and hasattr(self, '_fixture_panel'):
            self._fixture_panel.deselect_all()

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
            menu.addAction(
                'Toggle &Grid',
                lambda: self._canvas.toggle_grid(not self._canvas._show_grid))

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

    def _page_source_rect(self) -> QRectF:
        """Scene rectangle that maps 1:1 onto the chosen paper size."""
        c = self._canvas
        return QRectF(0, 0, c._paper_phys_w * c.scale_ratio,
                      c._paper_phys_h * c.scale_ratio)

    def _render_page(self, painter: QPainter, target: QRectF):
        """Draw the page area in print colours (black linework on white)."""
        from items import set_print_mode
        painter.fillRect(target, QColor('#ffffff'))
        set_print_mode(True)
        try:
            self._canvas.scene().render(painter, target, self._page_source_rect())
        finally:
            set_print_mode(False)

    def _configure_printer(self, printer):
        c = self._canvas
        printer.setPageSize(
            QPageSize(QSizeF(c._paper_phys_w * 25.4, c._paper_phys_h * 25.4),
                      QPageSize.Unit.Millimeter))
        printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
        printer.setPageOrientation(
            QPageLayout.Orientation.Landscape
            if c._paper_phys_w > c._paper_phys_h
            else QPageLayout.Orientation.Portrait)

    def _paint_printer(self, printer):
        painter = QPainter(printer)
        try:
            self._render_page(painter, QRectF(painter.viewport()))
        finally:
            painter.end()

    def _act_print(self):
        """Print the current page (to-scale, black on white)."""
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self._configure_printer(printer)
        dlg = QPrintDialog(printer, self)
        dlg.setWindowTitle('Print Drawing')
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._paint_printer(printer)

    def _act_print_preview(self):
        from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self._configure_printer(printer)
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle('Print Preview')
        preview.paintRequested.connect(self._paint_printer)
        preview.exec()

    def _act_export_pdf(self):
        """Render the drawing page to a PDF file (black linework on white)."""
        path, _ = QFileDialog.getSaveFileName(
            self, 'Export PDF', '', 'PDF Files (*.pdf);;All Files (*)')
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'

        canvas  = self._canvas
        pw_in   = canvas._paper_phys_w
        ph_in   = canvas._paper_phys_h

        writer = QPdfWriter(path)
        writer.setResolution(150)
        writer.setPageSize(
            QPageSize(QSizeF(pw_in * 25.4, ph_in * 25.4),
                      QPageSize.Unit.Millimeter))
        writer.setPageMargins(QMarginsF(0, 0, 0, 0),
                              QPageLayout.Unit.Millimeter)

        painter = QPainter(writer)
        try:
            self._render_page(painter, QRectF(painter.viewport()))
        finally:
            painter.end()

        QMessageBox.information(self, 'PDF Export', f'Saved:\n{path}')

    def closeEvent(self, event):
        # Skip the prompt for never-shown windows (headless tests).
        if self.isVisible() and not self._canvas._undo_stack.isClean():
            r = QMessageBox.question(
                self, 'Unsaved Changes',
                'You have unsaved changes. Save before closing?',
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save)
            if r == QMessageBox.StandardButton.Save:
                if not self._canvas.save_project():
                    event.ignore()
                    return
                self._sync_title()
            elif r == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()

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


