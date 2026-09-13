"""
ArchCAD — Fixture Panel  (dropdown edition)
A QComboBox selects the active category; the tile grid below updates
to show all fixtures for that category.  Clicking a tile activates
placement mode on the canvas.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QToolButton,
    QComboBox, QScrollArea, QStackedWidget, QFrame,
)
from PyQt6.QtCore    import Qt, QSize, pyqtSignal
from PyQt6.QtGui     import QPixmap, QPainter, QColor, QIcon

from fixtures import FIXTURE_SPECS, FIXTURE_CATEGORIES

# ── Thumbnail renderer ───────────────────────────────────────────────

_THUMB = 44

def render_thumbnail(fixture_type: str) -> QPixmap:
    """Render a 44×44 px QPixmap of the fixture symbol."""
    pm  = QPixmap(_THUMB, _THUMB)
    pm.fill(QColor('#111111'))
    spec = FIXTURE_SPECS.get(fixture_type)
    if not spec:
        return pm
    label, cat, dw, dh, draw_fn = spec
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
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

# ── Tile button ─────────────────────────────────────────────────────

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
QToolButton:hover   { background: #222; border-color: #555; }
QToolButton:pressed { background: #111; }
QToolButton:checked { background: #2a1a0e; border-color: #c85a14; }
"""

class _FixtureTile(QToolButton):
    def __init__(self, fixture_type: str, label: str, parent=None):
        super().__init__(parent)
        self._ftype = fixture_type
        pm = render_thumbnail(fixture_type)
        self.setIcon(QIcon(pm))
        self.setIconSize(QSize(_THUMB, _THUMB))
        short = label.split('(')[0].strip()
        if len(short) > 14:
            short = short[:13] + '…'
        self.setText(short)
        self.setToolTip(label)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setStyleSheet(_TILE_CSS)
        self.setCheckable(True)
        self.setFixedSize(QSize(64, 70))

# ── Main panel widget ────────────────────────────────────────────────

_CMB_CSS = """
QComboBox {
    background: #1e3050;
    border: 1px solid #3a5070;
    border-radius: 3px;
    color: #dce8f5;
    font-size: 9pt;
    font-family: 'Segoe UI';
    padding: 3px 6px;
    min-height: 22px;
}
QComboBox:hover  { border-color: #5a80aa; }
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background: #1a2d46;
    border: 1px solid #3a5070;
    color: #dce8f5;
    selection-background-color: #2d4a6e;
    font-size: 9pt;
    font-family: 'Segoe UI';
    padding: 2px;
}
"""

_PANEL_CSS = """
QScrollArea  { border: none; background: #1a2333; }
QWidget#fp_page { background: #1a2333; }
"""


class FixturePanel(QWidget):
    """
    Category dropdown + scrollable tile grid.
    Emit fixture_selected(str key) when a tile is clicked.
    """
    fixture_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_PANEL_CSS)

        # { category -> [tile, ...] }  — built lazily when first shown
        self._tiles_by_cat: dict[str, list[_FixtureTile]] = {}
        self._active_key = ''

        # ─ category map ────────────────────────────────────────────────
        self._cat_keys: dict[str, list[str]] = {c: [] for c in FIXTURE_CATEGORIES}
        for key, spec in FIXTURE_SPECS.items():
            cat = spec[1]
            if cat in self._cat_keys:
                self._cat_keys[cat].append(key)

        # ─ layout ───────────────────────────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setSpacing(4)
        outer.setContentsMargins(4, 4, 4, 4)

        # Dropdown
        self._cmb = QComboBox()
        self._cmb.setStyleSheet(_CMB_CSS)
        for cat in FIXTURE_CATEGORIES:
            self._cmb.addItem(cat)
        outer.addWidget(self._cmb)

        # Tile area (one page per category)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(self._scroll)

        self._stack = QStackedWidget()
        self._scroll.setWidget(self._stack)

        for cat in FIXTURE_CATEGORIES:
            page = self._build_page(cat)
            self._stack.addWidget(page)

        self._cmb.currentIndexChanged.connect(self._on_category_changed)
        self._stack.setCurrentIndex(0)

    # ─ Page builder ────────────────────────────────────────────────

    def _build_page(self, category: str) -> QWidget:
        page = QWidget()
        page.setObjectName('fp_page')
        grid = QGridLayout(page)
        grid.setSpacing(3)
        grid.setContentsMargins(3, 6, 3, 6)
        grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        tiles: list[_FixtureTile] = []
        cols = 3
        for idx, key in enumerate(self._cat_keys.get(category, [])):
            spec = FIXTURE_SPECS.get(key)
            if not spec:
                continue
            tile = _FixtureTile(key, spec[0], page)
            tile.clicked.connect(lambda checked, k=key: self._on_tile_clicked(k))
            tiles.append(tile)
            grid.addWidget(tile, idx // cols, idx % cols)

        self._tiles_by_cat[category] = tiles
        return page

    # ─ Slots ──────────────────────────────────────────────────────

    def _on_category_changed(self, idx: int):
        self._stack.setCurrentIndex(idx)
        self._scroll.verticalScrollBar().setValue(0)
        self.deselect_all()

    def _on_tile_clicked(self, key: str):
        # Uncheck every other tile across all categories
        for tiles in self._tiles_by_cat.values():
            for t in tiles:
                if t._ftype != key:
                    t.setChecked(False)
        self._active_key = key
        self.fixture_selected.emit(key)

    # ─ Public API ─────────────────────────────────────────────────

    def deselect_all(self):
        """Call when placement mode is cancelled (Esc / tool change)."""
        for tiles in self._tiles_by_cat.values():
            for t in tiles:
                t.setChecked(False)
        self._active_key = ''
