# ArchCAD — Material Estimator Implementation Plan

> Mark items `[x]` as each step is completed.

---

## Backups Created (pre-estimator — 2026-06-03)

- [x] `canvas.bak.pre-estimator-20260603.py`
- [x] `mainwindow.bak.pre-estimator-20260603.py`
- [x] `items.bak.pre-estimator-20260603.py`

---

## UI Note: Drop-Down Menus Only

All estimator result categories are displayed using **QComboBox / drop-down selectors** for category navigation. No collapsible tree nodes. The results table filters to show the selected category.

---

## Phase 1 — New File: `estimator.py`

- [x] **1.1** Create `estimator.py` with `EstimatorSettings` dataclass
  - All user-configurable inputs (post spacing, joist size, stud spacing, waste %, etc.)
- [x] **1.2** `LumberSchedule` helper class
  - `STOCK_LENGTHS_FT = [8, 10, 12, 14, 16, 18, 20]`
  - `round_up(raw_ft)` → nearest stock length
  - `summarize(list[float])` → `{8: n, 10: n, ...}` purchase dict
- [x] **1.3** `MaterialReport` class
  - Holds list of `LineItem(category, description, qty, unit, notes)`
  - `to_csv()` → string
  - `to_plain_text()` → clipboard-friendly string
- [x] **1.4** `MaterialEstimator.run(scene_items, settings)` main entry
  - Iterates canvas items, dispatches to per-category methods
- [x] **1.5** `_calc_substructure(joistfills, posts_placed, settings)`
  - Interior joists (count + lengths → stock groups)
  - Band / rim boards (perimeter of each JoistFillItem)
  - Blocking rows (1 row mid-span if joist span > 96 in)
  - Post count from grid (corners always included, user spacing X/Y)
  - Post lumber lengths (height + 6 in below grade minimum → stock)
  - Ledger board toggle (longest edge adjacent to a WallItem)
- [x] **1.6** `_calc_decking(joistfills, settings)`
  - **Deck boards mode**: area / board_width_in → linear ft → stock groups + count; + deck screws
  - **Plywood / OSB mode**: area / 32 sqft → sheet count (round up + waste %)
  - Construction adhesive (1 tube per 4 sheets, subfloor mode)
  - Hidden fastener clips (optional toggle)
- [x] **1.7** `_calc_walls(walls, doors, windows, settings)`
  - **Wall framing mode**:
    - Bottom plate: sum of WallItem lengths
    - Top plate(s): plate_count × same
    - Studs per wall + extra for corners (3-stud assembly)
    - Stud cut length → stock (ceiling_ht − 3 × 1.5 in)
    - Headers over doors (size by span table: ≤4 ft → 2×6, ≤6 ft → 2×8, ≤8 ft → 2×10, >8 ft → 2×12)
    - Headers over windows (same span table)
    - Jack studs (2 per opening)
    - King studs (2 per opening, full height)
    - Cripples above header (opening_width / stud_spacing, rounded up)
    - Sill plate per window + cripples below sill
    - Wall sheathing (OSB/plywood sheets, area / 32)
    - Drywall sheets (same area calc, separate tally)
    - Batt insulation bags (area → bags, by R-value / depth)
    - Vapor barrier rolls (area / 1000 sqft per roll)
  - **Rail framing mode**:
    - Top rail linear ft
    - Bottom rail linear ft
    - Balusters (linear_ft × 12 / 4-in spacing, round up)
    - Rail posts (every 6–8 ft + corners)
- [x] **1.8** `_calc_concrete(post_count, settings)`
  - Tube form (Sonotube): 1 per post × depth_ft → linear ft → count of 4 ft sections
  - Concrete volume per footing = π × (dia_in/2 in ft)² × depth_ft
  - Total cubic yards → 60 lb bags (0.45 cu ft each) or 80 lb (0.60 cu ft)
  - Rebar vertical (optional): 2 × depth_ft per post → stock 10 ft lengths
  - Post bases (Simpson ABA44 / CB66): 1 per post
  - J-bolt anchor bolts: 1 per post
- [x] **1.9** `_calc_hardware(joist_count, post_count, rafter_count, settings)`
  - Joist hangers (LUS/LU): 2 per interior joist (both ends)
  - Post caps (Simpson BC/PCZ): 1 per post
  - Beam seat hardware: per beam end count
  - Hurricane ties (H2.5A): 2 per joist (for roof/floor)
  - Ledger lag bolts: every 16 in along ledger
  - Structural screws / nails: 3 per joist end (rim connection)
- [x] **1.10** `_calc_roof(rooms, settings)`
  - Rafter length = `run × sqrt(1 + (pitch/12)²)` + overhang
  - Rafter count = `floor(building_length / spacing) + 1` × 2 sides
  - Ridge board = building length + 2× overhang
  - Collar ties = every other rafter pair
  - Roof sheathing: rafter_len × building_len × 2 / 32 → sheets
  - Underlayment rolls (400 sqft/roll)
  - Drip edge: perimeter linear ft
- [x] **1.11** `_calc_finish(rooms, walls, settings)`
  - Exterior paint / stain: wall area / 350 sqft per gallon
  - Primer: same area / 400 sqft per gallon
  - Deck stain / sealer: deck area / 200 sqft per gallon
  - Caulk tubes: 1 per 25 linear ft of seams
- [ ] **1.12** `_calc_electrical_stub(rooms, walls, settings)` *(rough-in estimate)*
  - Outlet boxes: 1 per 12 linear ft of wall
  - Switch boxes: 1 per DoorItem
  - Romex 14/2: ceiling_ht × outlet_count × 1.25 linear ft

---

## Phase 2 — `canvas.py` Changes

- [x] **2.1** Add ~15 new estimator settings attributes to `CADCanvas.__init__`:
  ```python
  self._est_post_spacing_x   = 8.0    # ft
  self._est_post_spacing_y   = 8.0    # ft
  self._est_post_height      = 3.0    # ft
  self._est_joist_size       = '2x10'
  self._est_beam_size        = '3x10'
  self._est_decking_type     = 'deck_board'  # 'deck_board' | 'plywood'
  self._est_deck_board_width = 5.5    # actual in (5/4x6)
  self._est_waste_pct        = 10     # %
  self._est_stud_spacing     = 16     # in
  self._est_stud_size        = '2x4'  # '2x4' | '2x6'
  self._est_plate_count      = 2      # 1 or 2 top plates
  self._est_ceiling_ht       = 8.0    # ft
  self._est_roof_pitch       = 4      # in/12
  self._est_footing_dia      = 12     # in
  self._est_footing_depth    = 42     # in
  self._est_surface_mode     = 'walls'    # 'walls' | 'rails'
  self._est_include_hardware = True
  self._est_include_concrete = True
  self._est_include_roof     = False
  self._est_include_finish   = False
  self._est_include_electrical = False
  self._est_stock_lengths    = [8, 10, 12, 16]  # selectable
  ```

---

## Phase 3 — `mainwindow.py` Changes

- [x] **3.1** Import `EstimatorSettings`, `MaterialEstimator` from `estimator`
- [x] **3.2** Add `_build_estimator_dock()` call in `__init__` after `_build_layers_dock()`
- [x] **3.3** Build the Estimator dock panel with **drop-down category selector**:
  ```
  ┌─────────────────────────────────────┐
  │  ESTIMATOR                          │
  ├─────────────────────────────────────┤
  │  SETTINGS                           │
  │  Post spacing X:  [  8.0 ft  ▲▼]   │
  │  Post spacing Y:  [  8.0 ft  ▲▼]   │
  │  Post height:     [  3.0 ft  ▲▼]   │
  │  Joist size:      [ 2x10    ▼ ]    │
  │  Stud spacing:    [ 16"     ▼ ]    │
  │  Ceiling height:  [  8.0 ft  ▲▼]   │
  │  Decking:         [ Boards  ▼ ]    │
  │   └ Board width:  [  5.5"   ▲▼]   │
  │  Surface mode:    [ Walls   ▼ ]    │
  │  Waste factor:    [ 10%     ▲▼]    │
  │  Footing dia:     [ 12"     ▼ ]    │
  │  Footing depth:   [ 42"     ▲▼]   │
  │  Include:  [x] Hardware  [x] Concrete │
  │            [ ] Roof      [ ] Finish  │
  ├─────────────────────────────────────┤
  │  [ Scope: Full Project ▼ ]          │
  │  [     Calculate Materials     ]    │
  ├─────────────────────────────────────┤
  │  Category:  [ All ▼ ]  (drop-down)  │
  │  ┌───────────────────────────────┐  │
  │  │ Description  │ Qty │ Unit │Notes│ │
  │  │ ...          │     │      │     │ │
  │  └───────────────────────────────┘  │
  ├─────────────────────────────────────┤
  │  [Export CSV]      [Copy to Clipboard] │
  └─────────────────────────────────────┘
  ```
- [x] **3.4** `_act_calculate_materials()` — builds `EstimatorSettings` from dock spinboxes, calls `MaterialEstimator.run()`, populates the results `QTableWidget`
- [x] **3.5** Category drop-down filters `QTableWidget` rows
- [x] **3.6** Scope drop-down: **Full Project** vs **Selection Only**
- [x] **3.7** Export CSV: `QFileDialog.getSaveFileName` → write `MaterialReport.to_csv()`
- [x] **3.8** Copy to Clipboard: `QApplication.clipboard().setText(report.to_plain_text())`
- [x] **3.9** Add **"Estimate Materials  Ctrl+E"** to the **Tools** menu

---

## Phase 4 — Smoke Tests

- [x] **4.1** Add ~12 estimator unit tests to `smoke_test.py`:
  - LumberSchedule.round_up edge cases
  - Post grid corner-always-included
  - Zero-area JoistFillItem → 0 joists
  - Joist count from known 120×96 in fill @ 16 in o.c.
  - Band board count and lengths
  - Blocking triggered at span > 96 in
  - Wall stud count with one door + one window
  - Header size selection by span
  - Concrete volume (known footing size)
  - Deck board count from known area
  - Plywood sheet count round-up
  - Full run on loaded .acad file → no crash

---

## Revert Instructions

To revert any file to pre-estimator state:

```powershell
cd F:\Free_apps\ArchCAD
Copy-Item canvas.bak.pre-estimator-20260603.py    canvas.py
Copy-Item mainwindow.bak.pre-estimator-20260603.py mainwindow.py
Copy-Item items.bak.pre-estimator-20260603.py      items.py
# Then delete estimator.py if it was created
Remove-Item estimator.py -ErrorAction SilentlyContinue
```

To revert to pre-code-compliance state (20260603b backups):

```powershell
cd F:\Free_apps\ArchCAD
Copy-Item canvas.bak.20260603b.py    canvas.py
Copy-Item mainwindow.bak.20260603b.py mainwindow.py
Copy-Item estimator.bak.20260603b.py  estimator.py
Copy-Item items.bak.20260603b.py      items.py
Copy-Item smoke_test.bak.20260603b.py smoke_test.py
Remove-Item code_tables.py -ErrorAction SilentlyContinue
```

---

## Phase 5 — New File: `code_tables.py`  *(Kentucky / IRC 2021 Code Data)*

> **Kentucky adopts IRC 2021.** All tables below are sourced from IRC 2021 / KBC.
> Default regional values: Ground snow = 20 psf, Frost depth = 24 in, Wind = 90 mph Exp B.

- [x] **5.1** `KY_DEFAULTS` dict — regional constants
  - `ground_snow_psf = 20`  (most of KY; adjustable)
  - `frost_depth_in  = 24`
  - `floor_live_psf  = 40`  (living areas, IRC R502.3.2)
  - `deck_live_psf   = 40`  (IRC R507)
  - `dead_load_psf   = 10`
  - `soil_bearing_psf = 1500` (conservative default)

- [x] **5.2** `DECK_JOIST_SPANS` — IRC Table R507.6 (Southern Pine #2, 40 psf LL)
  - `{size: {spacing_in: max_span_ft}}` for 2×6/8/10/12 @ 12/16/24" o.c.

- [x] **5.3** `FLOOR_JOIST_SPANS` — IRC Table R502.3.1(2) (SPF #2 + SYP #2, 40 psf LL)
  - Same structure as deck table

- [x] **5.4** `DECK_BEAM_SPANS` — IRC Table R507.5(1) (Southern Pine, 40 psf LL)
  - `{ply_size: {joist_span_ft: max_beam_span_ft}}`

- [x] **5.5** `RAFTER_SPANS` — IRC Table R802.4.1 (SPF #2, 20 psf snow, ceiling not attached)
  - `{size: {spacing_in: max_rafter_span_ft}}`

- [x] **5.6** `FOOTING_SIZES` — IRC Table R507.3.1 (1500 psf soil, 40 psf LL)
  - `{tributary_area_ft2: min_round_dia_in}`

- [x] **5.7** `POST_MAX_HEIGHTS` — IRC Table R507.4
  - `{size: max_height_ft}` e.g. `{'4x4': 8, '4x6': 10, '6x6': 14}`

- [x] **5.8** `HEADER_SIZES` — IRC R602.7 (load-bearing, 1-story)
  - `{max_span_in: size}` → `{48: '2x6', 72: '2x8', 96: '2x10', 120: '2x12'}`

- [x] **5.9** Lookup helper functions (all return strings or numbers):
  - `min_deck_joist(span_ft, spacing_in) → str`  e.g. `'2x10'`
  - `min_floor_joist(span_ft, spacing_in) → str`
  - `min_deck_beam(joist_span_ft, beam_span_ft) → str`
  - `min_rafter(span_ft, spacing_in) → str`
  - `min_footing_dia(trib_area_ft2) → int`  inches
  - `max_cantilever(joist_size) → float`  inches (= nominal depth)
  - `blocking_rows_required(span_in) → int`  0, 1, or 2 rows

---

## Phase 6 — Code Compliance Engine in `estimator.py`

- [x] **6.1** `CodeIssue` dataclass
  - `element: str`, `location: str`, `required: str`, `provided: str`
  - `severity: str`  — `'ERROR'` (code violation) | `'WARN'` (marginal) | `'OK'`
  - `auto_fixable: bool`  — True if auto-draw can resolve it

- [x] **6.2** `CodeReport` class
  - `issues: list[CodeIssue]`
  - `errors()`, `warnings()`, `ok_items()`
  - `to_csv()`, `to_plain_text()`

- [x] **6.3** `CodeChecker.run(scene_items, settings, ky_defaults) → CodeReport`
  - `_check_joists(fills)` — each JoistFillItem span vs `min_deck_joist()`
  - `_check_beams(fills)` — mid-span beam needed if joist span > table max; recommend size
  - `_check_posts(fills)` — post height vs `POST_MAX_HEIGHTS`; footing dia vs tributary area
  - `_check_footings(fills)` — diameter/depth ≥ frost + minimum per table
  - `_check_blocking(fills)` — rows present in scene vs `blocking_rows_required()`
  - `_check_rafters(rooms, walls)` — rafter span vs `min_rafter()`; overhang ≤ 24" for 2×4, ≤ L/4
  - `_check_cantilevers(fills)` — flag if any JoistFillItem cantilever > nominal joist depth
  - `_check_headers(walls, doors, windows)` — door/window widths vs current header size
  - `_check_bearing(joists, beams, posts)` — ≥ 1.5" bearing on wood, 3" on masonry

- [x] **6.4** Integrate `CodeChecker` into `MaterialEstimator.run()` — append a `'Code Compliance'` category to `MaterialReport` with one line per `CodeIssue`

---

## Phase 7 — Auto-Draw Missing Structural Elements

> When the user clicks **"Auto-Draw Missing"**, the app reads the `CodeReport` and
> draws missing elements directly onto the canvas using undo-able commands.

- [x] **7.1** `AutoDrawEngine.run(canvas, code_report, settings)`
  - Collects all `auto_fixable=True` issues into a single undo group (`_GroupCmd`)
  - Calls the appropriate `_draw_*` method for each issue type

- [x] **7.2** `_draw_blocking_row(canvas, joist_fill, row_y_in)`
  - Adds a `LineItem` spanning the full fill width at the computed row position
  - Labels it "Blocking" via item property
  - Layer: `'Structural'` (creates layer if missing)

- [x] **7.3** `_draw_beam(canvas, joist_fill, beam_x_in, beam_size)`
  - Adds a `WallItem`-like `BeamItem` (thick line) at mid-span perpendicular to joist run
  - Or reuses `WallItem` on a `'Beam'` layer with `beam_size` stored as property

- [x] **7.4** `_draw_posts(canvas, beam_item, post_spacing_ft)`
  - Adds `PostItem` objects at computed spacing along beam
  - Ensures corner posts always placed

- [x] **7.5** `_draw_rafters(canvas, room_outline, settings)`
  - Adds rafter `LineItem` objects spanning from plate line to ridge
  - Overhang length = `settings.rafter_overhang_in` (12–96 in) beyond outer wall
  - Ridge `LineItem` centred on room at peak height

- [x] **7.6** All auto-drawn items tagged with `auto_generated=True` property
  - Visible in Properties panel as "(auto)"
  - Deletable individually or via **Edit → Remove Auto-Generated**

---

## Phase 8 — UI Updates in `mainwindow.py`

- [x] **8.1** Add **Rafter Overhang** spinbox to Estimator dock (12 to 96 in, step 1, suffix `"`)
  - Stored in `canvas._est_rafter_overhang = 24`  (default 24")

- [x] **8.2** Add **Rafter Spacing** combo to Estimator dock (12 / 16 / 19.2 / 24 o.c.)

- [x] **8.3** Add **Kentucky Ground Snow** combo (20 / 25 / 30 psf — most KY = 20)

- [x] **8.4** Add **Soil Bearing** combo (1500 / 2000 / 3000 psf)

- [x] **8.5** Add **Run Code Check** button → calls `CodeChecker.run()` → populates compliance table

- [x] **8.6** Compliance `QTableWidget` columns: Element | Required | Provided | Status
  - Status cell background: green (OK) / yellow (WARN) / red (ERROR)

- [x] **8.7** **Auto-Draw Missing** button (enabled only if code report has `auto_fixable` issues)
  - Calls `AutoDrawEngine.run(canvas, code_report, settings)`
  - Shows modal progress (simple `QMessageBox` with count of items drawn)

- [x] **8.8** Category combo updated to include `'Code Compliance'`

- [x] **8.9** **Edit → Remove Auto-Generated** menu action
  - Removes all items with `auto_generated=True` from scene via undo command

---

## Phase 9 — Smoke Tests for Code Engine

- [x] **9.1** `code_tables.min_deck_joist` — known span → expected size
- [x] **9.2** `code_tables.min_footing_dia` — known tributary area → min dia
- [x] **9.3** `code_tables.blocking_rows_required` — short/medium/long spans
- [x] **9.4** `code_tables.max_cantilever` — 2×10 → 9.25 in, 2×12 → 11.25 in
- [x] **9.5** `CodeChecker` — joist span within table → OK
- [x] **9.6** `CodeChecker` — joist span exceeds table max → ERROR
- [x] **9.7** `CodeChecker` — footing too small for tributary area → ERROR
- [x] **9.8** `CodeChecker` — header undersized for opening → ERROR
- [x] **9.9** `CodeChecker` — correct blocking count → OK; missing blocking → WARN
- [x] **9.10** `AutoDrawEngine` — blocking drawn at correct Y coordinate
- [x] **9.11** `AutoDrawEngine` — rafter lines with correct overhang
- [x] **9.12** Full code-check on `james sheindel deck.acad` → no crash

---

