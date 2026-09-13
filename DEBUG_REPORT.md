# ArchCAD — Comprehensive Debug Report

**Analysis date:** 2025-07  
**Source files audited:** `main.py`, `canvas.py`, `items.py`, `fixtures.py`, `fixture_panel.py`, `mainwindow.py`, `rulers.py`  
**Smoke test:** 115/115 passed (all clean)  
**Static/lint errors (Pylance):** 0  
**Dependency:** `PyQt6 >= 6.4.0` — only dependency, correct

---

## Architecture Summary

| Layer | File | Responsibility |
|---|---|---|
| Entry point | `main.py` | QApplication + Fusion style, launches MainWindow |
| Main window | `mainwindow.py` (~2050 lines) | Ribbon, menus, docks, all UI signals |
| Canvas | `canvas.py` (~1000 lines) | QGraphicsView, tool state machine, undo stack, save/load |
| Items | `items.py` (~1095 lines) | 12 QGraphicsItem subclasses + undo commands |
| Fixtures | `fixtures.py` (~1820 lines) | 88 architectural draw functions + FIXTURE_SPECS registry |
| Fixture panel | `fixture_panel.py` | Category tiles, thumbnails, fixture_selected signal |
| Rulers | `rulers.py` | HRuler + VRuler, viewport_changed sync |

**Scene coordinate system:** 1 scene unit = 1 inch. Grid minor = 12 in (1 ft), major = 48 in (4 ft). Default zoom = 2 px/in. Default scale ratio = 48 (1/4" = 1 ft).

---

## Bug Findings

### BUG-01 · CRITICAL — `paste_items` silently drops all FixtureItems

**File:** `canvas.py`, line ~662  
**Severity:** Critical (data loss)

The `loaders` dict in `paste_items()` maps `item_type` strings to their constructors for all 10 core item types, but omits `FixtureItem`:

```python
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
    # FixtureItem is MISSING
}
```

**Effect:** Any fixture item in the clipboard is silently skipped — `loaders.get('fixture')` returns `None`, the `if cls:` guard skips it, and no error is raised. Copy → Paste and the Duplicate action both lose all fixtures with no user feedback.  
Note: `open_project()` correctly includes `FixtureItem` in its loaders; this omission is isolated to the clipboard path.

**Fix:**
```python
from fixtures import FixtureItem
loaders = {
    ...
    GroupItem.item_type:   GroupItem,
    FixtureItem.item_type: FixtureItem,   # add this line
}
```
The paste offset logic (`dc['x'] + offset_x`) does not apply to `FixtureItem` because it uses `'x'`/`'y'` keys which `FixtureItem.to_dict()` does store. The fix is a one-line addition.

---

### BUG-02 · HIGH — Door width preset has no effect

**File:** `canvas.py` line 336 + `mainwindow.py` line ~760  
**Severity:** High (feature completely broken)

The Door Width preset in the presets dock sets `self._canvas._door_width`:

```python
# mainwindow.py _build_presets_dock
def _door_act(idx):
    self._canvas._door_width = _door_entries[idx][1]   # e.g. 30, 32, 36...
    self._set_tool(TOOL_DOOR)
```

But when `TOOL_DOOR` places a door, it ignores `_door_width` and hardcodes 36 inches:

```python
# canvas.py mousePressEvent
elif self._tool == TOOL_DOOR:
    self._preview = DoorItem(36)   # ← hardcoded; never reads _door_width
```

**Effect:** Every door placed is always 36 inches wide regardless of the selected preset. `_door_width` is initialized in `__init__` and updated by the preset but is never read during door placement.

**Fix:** Replace the hardcoded `36` with `self._door_width`:
```python
elif self._tool == TOOL_DOOR:
    self._preview = DoorItem(self._door_width)
```

---

### BUG-03 · HIGH — Window width preset has no effect

**File:** `mainwindow.py` line 780–782  
**Severity:** High (feature completely broken)

The Window Width preset sets `_door_width` (reusing the door width slot):

```python
def _win_act(idx):
    self._canvas._door_width = _win_widths[idx]   # ← sets _door_width
    self._set_tool(TOOL_WINDOW)
```

But the window tool uses a drag-to-size interaction that sets `dx`/`dy` from the mouse gesture and never reads `_door_width` at all:

```python
# canvas.py mousePressEvent
elif self._tool == TOOL_WINDOW:
    self._preview = WindowItem(0, 0)   # always starts at (0,0)
    self._preview.setPos(pt)
    ...
```

**Effect:** The Window Width preset is a complete no-op. Windows are always sized by dragging; the preset combo has no influence on the result. Users selecting a preset width get no feedback that it isn't working.

**Fix:** The window tool needs a dedicated `_window_width` field and a click-to-place interaction (similar to how `TOOL_DOOR` uses a click, not a drag). Or the preset should be removed/disabled for windows since drag-to-size is the intended UX. A simpler fix is to add a `_window_width` attribute and on mouse-press, create `WindowItem(_window_width, 0)` so the horizontal size is preset and only the direction/angle is set by drag.

---

### BUG-04 · MEDIUM — `place_post_grid` is not undoable

**File:** `canvas.py` lines 925–940  
**Severity:** Medium (UX regression)

Posts placed by the Auto-fill Posts dialog are added directly to the scene without an undo command:

```python
def place_post_grid(self, origin_x, origin_y, width, height,
                    spacing_x, spacing_y, post_size):
    x = origin_x
    while x <= origin_x + width + 0.1:
        y = origin_y
        while y <= origin_y + height + 0.1:
            post = PostItem(post_size)
            post.setPos(x, y)
            self.scene().addItem(post)   # ← no undo push
            y += spacing_y
        x += spacing_x
```

**Effect:** Placing a 5×5 post grid adds 25 items that cannot be undone. Ctrl+Z after this operation does nothing. The only remedy is selecting all new posts manually and deleting them.

**Fix:** Wrap in a macro undo operation:
```python
def place_post_grid(self, origin_x, origin_y, width, height,
                    spacing_x, spacing_y, post_size):
    posts = []
    x = origin_x
    while x <= origin_x + width + 0.1:
        y = origin_y
        while y <= origin_y + height + 0.1:
            post = PostItem(post_size)
            post.setPos(x, y)
            post._layer_idx = self._active_layer
            self.scene().addItem(post)
            posts.append(post)
            y += spacing_y
        x += spacing_x
    if posts:
        self._undo_stack.beginMacro(f'Auto-fill {len(posts)} post(s)')
        for post in posts:
            self._undo_stack.push(_AddCmd(self.scene(), post))
        self._undo_stack.endMacro()
```

Note: The existing smoke test `place_post_grid 3x3 = 9` only checks post count, not undoability. A test covering undo behavior is needed here.

---

### BUG-05 · MEDIUM — Style dialog changes are not undoable

**File:** `mainwindow.py` lines 1522–1590  
**Severity:** Medium (UX regression)

`_act_style_dialog()` applies fill, border, and color changes directly to items without using `_PropCmd` or any undo command:

```python
if dlg.exec() == QDialog.DialogCode.Accepted:
    if fill_btn:
        for s in shapes:
            s.fill = fill_btn._hex    # ← direct mutation, no undo
            s.update()
    if border_btn:
        for s in shapes:
            s.border = border_btn._hex
            s.update()
    if line_btn:
        for li in lines_:
            li.line_color = line_btn._hex
            li._apply_pen()           # ← direct mutation, no undo
    if text_btn:
        for t in texts:
            t.color = text_btn._hex
            t.update()
```

**Effect:** After using the Style dialog, Ctrl+Z does not revert style changes. The undo history skips over them entirely.

**Fix:** Capture old values before the dialog and push `_PropCmd` lambdas:
```python
if dlg.exec() == QDialog.DialogCode.Accepted:
    self._canvas._undo_stack.beginMacro('Style change')
    for s in shapes:
        old_fill, old_bdr = s.fill, s.border
        new_fill = fill_btn._hex if fill_btn else s.fill
        new_bdr  = border_btn._hex if border_btn else s.border
        def _do(it=s, f=new_fill, b=new_bdr):
            it.fill = f; it.border = b; it.update()
        def _un(it=s, f=old_fill, b=old_bdr):
            it.fill = f; it.border = b; it.update()
        _do()
        self._canvas._undo_stack.push(_PropCmd('Style', _do, _un))
    # similar for lines_ and texts
    self._canvas._undo_stack.endMacro()
```

---

### BUG-06 · MEDIUM — R key conflict: rotates items AND switches to Room tool simultaneously

**File:** `canvas.py` line 605 + `mainwindow.py` line 56  
**Severity:** Medium (incorrect behavior)

The canvas handles `Key_R` in `keyPressEvent` to rotate selected items:

```python
# canvas.py
elif k == Qt.Key.Key_R:
    delta = -90.0 if mods & Qt.KeyboardModifier.ShiftModifier else 90.0
    self._rotate_selection(delta)
    event.accept()
    return
```

Separately, mainwindow registers a `QShortcut` mapping `'R'` to TOOL_ROOM:

```python
# mainwindow.py _build_home_tab
(TOOL_ROOM, 'Room', 'R'),
...
sc = QShortcut(QKeySequence(key), self)
sc.activated.connect(lambda t=tool: self._set_tool(t))
```

**Effect:** `QShortcut.activated` fires at the application level and is not suppressed by a widget's `event.accept()`. Pressing R while any Door, Window, or Fixture is selected both rotates the item(s) **and** switches the active tool to Room — a side-effect the user never intended. After rotation, the user has to re-select their drawing tool.

**Fix (Option A — Remove R shortcut from Room tool):** Change TOOL_ROOM's shortcut to a key not used by canvas (e.g., `'M'` for "Make room").

**Fix (Option B — Move rotation to a non-conflicting key):** Use `'E'` for rotate in canvas.keyPressEvent and remove the Room shortcut or rebind it.

**Fix (Option C — Guard the shortcut):** Override the Room shortcut to check whether canvas has selected items before activating:
```python
sc.activated.connect(lambda t=tool: (
    self._set_tool(t)
    if not any(hasattr(i,'to_dict') for i in self._canvas.scene().selectedItems())
    else None
))
```

---

### BUG-07 · LOW — `_RotatableMixin.mouseReleaseEvent` silently fails if scene has no views

**File:** `items.py` ~line 150  
**Severity:** Low (edge case)

```python
def mouseReleaseEvent(self, event):
    ...
    views = scene.views()
    if views and hasattr(views[0], '_undo_stack'):
        stk = views[0]._undo_stack
        self.setRotation(old)
        stk.push(_RotateItemCmd(self, old, new))
    else:
        pass  # rotation applied but not pushed to undo stack
```

**Effect:** If `scene.views()` is empty (e.g., in testing or if an item is attached to a scene without a view), the rotation happens but is not registered in the undo stack. The user sees the rotation but cannot undo it. No error is raised.  

**Fix:** Pass the undo stack reference through the item (e.g., store it as `item._undo_stack` when the item is added to the canvas) rather than reaching through the scene's view list. This is the standard approach for items that need undo access.

---

### BUG-08 · LOW — `GroupItem` missing `_locked` attribute

**File:** `items.py` ~line 1000  
**Severity:** Low (potential AttributeError)

`GroupItem` does not inherit `_SelectableMixin` and does not call `_setup_base()`. It manually sets `item_id` and `_layer_idx`, but never sets `_locked`:

```python
class GroupItem(QGraphicsItemGroup):
    def __init__(self):
        super().__init__()
        self.item_id    = str(uuid.uuid4())
        self._layer_idx = 0
        # _locked is never set
```

All current code that accesses `_locked` uses `getattr(item, '_locked', False)` or guards via `hasattr(i, 'set_locked')`, so no crash occurs today. However, any future code that accesses `group._locked` directly (without the `getattr` default) will raise `AttributeError`.

**Fix:** Add `self._locked = False` to `GroupItem.__init__`.

---

## Observations (Non-Bug Issues)

### OBS-01 — `place_post_grid` ignores `_active_layer`

**File:** `canvas.py` line ~935  
**Severity:** Informational

Auto-placed posts are not assigned to the active layer:

```python
post = PostItem(post_size)
post.setPos(x, y)
self.scene().addItem(post)
# post._layer_idx is 0 (default) regardless of active layer
```

Compare with the single-click post placement in `mousePressEvent`:
```python
post._layer_idx = self._active_layer   # ← single-click sets layer correctly
```

**Effect:** Posts placed via the Auto-fill dialog always land on Layer 0 even if the user is working on a different layer. The fix adds `post._layer_idx = self._active_layer` inside the loop (same as shown in BUG-04's fix).

---

### OBS-02 — `_draw_insul_blown` imports `random` inside paint function

**File:** `fixtures.py`  
**Severity:** Informational (style)

```python
def _draw_insul_blown(p, w, h, sel):
    import random; rng = random.Random(42)
```

Python caches module imports so this has negligible runtime cost after the first call. The seeded `random.Random(42)` ensures deterministic rendering, which is correct. However, placing an import inside a paint callback is unconventional and may confuse future maintainers.

**Suggestion:** Move `import random` to the top of `fixtures.py` with the other imports.

---

### OBS-03 — Mislabeled inline comment in `CADCanvas.__init__`

**File:** `canvas.py` ~line 178  
**Severity:** Informational (cosmetic)

```python
self._move_origins: dict = {}        # ── layers ──────
self._layers: list[dict] = [{'name': 'Layer 0', 'visible': True, 'locked': False}]
```

The `# ── layers ──` section marker appears on the `_move_origins` line. It should be on the `_layers` line.

---

### OBS-04 — Rubber-band area-select is disabled in SELECT mode

**File:** `canvas.py` ~line 310  
**Severity:** Informational (UX limitation)

In SELECT mode, clicking on empty canvas space activates a pan gesture:

```python
if self._tool == TOOL_SELECT:
    if (event.button() == Qt.MouseButton.LeftButton
            and self.itemAt(event.pos()) is None):
        self._sel_pan_last = event.position()
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()
        return
```

`event.accept()` + `return` prevents `super().mousePressEvent(event)` from being called, which disables the native QGraphicsView rubber-band drag selection when starting from empty space. Users can only area-select if they already have a partial selection or use Ctrl+A.

This may be intentional, but it's worth noting that users accustomed to other CAD tools expect to drag-select from empty space.

---

### OBS-05 — PDF export uses `painter.viewport()` (QRect) passed to QRectF

**File:** `mainwindow.py` line ~1981  
**Severity:** Informational (minor type mismatch)

```python
target = QRectF(painter.viewport())
```

`QPainter.viewport()` returns a `QRect`. `QRectF(QRect)` is a valid conversion in PyQt6, so no crash or precision issue occurs in practice. It is slightly cleaner to write `QRectF(painter.viewport())` explicitly noting the conversion, or use `painter.window()` which returns the logical paint rectangle.

---

## Smoke Test Results

```
115/115 passed  -- all tests passed
```

All 16 test sections (11 + 10 + 14 + 11 + 10 + 8 + 9 + 3 + 3 + 9 + 5 + 4 + 7 + 5 + 5 + 3) passed without failures. Sections tested: `_ft` formatter, length parser, item constructors, serialization, canvas defaults, undo/redo, layers, save/load roundtrip, paste/duplicate, MainWindow selection, property commits, lock toggle, alignment, z-order, scale/paper/post-grid, item flags.

**Coverage gap:** No test covers paste behavior for `FixtureItem` (BUG-01). Adding a test that copies a fixture, pastes it, and checks the paste result is returned would catch this regression.

---

## Summary Table

| ID | Severity | File | Description |
|---|---|---|---|
| BUG-01 | **Critical** | `canvas.py:662` | `paste_items` missing `FixtureItem` — fixtures silently lost on paste |
| BUG-02 | **High** | `canvas.py:336` | Door width preset ignored — always places 36" door |
| BUG-03 | **High** | `mainwindow.py:781` | Window width preset is a no-op — `_door_width` not used by window tool |
| BUG-04 | **Medium** | `canvas.py:925` | `place_post_grid` not undoable — Ctrl+Z has no effect |
| BUG-05 | **Medium** | `mainwindow.py:1573` | Style dialog changes not undoable |
| BUG-06 | **Medium** | `canvas.py:605` | R key conflict — rotates items AND switches to Room tool |
| BUG-07 | **Low** | `items.py:~150` | `_RotatableMixin` rotation undo silently fails if scene has no views |
| BUG-08 | **Low** | `items.py:~1000` | `GroupItem` missing `_locked` attribute — potential future AttributeError |
| OBS-01 | Info | `canvas.py:935` | Auto-fill posts ignore active layer — always placed on Layer 0 |
| OBS-02 | Info | `fixtures.py` | `import random` inside paint function |
| OBS-03 | Info | `canvas.py:~178` | Mislabeled `# ── layers ──` comment on wrong line |
| OBS-04 | Info | `canvas.py:~310` | Rubber-band area-select blocked in SELECT mode (pan takes priority) |
| OBS-05 | Info | `mainwindow.py:~1981` | `QRect` passed to `QRectF()` implicitly |

---

## Recommended Fix Priority

1. **BUG-01** (paste loses fixtures) — one-line fix, high impact
2. **BUG-02** (door width ignored) — one-word fix (`self._door_width`), high impact  
3. **BUG-04** (post grid not undoable) — ~8 lines, needed for correctness
4. **BUG-06** (R key conflict) — requires a shortcut rebind decision
5. **BUG-03** (window width no-op) — requires UX decision on window placement model
6. **BUG-05** (style not undoable) — 15–20 lines, improves reliability
7. **BUG-07 / BUG-08** — defensive fixes, low priority
