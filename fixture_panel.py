"""
ArchCAD — Fixture Panel
Collapsible tile palette rendered in the left Elements dock.
Each tile shows a 44×44 QPainter thumbnail + label.
Clicking a tile activates placement mode on the canvas.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QToolButton,
    QLabel, QSizePolicy, QScrollArea, QFrame,
)
from PyQt6.QtCore    import Qt, QSize, pyqtSignal
from PyQt6.QtGui     import QPixmap, QPainter, QColor, QIcon

from fixtures import FIXTURE_SPECS, FIXTURE_CATEGORIES

# ── Thumbnail renderer ────────────────────────────────────────────────────────

_THUMB = 44   # thumbnail pixel size

def render_thumbnail(fixture_type: str) -> QPixmap:
    """Render a 44×44 px QPixmap of the fixture symbol."""
    pm  = QPixmap(_THUMB, _THUMB)
    pm.fill(QColor('#1a2333'))
    spec = FIXTURE_SPECS.get(fixture_type)
    if not spec:
        return pm
    label, cat, dw, dh, draw_fn = spec
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Scale fixture to fit thumbnail with 3px margin
    margin = 3
    avail  = _THUMB - 2 * margin
    scale  = min(avail / max(dw, 1), avail / max(dh, 1))
    ox = margin + (avail - dw * scale) / 2
    oy = margin + (avail - dh * scale) / 2
    painter.translate(ox, oy)
    painter.scale(scale, scale)
    try:
        draw_fn(painter, dw, dh, False)
    except Exception:
        pass
    painter.end()
    return pm

# ── Tile button ───────────────────────────────────────────────────────────────

_TILE_CSS = """
QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 3px;
    padding: 2px;
    color: #a8bcd0;
    font-size: 6.5pt;
    font-family: 'Segoe UI';
}
QToolButton:hover   { background: #2d4a6e; border-color: #4a6a9e; }
QToolButton:pressed { background: #1e3558; }
QToolButton:checked { background: #1e3a5a; border-color: #5a90c0; }
"""

class _FixtureTile(QToolButton):
    def __init__(self, fixture_type: str, label: str, parent=None):
        super().__init__(parent)
        self._ftype = fixture_type
        pm  = render_thumbnail(fixture_type)
        self.setIcon(QIcon(pm))
        self.setIconSize(QSize(_THUMB, _THUMB))
        # Truncate label for tile display
        short = label.split('(')[0].strip()
        if len(short) > 14:
            short = short[:13] + '…'
        self.setText(short)
        self.setToolTip(label)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setStyleSheet(_TILE_CSS)
        self.setCheckable(True)
        self.setFixedSize(QSize(64, 70))

# ── Collapsible category section ──────────────────────────────────────────────

_HDR_CSS = (
    "QPushButton {"
    "  background: #2c4a6e; border: none;"
    "  border-bottom: 1px solid #1a3050;"
    "  padding: 3px 6px; text-align: left;"
    "  font-size: 9pt; font-weight: bold; color: #ffffff;"
    "  font-family: 'Segoe UI';"
    "}"
    "QPushButton:hover { background: #3a5a80; }"
)

from PyQt6.QtWidgets import QPushButton

class _FixtureSection(QWidget):
    tile_clicked = pyqtSignal(str)   # emits fixture_type

    def __init__(self, category: str, keys: list, parent=None):
        super().__init__(parent)
        self._expanded = True
        self._category = category
        self._tiles: list[_FixtureTile] = []

        vl = QVBoxLayout(self)
        vl.setSpacing(0)
        vl.setContentsMargins(0, 0, 0, 0)

        self._hdr = QPushButton(f'▼  {category}')
        self._hdr.setStyleSheet(_HDR_CSS)
        self._hdr.setFixedHeight(24)
        self._hdr.clicked.connect(self._toggle)

        self._body = QWidget()
        grid = QGridLayout(self._body)
        grid.setSpacing(2)
        grid.setContentsMargins(3, 3, 3, 6)

        cols = 3
        for idx, key in enumerate(keys):
            spec  = FIXTURE_SPECS.get(key)
            if not spec:
                continue
            label = spec[0]
            tile  = _FixtureTile(key, label, self._body)
            tile.clicked.connect(lambda checked, k=key: self._on_tile(k))
            self._tiles.append(tile)
            grid.addWidget(tile, idx // cols, idx % cols)

        vl.addWidget(self._hdr)
        vl.addWidget(self._body)

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        arrow = '▼' if self._expanded else '▶'
        self._hdr.setText(f'{arrow}  {self._category}')

    def _on_tile(self, key: str):
        # Uncheck all other tiles
        for t in self._tiles:
            if t._ftype != key:
                t.setChecked(False)
        self.tile_clicked.emit(key)

    def deselect_all(self):
        for t in self._tiles:
            t.setChecked(False)

# ── Main panel widget ─────────────────────────────────────────────────────────

_PANEL_CSS = """
QScrollArea         { border: none; background: #1a2333; }
QWidget#fp_body     { background: #1a2333; }
QLabel#fp_hdr_lbl   {
    color: #8090a8; font-size: 7.5pt; font-family: 'Segoe UI';
    padding: 6px 6px 2px 6px; background: #1a2333;
}
"""

_SEP_CSS = (
    'background: #2a3850; min-height: 1px; max-height: 1px;'
    ' margin: 4px 0px;'
)


class FixturePanel(QWidget):
    """
    Embeddable widget that shows collapsible fixture categories.
    Connect fixture_selected(str fixture_type) to handle placement.
    """
    fixture_selected = pyqtSignal(str)   # emits fixture_type when tile clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_PANEL_CSS)
        self._sections: list[_FixtureSection] = []
        self._active_key: str = ''

        outer = QVBoxLayout(self)
        outer.setSpacing(0)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        body.setObjectName('fp_body')
        vl   = QVBoxLayout(body)
        vl.setSpacing(0)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Build by category (order from FIXTURE_CATEGORIES)
        cat_map: dict[str, list] = {c: [] for c in FIXTURE_CATEGORIES}
        for key, spec in FIXTURE_SPECS.items():
            cat = spec[1]
            if cat in cat_map:
                cat_map[cat].append(key)

        for cat in FIXTURE_CATEGORIES:
            keys = cat_map.get(cat, [])
            if not keys:
                continue
            sep = QFrame()
            sep.setStyleSheet(_SEP_CSS)
            vl.addWidget(sep)
            sec = _FixtureSection(cat, keys)
            sec.tile_clicked.connect(self._on_section_tile)
            self._sections.append(sec)
            vl.addWidget(sec)

        vl.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)

    # ── Signals & public API ──────────────────────────────────────────────────

    def _on_section_tile(self, key: str):
        # Deselect all other sections' tiles
        for sec in self._sections:
            if sec._category != FIXTURE_SPECS[key][1]:
                sec.deselect_all()
        self._active_key = key
        self.fixture_selected.emit(key)

    def deselect_all(self):
        """Call when placement mode is cancelled (Esc / tool change)."""
        for sec in self._sections:
            sec.deselect_all()
        self._active_key = ''
