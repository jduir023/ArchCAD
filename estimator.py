"""
ArchCAD — Material Estimator
Calculates a full bill-of-materials from the canvas scene items.

Units throughout: inches (scene units).  Feet conversions are done only at
output time.  All public inputs in EstimatorSettings use feet or inches as
noted in the field docstring.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from typing import List, Optional

# ── Stock lumber lengths available for purchase ───────────────────────────────

_ALL_STOCK_FT = [8, 10, 12, 14, 16, 18, 20]


# ── Lumber schedule helper ────────────────────────────────────────────────────

class LumberSchedule:
    """Groups a list of required raw lengths into purchasable stock lengths."""

    def __init__(self, stock_lengths_ft: list[int] | None = None):
        self._stock = sorted(stock_lengths_ft or [8, 10, 12, 16])

    def round_up(self, raw_ft: float) -> int:
        """Return the smallest available stock length >= raw_ft."""
        for s in self._stock:
            if s >= raw_ft:
                return s
        return self._stock[-1]   # clamp to longest available

    def summarize(self, raw_lengths_ft: list[float]) -> dict[int, int]:
        """
        Given a list of required piece lengths (ft), return a dict mapping
        stock length → number of pieces needed.
        """
        counts: dict[int, int] = {}
        for raw in raw_lengths_ft:
            stock = self.round_up(raw)
            counts[stock] = counts.get(stock, 0) + 1
        return counts

    def total_linear_ft(self, summary: dict[int, int]) -> float:
        return sum(length * count for length, count in summary.items())


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class ReportLine:
    category: str
    description: str
    qty: float
    unit: str          # 'pcs', 'lf', 'sqft', 'bags', 'gal', 'rolls', 'each'
    notes: str = ''

    def qty_str(self) -> str:
        if self.unit in ('pcs', 'bags', 'rolls', 'each', 'sheets'):
            return str(int(math.ceil(self.qty)))
        return f'{self.qty:.1f}'


@dataclass
class MaterialReport:
    lines: list[ReportLine] = field(default_factory=list)

    def add(self, category: str, description: str, qty: float,
            unit: str, notes: str = ''):
        if qty > 0:
            self.lines.append(ReportLine(category, description, qty, unit, notes))

    def categories(self) -> list[str]:
        seen: list[str] = []
        for ln in self.lines:
            if ln.category not in seen:
                seen.append(ln.category)
        return seen

    def filtered(self, category: str | None = None) -> list[ReportLine]:
        if not category or category == 'All':
            return list(self.lines)
        return [ln for ln in self.lines if ln.category == category]

    def to_csv(self) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(['Category', 'Description', 'Qty', 'Unit', 'Notes'])
        for ln in self.lines:
            w.writerow([ln.category, ln.description,
                        ln.qty_str(), ln.unit, ln.notes])
        return buf.getvalue()

    def to_plain_text(self) -> str:
        lines = ['ArchCAD — Material Estimate', '=' * 48]
        cur_cat = ''
        for ln in self.lines:
            if ln.category != cur_cat:
                cur_cat = ln.category
                lines.append(f'\n{cur_cat}')
                lines.append('-' * len(cur_cat))
            lines.append(f'  {ln.description:<36}  {ln.qty_str():>6} {ln.unit}')
            if ln.notes:
                lines.append(f'    ↳ {ln.notes}')
        return '\n'.join(lines)


# ── Settings ──────────────────────────────────────────────────────────────────

@dataclass
class EstimatorSettings:
    # Post / substructure
    post_spacing_x_ft: float  = 8.0    # ft
    post_spacing_y_ft: float  = 8.0    # ft
    post_height_ft:    float  = 3.0    # ft (above grade)
    joist_size:        str    = '2x10'
    beam_size:         str    = '3x10'

    # Decking
    decking_type:      str    = 'deck_board'   # 'deck_board' | 'plywood'
    deck_board_width:  float  = 5.5            # actual inches (5/4×6 default)
    waste_pct:         float  = 10.0           # % overage

    # Wall / rail framing
    surface_mode:      str    = 'walls'   # 'walls' | 'rails'
    stud_spacing:      int    = 16        # inches o.c. (16 or 24)
    stud_size:         str    = '2x4'     # '2x4' | '2x6'
    plate_count:       int    = 2         # 1 or 2 top plates
    ceiling_ht_ft:     float  = 8.0       # ft

    # Roof
    roof_pitch:        int    = 4         # in/12
    rafter_spacing:    int    = 16        # inches o.c.
    rafter_overhang_ft: float = 1.5       # ft

    # Concrete / footings
    footing_dia_in:    int    = 12        # inches (tube form)
    footing_depth_in:  int    = 42        # inches

    # Toggles
    include_substructure: bool = True
    include_decking:     bool = True
    include_walls:       bool = True
    include_hardware:    bool = True
    include_concrete:    bool = True
    include_roof:        bool = False
    include_finish:      bool = False
    include_electrical:  bool = False
    include_drywall:     bool = True
    include_insulation:  bool = True
    include_flooring:    bool = True
    include_doors_windows: bool = True
    include_siding:      bool = True
    include_roofing:     bool = False
    include_trim:        bool = False
    include_plumbing:    bool = False
    include_hvac:        bool = False

    # Type selectors
    flooring_type:       str  = 'lvp'       # 'lvp' | 'tile' | 'carpet' | 'hardwood'
    siding_type:         str  = 'vinyl'     # 'vinyl' | 'hardie' | 'wood'
    roofing_type:        str  = 'shingles'  # 'shingles' | 'metal'
    ceiling_insul_r:     int  = 38          # R-value for ceiling (30/38/49)

    # Building sections — used when no items are drawn.
    # Each entry: {'label': str, 'width_ft': float, 'length_ft': float}
    # Falls back to building_width_ft / building_length_ft when list is empty.
    building_sections:   list  = field(default_factory=list)
    building_width_ft:   float = 20.0   # legacy / single-section fallback
    building_length_ft:  float = 30.0   # legacy / single-section fallback
    door_count:          int   = 2    # default doors synthesized when none drawn
    window_count:        int   = 4    # default windows synthesized when none drawn

    # Foundation
    foundation_type:     str   = 'posts'   # 'posts'|'footer_block'|'slab'|'concrete_wall'
    post_size:           str   = '4x4'     # '4x4' | '6x6'
    crawl_space_ht_in:   float = 30.0      # crawl space height for footer_block (in)

    # Building type — drives which calculations run
    building_type:       str   = 'building'  # 'building' | 'deck' | 'pole_barn'

    # Pole Barn specific (used when building_type == 'pole_barn')
    pb_col_size:         str   = '6x6'       # column timber size
    pb_col_spacing_ft:   float = 10.0        # column spacing along walls (ft)
    pb_col_embed_ft:     float = 4.0         # embed depth below grade (ft) — KY frost 24"
    pb_col_height_ft:    float = 12.0        # column height above grade (ft)
    pb_girt_spacing_in:  float = 48.0        # horizontal girt o.c. (in)
    pb_truss_spacing_ft: float = 4.0         # roof truss spacing (ft)
    pb_purlin_spacing_in: float = 24.0       # roof purlin o.c. (in)
    pb_roof_cladding:    str   = 'metal'     # 'metal' | 'shingles'
    pb_wall_cladding:    str   = 'metal'     # 'metal' | 'board_batten' | 'lp_smartside'
    pb_skirt_type:       str   = 'pt_skirt'  # 'pt_skirt' | 'grade_beam' | 'none'
    pb_floor_type:       str   = 'gravel'    # 'concrete' | 'gravel' | 'none'

    # Stock lengths
    stock_lengths_ft:  list[int] = field(default_factory=lambda: [8, 10, 12, 16])


# ── Header size by span ───────────────────────────────────────────────────────

def _header_size(opening_in: float) -> str:
    """Return nominal header lumber size for a given rough opening width."""
    ft = opening_in / 12
    if ft <= 4:  return '2x6'
    if ft <= 6:  return '2x8'
    if ft <= 8:  return '2x10'
    return '2x12'


# ── Main estimator ────────────────────────────────────────────────────────────

class MaterialEstimator:
    """
    Reads serialised canvas item dicts (same format as to_dict()) and
    an EstimatorSettings instance, returns a MaterialReport.
    """

    CAT_SUB    = 'Substructure'
    CAT_DECK   = 'Decking / Subfloor'
    CAT_WALL   = 'Wall / Rail Framing'
    CAT_CONC   = 'Concrete & Footings'
    CAT_HW     = 'Structural Hardware'
    CAT_ROOF   = 'Roof Framing'
    CAT_FIN    = 'Finish & Paint'
    CAT_ELEC   = 'Electrical (Rough)'
    CAT_DW     = 'Drywall & Finishing'
    CAT_INSUL  = 'Insulation'
    CAT_FLOOR  = 'Flooring'
    CAT_DWIN   = 'Doors & Windows'
    CAT_EXT    = 'Exterior Finish'
    CAT_ROOFING = 'Roofing Materials'
    CAT_TRIM   = 'Interior Trim'
    CAT_PLUMB  = 'Plumbing (Rough)'
    CAT_HVAC   = 'HVAC (Rough)'

    def run(self, scene_items: list[dict],
            settings: EstimatorSettings) -> MaterialReport:
        report  = MaterialReport()
        sched   = LumberSchedule(settings.stock_lengths_ft)
        btype   = settings.building_type
        is_deck = btype == 'deck'
        is_slab = settings.foundation_type == 'slab'

        # Per-trade switches.  Deck type drops interior/finish trades so they
        # cannot leak into a deck estimate even if a checkbox is still on.
        want_sub     = settings.include_substructure and not is_slab
        want_decking = settings.include_decking and not is_slab
        want_walls   = settings.include_walls
        want_conc    = settings.include_concrete
        want_hw      = settings.include_hardware
        want_roof    = settings.include_roof
        want_fin     = settings.include_finish
        want_elec    = settings.include_electrical and not is_deck
        want_dw      = settings.include_drywall and not is_deck
        want_insul   = settings.include_insulation and not is_deck
        want_floor   = settings.include_flooring and not is_deck
        want_dwin    = settings.include_doors_windows
        want_siding  = settings.include_siding and not is_deck
        want_roofing = settings.include_roofing
        want_trim    = settings.include_trim and not is_deck
        want_plumb   = settings.include_plumbing and not is_deck
        want_hvac    = settings.include_hvac and not is_deck

        # Partition items by type
        joistfills   = [d for d in scene_items if d.get('type') == 'joist_fill']
        posts_placed = [d for d in scene_items if d.get('type') == 'post']
        walls        = [d for d in scene_items if d.get('type') == 'wall']
        doors        = [d for d in scene_items if d.get('type') == 'door']
        windows      = [d for d in scene_items if d.get('type') == 'window']
        rooms        = [d for d in scene_items if d.get('type') == 'room']

        sections = settings.building_sections or [
            {'label': 'Main', 'width_ft': settings.building_width_ft,
             'length_ft': settings.building_length_ft}
        ]

        # ── Pole barn: separate calculation path (still honors trade flags) ──
        if btype == 'pole_barn':
            self._calc_pole_barn(report, sched, sections, settings)
            return report

        # Synthesize missing geometry only for trades that need it.
        if not rooms:
            y_offset = 0.0
            for sec in sections:
                w_in = sec['width_ft']  * 12
                l_in = sec['length_ft'] * 12
                rooms.append({'type': 'room', 'x': 0, 'y': y_offset,
                              'w': w_in, 'h': l_in,
                              'label': sec.get('label', 'building')})
                y_offset += l_in
        if not walls and (want_walls or want_siding or want_dw or want_insul
                          or want_fin or want_elec or want_roof):
            y_offset = 0.0
            for sec in sections:
                w_in = sec['width_ft']  * 12
                l_in = sec['length_ft'] * 12
                walls += [
                    {'type': 'wall', 'x1': 0,    'y1': y_offset,       'x2': w_in, 'y2': y_offset},
                    {'type': 'wall', 'x1': w_in, 'y1': y_offset,       'x2': w_in, 'y2': y_offset + l_in},
                    {'type': 'wall', 'x1': w_in, 'y1': y_offset + l_in,'x2': 0,    'y2': y_offset + l_in},
                    {'type': 'wall', 'x1': 0,    'y1': y_offset + l_in,'x2': 0,    'y2': y_offset},
                ]
                y_offset += l_in
        if not joistfills and (want_sub or want_decking or (want_hw and not is_slab)):
            y_offset = 0.0
            for sec in sections:
                w_in = sec['width_ft']  * 12
                l_in = sec['length_ft'] * 12
                joistfills.append({
                    'type': 'joist_fill', 'x': 0, 'y': y_offset,
                    'w': w_in, 'h': l_in,
                    'spacing': 16, 'direction': 'h',
                })
                y_offset += l_in
        # Phantom openings only when the door/window trade is on (so they
        # cannot inflate stud counts when that trade is isolated off).
        if not doors and want_dwin:
            doors = [{'type': 'door', 'x': 0, 'y': 0, 'width': 36, 'height': 80}
                     for _ in range(settings.door_count)]
        if not windows and want_dwin:
            windows = [{'type': 'window', 'x1': 0, 'y1': 0,
                        'x2': 36, 'y2': 0, 'height': 36}
                       for _ in range(settings.window_count)]

        if want_sub:
            self._calc_substructure(report, sched, joistfills, posts_placed, settings)
        if want_decking:
            self._calc_decking(report, sched, joistfills, settings)
        if want_walls:
            self._calc_walls(report, sched, walls, doors, windows, settings)
        if want_conc:
            post_count = (self._count_posts(joistfills, posts_placed, settings)
                          if settings.foundation_type == 'posts' else 0)
            self._calc_concrete(report, post_count, rooms, settings)
        if want_hw:
            post_count = (self._count_posts(joistfills, posts_placed, settings)
                          if settings.foundation_type == 'posts' else 0)
            self._calc_hardware(report, joistfills, post_count, settings)
        if want_roof:
            self._calc_roof(report, sched, rooms, settings)
        if want_fin:
            self._calc_finish(report, rooms, walls, settings)
        if want_elec:
            self._calc_electrical_stub(report, rooms, walls, doors, settings)
        if want_dw:
            self._calc_drywall(report, rooms, walls, doors, windows, settings)
        if want_insul:
            self._calc_insulation(report, rooms, walls, settings)
        if want_floor:
            self._calc_flooring(report, rooms, settings)
        if want_dwin:
            self._calc_doors_windows(report, doors, windows, settings)
        if want_siding:
            self._calc_siding(report, rooms, walls, doors, windows, settings)
        if want_roofing:
            self._calc_roofing(report, rooms, settings)
        if want_trim:
            self._calc_interior_trim(report, rooms, doors, windows, settings)
        if want_plumb:
            self._calc_plumbing_stub(report, rooms, settings)
        if want_hvac:
            self._calc_hvac_stub(report, rooms, settings)

        return report

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _waste(qty: float, pct: float) -> float:
        return qty * (1 + pct / 100)

    @staticmethod
    def _ft(inches: float) -> float:
        return inches / 12.0

    @staticmethod
    def _wall_len_ft(d: dict) -> float:
        x1 = d.get('x1', d.get('x', 0))
        y1 = d.get('y1', d.get('y', 0))
        x2 = d.get('x2', x1 + d.get('w', 0))
        y2 = d.get('y2', y1 + d.get('h', 0))
        return math.hypot(x2 - x1, y2 - y1) / 12.0

    @staticmethod
    def _joist_span_bay(jf: dict) -> tuple[float, float, float]:
        """Return (span_in, bay_in, spacing_in).

        direction='h' draws horizontal joist lines of length w, spaced along h.
        Span (joist length) is therefore w; bay (spacing axis) is h.
        """
        spacing = float(jf.get('spacing', 16) or 16)
        if jf.get('direction', 'h') == 'h':
            return float(jf['w']), float(jf['h']), spacing
        return float(jf['h']), float(jf['w']), spacing

    @staticmethod
    def _opening_wh(d: dict, default_w: float = 36.0,
                    default_h: float = 36.0) -> tuple[float, float]:
        """Plan-view opening (width_in, height_in) for a door or window dict."""
        if d.get('type') == 'door' or ('width' in d and 'x2' not in d):
            w = float(d.get('width', d.get('door_width', default_w)))
            h = float(d.get('height', d.get('door_height', 80)))
            return w, h
        dx = abs(d.get('x2', d.get('x', 0) + d.get('w', 0))
                 - d.get('x1', d.get('x', 0)))
        dy = abs(d.get('y2', d.get('y', 0) + d.get('h', 0))
                 - d.get('y1', d.get('y', 0)))
        length = math.hypot(dx, dy)
        if length < 1:
            length = float(d.get('width', d.get('w', default_w)))
        height = float(d.get('height', 0) or 0)
        if height < 1:
            height = default_h
            # Legacy square synth (x2-x1 == y2-y1) stored width on both axes.
            if abs(dx - dy) < 0.5 and dx > 1:
                length = dx
        return length, height

    def _count_posts(self, joistfills: list[dict],
                     posts_placed: list[dict],
                     settings: EstimatorSettings) -> int:
        """Total post count: grid-derived + explicitly placed."""
        grid_posts: set[tuple] = set()
        sp_x = settings.post_spacing_x_ft * 12
        sp_y = settings.post_spacing_y_ft * 12
        for jf in joistfills:
            w, h = jf['w'], jf['h']
            xs = self._grid_positions(w, sp_x)
            ys = self._grid_positions(h, sp_y)
            ox, oy = jf.get('x', 0), jf.get('y', 0)
            for x in xs:
                for y in ys:
                    grid_posts.add((round(ox + x), round(oy + y)))
        return len(grid_posts) + len(posts_placed)

    @staticmethod
    def _grid_positions(span: float, spacing: float) -> list[float]:
        """
        Grid lines at 0, spacing, 2×spacing … capped at span.
        The final value is always exactly span so corners are guaranteed.
        """
        if spacing <= 0:
            spacing = 96
        positions = [0.0]
        cur = spacing
        while cur < span - 0.1:
            positions.append(cur)
            cur += spacing
        if not positions or abs(positions[-1] - span) > 0.1:
            positions.append(span)
        return positions

    @staticmethod
    def _add_lumber_summary(report: MaterialReport, sched: LumberSchedule,
                            category: str, size: str,
                            lengths_ft: list[float], note: str = ''):
        summary = sched.summarize(lengths_ft)
        for stock_len, count in sorted(summary.items()):
            report.add(category, f'{size} × {stock_len}\' lumber',
                       count, 'pcs',
                       note or f'{count} pcs @ {stock_len} ft')

    # ── Phase 1.5 — Substructure ──────────────────────────────────────────────

    def _calc_substructure(self, report: MaterialReport,
                           sched: LumberSchedule,
                           joistfills: list[dict],
                           posts_placed: list[dict],
                           settings: EstimatorSettings):

        joist_size = settings.joist_size
        sp_x = settings.post_spacing_x_ft * 12
        sp_y = settings.post_spacing_y_ft * 12
        post_ht_ft = settings.post_height_ft

        all_joist_lengths: list[float] = []
        all_band_lengths:  list[float] = []
        all_block_lengths: list[float] = []
        total_post_count = 0

        from code_tables import blocking_rows_required

        for jf in joistfills:
            w = jf['w']   # scene inches
            h = jf['h']
            joist_span_in, bay_in, spacing = self._joist_span_bay(jf)
            num_spaces   = bay_in / spacing
            num_interior = max(0, int(num_spaces) - 1)
            # Band / rim: 2 along the bay (parallel to joists) + 2 headers
            band_len1_in = bay_in
            band_len2_in = joist_span_in

            # Interior joists
            for _ in range(num_interior):
                all_joist_lengths.append(self._ft(joist_span_in))

            # Band / rim boards: 2 parallel to joist run + 2 headers
            all_band_lengths.append(self._ft(band_len1_in))   # rim side 1
            all_band_lengths.append(self._ft(band_len1_in))   # rim side 2
            all_band_lengths.append(self._ft(band_len2_in))   # header end 1
            all_band_lengths.append(self._ft(band_len2_in))   # header end 2

            # Blocking rows per IRC practice; pieces fill every joist bay
            # including the gaps to the rim boards (interior + 1).
            rows = blocking_rows_required(joist_span_in)
            if rows > 0:
                num_blocks = num_interior + 1
                block_len_in = max(spacing - 1.5, 1.0)
                for _ in range(rows * num_blocks):
                    all_block_lengths.append(self._ft(block_len_in))

            # Post grid for this fill region
            xs = self._grid_positions(w, sp_x)
            ys = self._grid_positions(h, sp_y)
            total_post_count += len(xs) * len(ys)

        # Add explicitly placed PostItems
        total_post_count += len(posts_placed)

        # Post lumber: height + 6 in min below grade (footing)
        post_len_ft = post_ht_ft + 0.5   # 6 in below grade
        post_size = settings.post_size   # '4x4' or '6x6'

        # Apply waste factor to counts
        waste = settings.waste_pct
        joist_lengths_w = [l for l in all_joist_lengths
                           for _ in range(1)]  # waste handled by rounding
        joist_count_w = int(math.ceil(len(all_joist_lengths) * (1 + waste / 100)))
        band_count_w  = int(math.ceil(len(all_band_lengths)  * (1 + waste / 100)))
        block_count_w = int(math.ceil(len(all_block_lengths) * (1 + waste / 100)))

        if all_joist_lengths:
            summary = sched.summarize(all_joist_lengths)
            # Apply waste by inflating counts
            for stock_len, count in sorted(summary.items()):
                adj = int(math.ceil(count * (1 + waste / 100)))
                report.add(self.CAT_SUB,
                            f'{joist_size} joist × {stock_len}\'',
                            adj, 'pcs',
                            f'{adj} pcs @ {stock_len} ft  (+{waste:.0f}% waste)')

        if all_band_lengths:
            summary = sched.summarize(all_band_lengths)
            for stock_len, count in sorted(summary.items()):
                adj = int(math.ceil(count * (1 + waste / 100)))
                report.add(self.CAT_SUB,
                            f'{joist_size} band/rim board × {stock_len}\'',
                            adj, 'pcs',
                            f'Perimeter + headers (+{waste:.0f}% waste)')

        if all_block_lengths:
            summary = sched.summarize(all_block_lengths)
            for stock_len, count in sorted(summary.items()):
                adj = int(math.ceil(count * (1 + waste / 100)))
                report.add(self.CAT_SUB,
                            f'{joist_size} blocking × {stock_len}\'',
                            adj, 'pcs', 'Mid-span blocking rows')

        if total_post_count > 0:
            post_stock = sched.round_up(post_len_ft)
            report.add(self.CAT_SUB, f'{post_size} post × {post_stock}\'',
                       total_post_count, 'pcs',
                       f'{total_post_count} posts × {post_stock} ft stock')

    # ── Phase 1.6 — Decking / Subfloor ───────────────────────────────────────

    def _calc_decking(self, report: MaterialReport,
                      sched: LumberSchedule,
                      joistfills: list[dict],
                      settings: EstimatorSettings):
        total_area_sqft = 0.0
        for jf in joistfills:
            total_area_sqft += self._ft(jf['w']) * self._ft(jf['h'])

        if total_area_sqft <= 0:
            return

        area_w = self._waste(total_area_sqft, settings.waste_pct)
        waste  = settings.waste_pct

        if settings.decking_type == 'plywood':
            sheets = math.ceil(area_w / 32.0)
            report.add(self.CAT_DECK, '4×8 Plywood / OSB subfloor sheet',
                       sheets, 'sheets',
                       f'{total_area_sqft:.0f} sqft + {waste:.0f}% waste')
            # Adhesive: 1 tube per 4 sheets
            adhesive = math.ceil(sheets / 4)
            report.add(self.CAT_DECK, 'Construction adhesive (28 oz tube)',
                       adhesive, 'each', '1 tube per 4 sheets')
            # Screws: ~40 per sheet (perimeter 6" + field 12")
            screws = sheets * 40
            report.add(self.CAT_DECK, '1-5/8" coarse-thread subfloor screws',
                       math.ceil(screws / 100) * 100, 'each',
                       '~40 per sheet, rounded to nearest 100')
        else:
            # Deck boards
            bw_ft = settings.deck_board_width / 12
            if bw_ft <= 0:
                bw_ft = 5.5 / 12
            linear_ft_needed = area_w / bw_ft
            # Assume one stock board length runs full span; pick dominant span
            dominant_span_ft = 16
            if joistfills:
                jf = joistfills[0]
                sp = jf.get('spacing', 16)
                dominant_span_ft = sched.round_up(
                    self._ft(jf['w'] if jf.get('direction', 'h') == 'v' else jf['h']))
            boards = math.ceil(linear_ft_needed / dominant_span_ft)
            report.add(self.CAT_DECK,
                       f'Deck board ({settings.deck_board_width:.1f}" wide)'
                       f' × {dominant_span_ft}\'',
                       boards, 'pcs',
                       f'{linear_ft_needed:.0f} lf needed (+{waste:.0f}% waste)')
            # Screws: 2 per board per joist crossing (rims + interior)
            total_joists = 0
            for jf in joistfills:
                _span, bay, sp = self._joist_span_bay(jf)
                total_joists += max(0, int(bay / sp) - 1) + 2
            screws = boards * max(total_joists, 1) * 2
            report.add(self.CAT_DECK, '3" deck screws (exterior)',
                       math.ceil(screws / 50) * 50, 'each',
                       '2 per joist per board, rounded to nearest 50')

        report.add(self.CAT_DECK, 'Total deck area', total_area_sqft, 'sqft',
                   'Before waste factor')

    # ── Phase 1.7 — Wall / Rail Framing ──────────────────────────────────────

    def _calc_walls(self, report: MaterialReport,
                    sched: LumberSchedule,
                    walls: list[dict],
                    doors: list[dict],
                    windows: list[dict],
                    settings: EstimatorSettings):

        if not walls:
            return

        waste  = settings.waste_pct
        mode   = settings.surface_mode
        ss     = settings.stud_spacing   # inches
        sz     = settings.stud_size
        ht_ft  = settings.ceiling_ht_ft
        pc     = settings.plate_count

        total_lf = sum(self._wall_len_ft(w) for w in walls)

        if mode == 'rails':
            # ── Rail mode ────────────────────────────────────────────────────
            rail_lf = total_lf
            report.add(self.CAT_WALL, f'{sz} top rail', rail_lf, 'lf', 'Linear ft of railing')
            report.add(self.CAT_WALL, f'{sz} bottom rail', rail_lf, 'lf')
            # Balusters at 4" spacing (code minimum): 1 per 4 in
            balusters = math.ceil(rail_lf * 12 / 4)
            report.add(self.CAT_WALL, 'Baluster (1.5"×1.5" typical)',
                       balusters, 'pcs', '4" o.c. spacing (code minimum)')
            # Rail posts every 6 ft + corners
            corners = len(walls)   # rough: 1 corner per wall segment end
            rail_posts = math.ceil(rail_lf / 6) + corners
            report.add(self.CAT_WALL, f'{sz} rail post',
                       rail_posts, 'pcs', '6 ft spacing + corners')
            return

        # ── Wall framing mode ─────────────────────────────────────────────────
        # Bottom plate
        bp_lengths = [self._wall_len_ft(w) for w in walls]
        bp_summary = sched.summarize(bp_lengths)
        for stock, count in sorted(bp_summary.items()):
            adj = int(math.ceil(count * (1 + waste / 100)))
            report.add(self.CAT_WALL, f'{sz} bottom plate × {stock}\'',
                       adj, 'pcs', f'Bottom plate (+{waste:.0f}% waste)')

        # Top plate(s) — plate_count is number of TOP plates (1 or 2)
        for p in range(pc):
            tp_summary = sched.summarize(bp_lengths)
            for stock, count in sorted(tp_summary.items()):
                adj = int(math.ceil(count * (1 + waste / 100)))
                lbl = 'top plate' if (pc == 1 or p == 0) else 'cap plate'
                report.add(self.CAT_WALL, f'{sz} {lbl} × {stock}\'',
                           adj, 'pcs')

        # Stud cut: ceiling height minus bottom plate + top plate(s)
        n_plates = 1 + max(1, pc)
        stud_cut_ft = ht_ft - (n_plates * 1.5 / 12)
        stud_stock  = sched.round_up(stud_cut_ft)

        total_studs = 0
        for w in walls:
            lf = self._wall_len_ft(w)
            total_studs += int(lf * 12 / ss) + 1   # field studs including ends

        # 3-stud corners: one extra stud per wall-to-wall corner
        corners_est = max(0, len(walls) - 1)
        total_studs += corners_est

        # Openings: kings/jacks/cripples replace the field studs in the RO,
        # so add the net extras only (not a full extra 4–6 on top of field).
        # Door: 2 king + 2 jack  → net +3 (one field stud already in the opening)
        # Window: 2 king + 2 jack + sill cripples ≈ +4 net
        total_studs += len(doors) * 3
        total_studs += len(windows) * 4

        adj_studs = int(math.ceil(total_studs * (1 + waste / 100)))
        report.add(self.CAT_WALL, f'{sz} stud × {stud_stock}\'',
                   adj_studs, 'pcs',
                   f'Field + corners + opening trimmers (+{waste:.0f}% waste)')

        # Headers (doubled)
        for d in doors:
            opening_in, _ = self._opening_wh(d, default_h=80)
            size = _header_size(opening_in)
            hdr_ft = self._ft(opening_in) + 0.5
            stock  = sched.round_up(hdr_ft)
            report.add(self.CAT_WALL, f'{size} header × {stock}\' (door)',
                       2, 'pcs',
                       f'{int(opening_in)}" opening → doubled {size}')

        for wn in windows:
            opening_in, _ = self._opening_wh(wn)
            size = _header_size(opening_in)
            hdr_ft = self._ft(opening_in) + 0.5
            stock  = sched.round_up(hdr_ft)
            report.add(self.CAT_WALL, f'{size} header × {stock}\' (window)',
                       2, 'pcs',
                       f'{int(opening_in)}" opening → doubled {size}')

        # Structural wall sheathing stays with framing
        wall_area_sqft = total_lf * ht_ft
        sheathing_sheets = math.ceil(self._waste(wall_area_sqft, waste) / 32)
        report.add(self.CAT_WALL, '7/16" OSB wall sheathing (4×8 sheet)',
                   sheathing_sheets, 'sheets',
                   f'{wall_area_sqft:.0f} sqft wall area + {waste:.0f}% waste')

        wall_screws = adj_studs * 6
        report.add(self.CAT_WALL, '3" framing screws / 16d sinkers',
                   math.ceil(wall_screws / 50) * 50, 'each',
                   '~6 per stud for plate connections')

    # ── Phase 1.8 — Concrete & Footings (all foundation types) ──────────────

    def _calc_concrete(self, report: MaterialReport,
                       post_count: int,
                       rooms: list[dict],
                       settings: EstimatorSettings):
        ftype     = settings.foundation_type
        depth_ft  = settings.footing_depth_in / 12   # frost / footing depth

        if ftype == 'posts':
            # ── Helical / tube-form post footings ────────────────────────────
            if post_count <= 0:
                return
            dia_ft = settings.footing_dia_in / 12

            tube_sections = math.ceil(depth_ft / 4) * post_count
            report.add(self.CAT_CONC,
                       f'{settings.footing_dia_in}" dia. Sonotube tube form (4 ft section)',
                       tube_sections, 'each',
                       f'{post_count} posts × {depth_ft:.1f} ft depth')

            vol_cuft_each = math.pi * (dia_ft / 2) ** 2 * depth_ft
            total_cuft    = vol_cuft_each * post_count
            bags_80 = math.ceil(total_cuft / 0.60)
            report.add(self.CAT_CONC, '80 lb concrete bags',
                       bags_80, 'bags',
                       f'{total_cuft:.1f} cu ft total  ({post_count} footings)')
            report.add(self.CAT_CONC, 'Total concrete volume',
                       round(total_cuft / 27, 2), 'cu yd',
                       'Reference — order by bag or ready-mix')

            rebar_len_ft = (depth_ft + 1) * 2 * post_count
            report.add(self.CAT_CONC, '#4 rebar (10 ft lengths)',
                       math.ceil(rebar_len_ft / 10), 'each',
                       f'{rebar_len_ft:.0f} lf total, 2 per footing')

            base_model = 'Simpson ABA44' if settings.post_size == '4x4' else 'Simpson CB66'
            report.add(self.CAT_CONC, f'{base_model} post base', post_count, 'each')
            report.add(self.CAT_CONC, '1/2" J-bolt anchor (set in wet concrete)',
                       post_count, 'each')

        else:
            # ── Building footprint from rooms ─────────────────────────────────
            xs = [r['x'] for r in rooms] + [r['x'] + r['w'] for r in rooms]
            ys = [r['y'] for r in rooms] + [r['y'] + r['h'] for r in rooms]
            w_ft      = self._ft(max(xs) - min(xs))
            l_ft      = self._ft(max(ys) - min(ys))
            perim_ft  = 2 * (w_ft + l_ft)
            area_sqft = w_ft * l_ft

            if ftype == 'footer_block':
                # ── Continuous footing + CMU block stem wall ──────────────────
                # Footing: 16" wide × 8" deep continuous strip
                ftg_cuft = perim_ft * (16/12) * (8/12)
                ftg_bags = math.ceil(ftg_cuft / 0.60)
                report.add(self.CAT_CONC, 'Footing concrete 80 lb bags',
                           ftg_bags, 'bags',
                           f'{perim_ft:.0f} lf × 16"w × 8"d = {ftg_cuft:.1f} cu ft')
                report.add(self.CAT_CONC, 'Footing concrete (ready-mix reference)',
                           round(ftg_cuft / 27, 2), 'cu yd')

                # Rebar in footing: 2 × #4 continuous
                report.add(self.CAT_CONC, '#4 rebar for footing (10 ft length)',
                           math.ceil(perim_ft * 2 / 10), 'each',
                           f'2 bars × {perim_ft:.0f} lf continuous footing')

                # CMU blocks: 8×8×16 nominal
                crawl_ht_ft    = settings.crawl_space_ht_in / 12
                blocks_per_row = perim_ft / (16/12)      # 16" long block
                courses        = math.ceil(crawl_ht_ft / (8/12))   # 8" tall
                total_blocks   = math.ceil(blocks_per_row * courses * 1.05)  # +5% waste
                report.add(self.CAT_CONC, '8×8×16 CMU concrete block',
                           total_blocks, 'each',
                           f'{courses} courses × {perim_ft:.0f} lf perimeter')

                # Mortar: 1 bag (60 lb) per 25 blocks
                mortar_bags = math.ceil(total_blocks / 25)
                report.add(self.CAT_CONC, 'Type S mortar mix (60 lb bag)',
                           mortar_bags, 'bags', '1 bag per ~25 blocks')

                # Rebar vertical in CMU cores: #4 every 32" (IRC minimum)
                vert_bars   = math.ceil(perim_ft * 12 / 32)
                bar_len_ft  = crawl_ht_ft + 1.5   # extends into footing
                report.add(self.CAT_CONC, '#4 rebar vertical in CMU cores (10 ft)',
                           math.ceil(vert_bars * bar_len_ft / 10), 'each',
                           f'{vert_bars} cores × {bar_len_ft:.1f} ft each  (32" o.c.)')

                # Anchor bolts: IRC R403.1.6 — every 6 ft + corners
                anchor_bolts = math.ceil(perim_ft / 6) + 4
                report.add(self.CAT_CONC, '1/2"×10" J-bolt anchor',
                           anchor_bolts, 'each',
                           f'Every 6 ft + 4 corners  ({perim_ft:.0f} lf)')

                # PT mudsill + sill gasket
                report.add(self.CAT_CONC, 'PT 2×6 mudsill (16 ft length)',
                           math.ceil(perim_ft / 16), 'each',
                           f'{perim_ft:.0f} lf perimeter')
                report.add(self.CAT_CONC, 'Sill gasket / foam seal (50 ft roll)',
                           math.ceil(perim_ft / 50), 'each')

                # Foundation vents: IRC R408 — 1 sqft per 150 sqft crawl space
                vents = max(2, math.ceil(area_sqft / 150))
                report.add(self.CAT_CONC, 'Foundation crawl space vent',
                           vents, 'each',
                           f'IRC R408: 1 per 150 sqft ({area_sqft:.0f} sqft crawl area)')

                # Dampproofing: exterior CMU face
                damp_area = perim_ft * crawl_ht_ft
                report.add(self.CAT_CONC, 'CMU block sealer / dampproofing (1 gal)',
                           max(1, math.ceil(damp_area / 100)), 'gal',
                           f'{damp_area:.0f} sqft exterior face')

            elif ftype == 'slab':
                # ── Concrete pad on grade ─────────────────────────────────────
                slab_cuft = area_sqft * (4/12)   # 4" residential slab
                slab_cuyd = slab_cuft / 27
                bags_80   = math.ceil(slab_cuft / 0.60)
                report.add(self.CAT_CONC, 'Concrete slab (ready-mix)',
                           round(slab_cuyd, 2), 'cu yd',
                           f'{area_sqft:.0f} sqft × 4" thick = {slab_cuft:.1f} cu ft')
                report.add(self.CAT_CONC, '80 lb concrete bags (if self-mix)',
                           bags_80, 'bags', 'Alternative to ready-mix')

                # Compacted gravel base: 4" deep
                gravel_cuyd = area_sqft * (4/12) / 27
                report.add(self.CAT_CONC, 'Compacted gravel base 4" (cu yd)',
                           round(gravel_cuyd, 2), 'cu yd',
                           f'{area_sqft:.0f} sqft footprint')

                # Vapor barrier under slab
                vb_rolls = math.ceil(area_sqft / 1000)
                report.add(self.CAT_CONC, '6-mil poly vapor barrier (1000 sqft roll)',
                           max(1, vb_rolls), 'rolls', 'Under slab moisture retarder')

                # Rebar grid: #4 at 18" o.c. both ways (IRC R506.3)
                lf_long  = (w_ft / 1.5 + 1) * l_ft
                lf_short = (l_ft / 1.5 + 1) * w_ft
                total_rebar_lf = lf_long + lf_short
                report.add(self.CAT_CONC, '#4 rebar slab grid 18" o.c. (10 ft)',
                           math.ceil(total_rebar_lf / 10), 'each',
                           f'{total_rebar_lf:.0f} lf total grid  (IRC R506.3)')

                # Wire mesh (alternative)
                report.add(self.CAT_CONC, '6×6 W1.4 wire mesh (100 sqft roll)',
                           math.ceil(area_sqft / 100), 'rolls',
                           'Alternative to rebar grid')

                # Form boards: 2×8 around perimeter
                report.add(self.CAT_CONC, '2×8 form board (16 ft length)',
                           math.ceil(perim_ft / 16), 'each',
                           f'{perim_ft:.0f} lf perimeter forms')

                # Fiber reinforcement
                report.add(self.CAT_CONC, 'Fiber mesh additive (1.5 lb / cu yd)',
                           math.ceil(slab_cuyd * 1.5), 'lbs',
                           'Mix into concrete — reduces shrinkage cracking')

                # Anchor bolts: every 6 ft (IRC R403.1.6)
                anchor_bolts = math.ceil(perim_ft / 6) + 4
                report.add(self.CAT_CONC, '1/2"×10" anchor bolt (embedded in slab)',
                           anchor_bolts, 'each',
                           f'Every 6 ft + corners  ({perim_ft:.0f} lf)')

                # PT mudsill + sill gasket
                report.add(self.CAT_CONC, 'PT 2×6 mudsill (16 ft length)',
                           math.ceil(perim_ft / 16), 'each',
                           f'{perim_ft:.0f} lf perimeter')
                report.add(self.CAT_CONC, 'Sill gasket / foam seal (50 ft roll)',
                           math.ceil(perim_ft / 50), 'each')

                # Control joints: every 10 ft grid
                cj_lf = (math.ceil(w_ft / 10) * l_ft) + (math.ceil(l_ft / 10) * w_ft)
                report.add(self.CAT_CONC, 'Control joint — saw-cut or tooled (lf)',
                           math.ceil(cj_lf), 'lf',
                           '10 ft grid spacing prevents random cracking')

            elif ftype == 'concrete_wall':
                # ── Poured concrete foundation walls ─────────────────────────
                wall_ht_ft = depth_ft + 0.67   # frost depth + 8" above grade
                # Footing: 16" wide × 8" deep strip
                ftg_cuft  = perim_ft * (16/12) * (8/12)
                # Wall: 8" thick × wall_ht_ft tall
                wall_cuft = perim_ft * (8/12) * wall_ht_ft
                total_cuft = ftg_cuft + wall_cuft
                total_cuyd = total_cuft / 27
                bags_80    = math.ceil(total_cuft / 0.60)

                report.add(self.CAT_CONC, 'Concrete — footing + walls (ready-mix)',
                           round(total_cuyd, 2), 'cu yd',
                           f'Ftg {ftg_cuft:.1f} + walls {wall_cuft:.1f} = {total_cuft:.1f} cu ft')
                report.add(self.CAT_CONC, '80 lb concrete bags (if self-mix)',
                           bags_80, 'bags', 'Alternative to ready-mix')

                # Rebar in footing: 2 × #4 continuous
                report.add(self.CAT_CONC, '#4 rebar in footing (10 ft)',
                           math.ceil(perim_ft * 2 / 10), 'each',
                           f'2 continuous bars × {perim_ft:.0f} lf')

                # Vertical rebar: #5 every 24" (IRC R404.1)
                vert_count  = math.ceil(perim_ft * 12 / 24)
                vert_len_ft = wall_ht_ft + 1.5   # extends into footing
                report.add(self.CAT_CONC, '#5 rebar vertical in walls (10 ft)',
                           math.ceil(vert_count * vert_len_ft / 10), 'each',
                           f'{vert_count} bars × {vert_len_ft:.1f} ft  (24" o.c. IRC R404.1)')

                # Horizontal rebar: #4 every 24"
                horiz_rows = math.ceil(wall_ht_ft / 2)
                report.add(self.CAT_CONC, '#4 rebar horizontal in walls (10 ft)',
                           math.ceil(horiz_rows * perim_ft / 10), 'each',
                           f'{horiz_rows} rows every 24" × {perim_ft:.0f} lf')

                # Form panels (rental): both faces of wall
                form_sqft = perim_ft * wall_ht_ft * 2
                report.add(self.CAT_CONC, 'Concrete form panel — rental (sqft)',
                           math.ceil(form_sqft), 'sqft',
                           f'{perim_ft:.0f} lf × {wall_ht_ft:.1f} ft × 2 faces')
                report.add(self.CAT_CONC, 'Snap tie (1 per 2 sqft of form)',
                           math.ceil(form_sqft / 2), 'each')
                report.add(self.CAT_CONC, 'Form release agent (1 gal per 400 sqft)',
                           max(1, math.ceil(form_sqft / 400)), 'gal')

                # Anchor bolts: every 6 ft (IRC R403.1.6)
                anchor_bolts = math.ceil(perim_ft / 6) + 4
                report.add(self.CAT_CONC, '1/2"×10" anchor bolt (embedded in wall)',
                           anchor_bolts, 'each',
                           f'Every 6 ft + corners  ({perim_ft:.0f} lf)')

                # PT mudsill + sill gasket
                report.add(self.CAT_CONC, 'PT 2×6 mudsill (16 ft length)',
                           math.ceil(perim_ft / 16), 'each',
                           f'{perim_ft:.0f} lf perimeter')
                report.add(self.CAT_CONC, 'Sill gasket / foam seal (50 ft roll)',
                           math.ceil(perim_ft / 50), 'each')

                # Dampproofing: exterior wall face
                damp_area = perim_ft * wall_ht_ft
                report.add(self.CAT_CONC, 'Dampproofing / waterproofing (1 gal)',
                           max(1, math.ceil(damp_area / 100)), 'gal',
                           f'{damp_area:.0f} sqft exterior wall face')

                # Perimeter drain tile
                report.add(self.CAT_CONC, 'Perforated drain pipe (10 ft length)',
                           math.ceil(perim_ft / 10), 'each',
                           f'Perimeter drain  ({perim_ft:.0f} lf)')
                report.add(self.CAT_CONC, 'Drainage gravel 3/4" stone (cu yd)',
                           max(1, math.ceil(perim_ft * 0.5 / 27)), 'cu yd',
                           'Around perimeter drain tile')


    # ── Phase 1.9 — Structural Hardware ──────────────────────────────────────

    def _calc_hardware(self, report: MaterialReport,
                       joistfills: list[dict],
                       post_count: int,
                       settings: EstimatorSettings):

        total_interior_joists = 0
        for jf in joistfills:
            _span, bay, sp = self._joist_span_bay(jf)
            total_interior_joists += max(0, int(bay / sp) - 1)

        if total_interior_joists > 0:
            # Joist hangers: 2 per interior joist (both ends)
            report.add(self.CAT_HW,
                       'Joist hanger (Simpson LUS210 or LU)',
                       total_interior_joists * 2, 'each',
                       '2 per interior joist')
            # Hurricane ties: 2 per joist
            report.add(self.CAT_HW,
                       'Hurricane tie (Simpson H2.5A)',
                       total_interior_joists * 2, 'each',
                       '1 per joist end × 2 ends')
            # Structural screws for rim/joist connection: 3 per end
            report.add(self.CAT_HW,
                       '1-1/2" joist hanger nails / screws (1 lb box)',
                       math.ceil(total_interior_joists * 2 * 8 / 50), 'each',
                       '~8 nails per hanger, 50 per box')

        if post_count > 0:
            # Post caps: 1 per post
            report.add(self.CAT_HW,
                       'Simpson BC post cap (beam-to-post)',
                       post_count, 'each')
            # Lag screws for ledger (if any joistfills exist)
            if joistfills:
                longest_edge = max(
                    max(jf['w'], jf['h']) for jf in joistfills)
                lag_count = math.ceil(self._ft(longest_edge) * 12 / 16)
                report.add(self.CAT_HW,
                           '1/2"×3.5" ledger lag bolt',
                           lag_count, 'each',
                           'Every 16 in along ledger')

    # ── Phase 1.10 — Roof Framing ─────────────────────────────────────────────

    def _calc_roof(self, report: MaterialReport,
                   sched: LumberSchedule,
                   rooms: list[dict],
                   settings: EstimatorSettings):
        if not rooms:
            return

        pitch      = settings.roof_pitch
        ov_ft      = settings.rafter_overhang_ft
        r_sp       = settings.rafter_spacing
        waste      = settings.waste_pct

        # Use bounding box of all rooms
        xs = [r['x'] for r in rooms] + [r['x'] + r['w'] for r in rooms]
        ys = [r['y'] for r in rooms] + [r['y'] + r['h'] for r in rooms]
        bldg_w_ft = self._ft(max(xs) - min(xs))
        bldg_l_ft = self._ft(max(ys) - min(ys))

        run_ft = bldg_w_ft / 2
        rafter_len_ft = run_ft * math.sqrt(1 + (pitch / 12) ** 2) + ov_ft
        rafter_stock  = sched.round_up(rafter_len_ft)
        rafter_count  = (math.floor(bldg_l_ft * 12 / r_sp) + 1) * 2  # both sides

        adj_rafters = int(math.ceil(rafter_count * (1 + waste / 100)))
        report.add(self.CAT_ROOF, f'2x{8 if pitch <= 4 else 10} rafter × {rafter_stock}\'',
                   adj_rafters, 'pcs',
                   f'{rafter_count} rafters × {rafter_stock} ft (+{waste:.0f}% waste)')

        # Ridge board
        ridge_ft = bldg_l_ft + 2 * ov_ft
        ridge_stock = sched.round_up(ridge_ft)
        report.add(self.CAT_ROOF, f'2x{8 if pitch <= 4 else 10} ridge board × {ridge_stock}\'',
                   1, 'pcs')

        # Collar ties: every other rafter pair
        collar_count = math.ceil(rafter_count / 2 / 2)
        collar_len_ft = bldg_w_ft * 0.33   # ~1/3 width up the roof
        collar_stock = sched.round_up(collar_len_ft)
        report.add(self.CAT_ROOF, f'2x4 collar tie × {collar_stock}\'',
                   collar_count, 'pcs', 'Every other rafter pair')

        # Roof sheathing
        roof_area = rafter_len_ft * bldg_l_ft * 2
        sheets = math.ceil(self._waste(roof_area, waste) / 32)
        report.add(self.CAT_ROOF, '7/16" OSB roof sheathing (4×8 sheet)',
                   sheets, 'sheets',
                   f'{roof_area:.0f} sqft roof area + {waste:.0f}% waste')
        # Underlayment, drip edge, and shingles belong to the Roofing trade.

    # ── Phase 1.11 — Finish & Paint ───────────────────────────────────────────

    def _calc_finish(self, report: MaterialReport,
                     rooms: list[dict],
                     walls: list[dict],
                     settings: EstimatorSettings):
        ht = settings.ceiling_ht_ft
        wall_lf    = sum(self._wall_len_ft(w) for w in walls)
        wall_area  = wall_lf * ht
        floor_area = sum(self._ft(r['w']) * self._ft(r['h']) for r in rooms)
        is_deck    = (settings.building_type == 'deck'
                      or settings.surface_mode == 'rails')

        if is_deck:
            if floor_area > 0:
                report.add(self.CAT_FIN, 'Deck stain / sealer (1 gal)',
                           math.ceil(floor_area / 200), 'gal',
                           '200 sqft/gal coverage')
            return

        if wall_area > 0:
            report.add(self.CAT_FIN, 'Exterior paint / stain (1 gal)',
                       math.ceil(wall_area / 350 * 2), 'gal',
                       '2 coats, 350 sqft/gal coverage')
            report.add(self.CAT_FIN, 'Exterior primer (1 gal)',
                       math.ceil(wall_area / 400), 'gal')
            report.add(self.CAT_FIN, 'Interior wall paint (1 gal)',
                       max(1, math.ceil(wall_area / 350 * 2)), 'gal',
                       f'2 coats, {wall_area:.0f} sqft walls')
        if floor_area > 0:
            report.add(self.CAT_FIN, 'Ceiling paint (1 gal)',
                       max(1, math.ceil(floor_area / 400 * 2)), 'gal',
                       f'2 coats, {floor_area:.0f} sqft ceiling')
        if wall_lf:
            report.add(self.CAT_FIN, 'Exterior caulk (10 oz tube)',
                       math.ceil(wall_lf / 25), 'each',
                       '1 per 25 lf of seams')

    # ── Phase 1.12 — Electrical rough-in stub ────────────────────────────────

    def _calc_electrical_stub(self, report: MaterialReport,
                              rooms: list[dict],
                              walls: list[dict],
                              doors: list[dict],
                              settings: EstimatorSettings):

        def _wall_len(d):
            x1, y1 = d.get('x1', d.get('x', 0)), d.get('y1', d.get('y', 0))
            x2, y2 = d.get('x2', x1 + d.get('w', 0)), d.get('y2', y1)
            return math.hypot(x2 - x1, y2 - y1) / 12

        total_wall_lf = sum(_wall_len(w) for w in walls)

        outlets = math.ceil(total_wall_lf / 12)
        report.add(self.CAT_ELEC, 'Outlet box (single gang)',
                   outlets, 'each', '1 per 12 lf of wall (NEC minimum)')

        switches = len(doors)
        report.add(self.CAT_ELEC, 'Switch box (single gang)',
                   max(switches, 1), 'each', '1 per door opening')

        total_boxes = outlets + switches
        romex_lf = math.ceil(settings.ceiling_ht_ft * total_boxes * 1.25)
        report.add(self.CAT_ELEC, 'Romex 14/2 NM-B wire',
                   math.ceil(romex_lf / 250), 'rolls',
                   f'{romex_lf} lf est. (250 ft rolls)')

        report.add(self.CAT_ELEC, 'Electrical panel circuits (est.)',
                   math.ceil(total_boxes / 8), 'each',
                   '~8 outlets/switches per 15A circuit')

    # ── Phase 1.13 — Drywall & Finishing ─────────────────────────────────────

    def _calc_drywall(self, report: MaterialReport,
                      rooms: list[dict],
                      walls: list[dict],
                      doors: list[dict],
                      windows: list[dict],
                      settings: EstimatorSettings):
        ht     = settings.ceiling_ht_ft
        waste  = settings.waste_pct

        wall_area    = sum(self._wall_len_ft(w) for w in walls) * ht
        # Subtract openings so this trade does not double-count empty air
        for d in doors:
            ow, oh = self._opening_wh(d, default_h=80)
            wall_area -= self._ft(ow) * self._ft(oh)
        for wn in windows:
            ow, oh = self._opening_wh(wn)
            wall_area -= self._ft(ow) * self._ft(oh)
        wall_area = max(0.0, wall_area)

        ceiling_area = sum(self._ft(r['w']) * self._ft(r['h']) for r in rooms)
        total_area   = wall_area + ceiling_area

        if total_area <= 0:
            return

        wall_sheets = math.ceil(self._waste(wall_area, waste) / 32)
        if wall_sheets:
            report.add(self.CAT_DW, '1/2" drywall walls (4x8 sheet)',
                       wall_sheets, 'sheets',
                       f'{wall_area:.0f} sqft walls + {waste:.0f}% waste')
        ceil_sheets = math.ceil(self._waste(ceiling_area, waste) / 32)
        if ceil_sheets:
            report.add(self.CAT_DW, '1/2" drywall ceiling (4x8 sheet)',
                       ceil_sheets, 'sheets',
                       f'{ceiling_area:.0f} sqft ceiling area + {waste:.0f}% waste')

        # 5/8" Type-X for fire-rated areas (garage ceiling etc.) — 1 sheet note
        # Joint compound: 1 bucket (4.5 gal) per 200 sqft
        jc_buckets = math.ceil(total_area / 200)
        report.add(self.CAT_DW, 'Joint compound (4.5 gal bucket)',
                   max(1, jc_buckets), 'each',
                   f'{total_area:.0f} sqft total drywall area')

        # Drywall tape: 1 roll (500 ft) per 1000 sqft
        tape_rolls = math.ceil(total_area / 1000)
        report.add(self.CAT_DW, 'Drywall tape (500 ft roll)',
                   max(1, tape_rolls), 'rolls')

        # Corner bead: every exterior corner × ceiling_ht sections (sold 8 ft each)
        corners_est = max(4, len(walls))
        corner_bead = math.ceil(corners_est * ht / 8)
        report.add(self.CAT_DW, 'Metal corner bead (8 ft)',
                   corner_bead, 'each',
                   f'{corners_est} corners × {ht:.0f} ft')

        # Drywall screws: 1 lb per 500 sqft (1-5/8" coarse)
        dw_screws_lbs = math.ceil(total_area / 500)
        report.add(self.CAT_DW, 'Drywall screws 1-5/8" coarse (1 lb box)',
                   max(1, dw_screws_lbs), 'lbs')

        # Interior primer: 1 gal per 400 sqft
        int_primer = math.ceil(total_area / 400)
        report.add(self.CAT_DW, 'Interior drywall primer (1 gal)',
                   max(1, int_primer), 'gal',
                   f'{total_area:.0f} sqft total surface')

        # Paint belongs to the Finish trade — counted in _calc_finish when that
        # trade is on, not here.

    # ── Phase 1.14 — Insulation ───────────────────────────────────────────────

    def _calc_insulation(self, report: MaterialReport,
                         rooms: list[dict],
                         walls: list[dict],
                         settings: EstimatorSettings):
        ceiling_area = sum(self._ft(r['w']) * self._ft(r['h']) for r in rooms)
        r_val        = settings.ceiling_insul_r
        ht           = settings.ceiling_ht_ft
        wall_area    = sum(self._wall_len_ft(w) for w in walls) * ht
        waste        = settings.waste_pct

        if ceiling_area <= 0 and wall_area <= 0:
            return

        if wall_area > 0:
            batt_r = 'R-13' if settings.stud_size == '2x4' else 'R-19'
            insul_bags = math.ceil(self._waste(wall_area, waste) / 40)
            report.add(self.CAT_INSUL, f'Batt insulation ({batt_r})',
                       insul_bags, 'bags',
                       f'{wall_area:.0f} sqft walls')
            vb_wall = math.ceil(wall_area / 1000)
            report.add(self.CAT_INSUL, 'Vapor barrier (6-mil poly, 1000 sqft roll)',
                       max(1, vb_wall), 'rolls', 'Wall vapor retarder')

        if ceiling_area <= 0:
            return

        # Blown-in bags: R-38 ~ 22 bags/1000 sqft; R-30 ~ 17; R-49 ~ 29
        bags_per_1k = {30: 17, 38: 22, 49: 29}.get(r_val, 22)
        bags = math.ceil(ceiling_area / 1000 * bags_per_1k)
        report.add(self.CAT_INSUL, f'Blown-in insulation (R-{r_val}) bag',
                   max(1, bags), 'bags',
                   f'{ceiling_area:.0f} sqft attic floor')

        # Vapor barrier for ceiling/attic
        vb_rolls = math.ceil(ceiling_area / 1000)
        report.add(self.CAT_INSUL, 'Vapor barrier poly 6-mil (1000 sqft roll)',
                   max(1, vb_rolls), 'rolls',
                   'Attic floor vapor retarder')

        # Rigid foam for rim joist: perimeter estimate from rooms
        xs = [r['x'] for r in rooms] + [r['x'] + r['w'] for r in rooms]
        ys = [r['y'] for r in rooms] + [r['y'] + r['h'] for r in rooms]
        perim_ft = (self._ft(max(xs) - min(xs)) + self._ft(max(ys) - min(ys))) * 2
        rim_boards = math.ceil(perim_ft / 4)   # 2x4 ft rigid foam panels
        report.add(self.CAT_INSUL, '2" rigid foam (R-10) for rim joist (2x4 ft panel)',
                   rim_boards, 'each',
                   f'{perim_ft:.0f} lf perimeter rim joist')

    # ── Phase 1.15 — Flooring ─────────────────────────────────────────────────

    def _calc_flooring(self, report: MaterialReport,
                       rooms: list[dict],
                       settings: EstimatorSettings):
        floor_sqft = sum(self._ft(r['w']) * self._ft(r['h']) for r in rooms)
        if floor_sqft <= 0:
            return

        waste  = settings.waste_pct
        ftype  = settings.flooring_type
        total  = self._waste(floor_sqft, waste)

        if ftype == 'lvp':
            boxes = math.ceil(total / 20)   # ~20 sqft per box
            report.add(self.CAT_FLOOR, 'LVP flooring (box ≈ 20 sqft)',
                       boxes, 'boxes',
                       f'{floor_sqft:.0f} sqft + {waste:.0f}% waste')
            report.add(self.CAT_FLOOR, 'LVP underlayment (200 sqft roll)',
                       math.ceil(total / 200), 'rolls')
        elif ftype == 'tile':
            sqft_adj = math.ceil(total)
            report.add(self.CAT_FLOOR, 'Ceramic / porcelain tile (sqft)',
                       sqft_adj, 'sqft',
                       f'{floor_sqft:.0f} sqft + {waste:.0f}% waste')
            thinset_bags = math.ceil(total / 40)   # 50 lb bag covers ~40 sqft
            report.add(self.CAT_FLOOR, 'Thinset mortar (50 lb bag)',
                       max(1, thinset_bags), 'bags')
            grout_bags = math.ceil(total / 50)
            report.add(self.CAT_FLOOR, 'Grout (25 lb bag)',
                       max(1, grout_bags), 'bags')
        elif ftype == 'carpet':
            sy = math.ceil(total / 9)   # convert sqft to sq yards
            report.add(self.CAT_FLOOR, 'Carpet (sq yd)',
                       sy, 'sq yd',
                       f'{floor_sqft:.0f} sqft = {math.ceil(floor_sqft/9)} sy + waste')
            report.add(self.CAT_FLOOR, 'Carpet pad (sq yd)',
                       sy, 'sq yd')
            perim_lf = 0
            for r in rooms:
                perim_lf += 2 * (self._ft(r['w']) + self._ft(r['h']))
            report.add(self.CAT_FLOOR, 'Tack strip (8 ft length)',
                       math.ceil(perim_lf / 8), 'each',
                       f'{perim_lf:.0f} lf room perimeter')
        elif ftype == 'hardwood':
            waste_hw = settings.waste_pct + 5   # hardwood needs extra
            total_hw = self._waste(floor_sqft, waste_hw)
            report.add(self.CAT_FLOOR, 'Hardwood flooring (sqft)',
                       math.ceil(total_hw), 'sqft',
                       f'{floor_sqft:.0f} sqft + {waste_hw:.0f}% waste')
            report.add(self.CAT_FLOOR, 'Hardwood underlayment (200 sqft roll)',
                       math.ceil(total_hw / 200), 'rolls')

        # Transition strips: estimate 1 per door opening between rooms
        door_count_adj = max(1, len(rooms) - 1)
        report.add(self.CAT_FLOOR, 'Transition strip (T-molding, 6 ft)',
                   door_count_adj, 'each',
                   '1 per doorway between floored rooms')

    # ── Phase 1.16 — Doors & Windows ─────────────────────────────────────────

    def _calc_doors_windows(self, report: MaterialReport,
                            doors: list[dict],
                            windows: list[dict],
                            settings: EstimatorSettings):
        for d in doors:
            w_in, h_in = self._opening_wh(d, default_h=80)
            label = f'{int(w_in)}"×{int(h_in)}" pre-hung door unit'
            report.add(self.CAT_DWIN, label, 1, 'each',
                       f'{int(w_in)}" W × {int(h_in)}" H rough opening')

        if doors:
            # Door hardware: lever/knob set per door
            report.add(self.CAT_DWIN, 'Door lever/knob set',
                       len(doors), 'each', '1 per door')
            # Door hinges (3 per door, sold in pairs — 2 pair needed)
            report.add(self.CAT_DWIN, 'Door hinge pair (3.5" butt hinge)',
                       len(doors) * 2, 'pairs', '2 pairs (4 hinges) per door')
            # Door stop molding: 1 per door
            report.add(self.CAT_DWIN, 'Door stop molding (7 ft)',
                       len(doors), 'each')

        for wn in windows:
            w_in, h_in = self._opening_wh(wn)
            label = f'{int(w_in)}"×{int(h_in)}" window unit'
            report.add(self.CAT_DWIN, label, 1, 'each',
                       f'{int(w_in)}" W × {int(h_in)}" H rough opening')

        if windows:
            report.add(self.CAT_DWIN, 'Window lock / hardware set',
                       len(windows), 'each', '1 per window')

    # ── Phase 1.17 — Exterior Finish (Siding + Housewrap) ────────────────────

    def _calc_siding(self, report: MaterialReport,
                     rooms: list[dict],
                     walls: list[dict],
                     doors: list[dict],
                     windows: list[dict],
                     settings: EstimatorSettings):
        ht    = settings.ceiling_ht_ft
        waste = settings.waste_pct

        def _wall_len(d):
            x1 = d.get('x1', d.get('x', 0))
            y1 = d.get('y1', d.get('y', 0))
            x2 = d.get('x2', x1 + d.get('w', 0))
            y2 = d.get('y2', y1 + d.get('h', 0))
            return math.hypot(x2 - x1, y2 - y1) / 12

        total_lf   = sum(_wall_len(w) for w in walls)
        wall_area  = total_lf * ht

        # Subtract door/window openings
        for d in doors:
            w_in, h_in = self._opening_wh(d, default_h=80)
            wall_area -= self._ft(w_in) * self._ft(h_in)
        for wn in windows:
            w_in, h_in = self._opening_wh(wn)
            wall_area -= self._ft(w_in) * self._ft(h_in)

        wall_area = max(0.0, wall_area)
        if wall_area <= 0:
            return

        stype = settings.siding_type
        adj   = self._waste(wall_area, waste)

        if stype == 'vinyl':
            squares = math.ceil(adj / 100)
            report.add(self.CAT_EXT, 'Vinyl siding (1 square = 100 sqft)',
                       squares, 'squares',
                       f'{wall_area:.0f} sqft net wall area + {waste:.0f}% waste')
            # J-channel: around every window/door + top of wall
            jchannel_lf = total_lf
            for d in doors:
                w_in, h_in = self._opening_wh(d, default_h=80)
                jchannel_lf += (w_in + h_in) * 2 / 12
            for wn in windows:
                w_in, h_in = self._opening_wh(wn)
                jchannel_lf += (w_in + h_in) * 2 / 12
            report.add(self.CAT_EXT, 'Vinyl J-channel (12 ft length)',
                       math.ceil(jchannel_lf / 12), 'each',
                       f'{jchannel_lf:.0f} lf around openings + top')
            report.add(self.CAT_EXT, 'Vinyl starter strip (12 ft length)',
                       math.ceil(total_lf / 12), 'each',
                       f'{total_lf:.0f} lf wall base')
            report.add(self.CAT_EXT, 'Outside corner post (10 ft)',
                       math.ceil(len(walls) / 2) * 2, 'each',
                       'Estimate 2 per building corner')
        elif stype in ('hardie', 'wood'):
            label = 'Fiber cement (Hardie) siding (sqft)' if stype == 'hardie' else 'Wood lap siding (sqft)'
            report.add(self.CAT_EXT, label,
                       math.ceil(adj), 'sqft',
                       f'{wall_area:.0f} sqft + {waste:.0f}% waste')
            nails_lbs = math.ceil(adj / 150)   # ~1 lb per 150 sqft
            report.add(self.CAT_EXT, 'Siding nails (1 lb box)',
                       max(1, nails_lbs), 'lbs')

        # Housewrap: same as gross wall area (no opening deductions needed)
        gross_area = total_lf * ht
        hw_rolls = math.ceil(gross_area / 900)   # typical roll = 9 sq = 900 sqft
        report.add(self.CAT_EXT, 'Housewrap / Tyvek (900 sqft roll)',
                   max(1, hw_rolls), 'rolls',
                   f'{gross_area:.0f} sqft gross wall area')
        hw_tape_rolls = math.ceil(gross_area / 500)
        report.add(self.CAT_EXT, 'Housewrap seam tape (164 ft roll)',
                   max(1, hw_tape_rolls), 'rolls')

    # ── Phase 1.18 — Roofing Materials ───────────────────────────────────────

    def _calc_roofing(self, report: MaterialReport,
                      rooms: list[dict],
                      settings: EstimatorSettings):
        if not rooms:
            return

        pitch  = settings.roof_pitch
        ov_ft  = settings.rafter_overhang_ft
        waste  = settings.waste_pct

        xs = [r['x'] for r in rooms] + [r['x'] + r['w'] for r in rooms]
        ys = [r['y'] for r in rooms] + [r['y'] + r['h'] for r in rooms]
        bldg_w_ft = self._ft(max(xs) - min(xs))
        bldg_l_ft = self._ft(max(ys) - min(ys))

        run_ft        = bldg_w_ft / 2
        rafter_len_ft = run_ft * math.sqrt(1 + (pitch / 12) ** 2) + ov_ft
        roof_area     = rafter_len_ft * bldg_l_ft * 2   # both slopes
        adj_roof      = self._waste(roof_area, waste)
        squares       = math.ceil(adj_roof / 100)

        rtype = settings.roofing_type
        perimeter_lf = (bldg_l_ft + bldg_w_ft) * 2 + 4 * ov_ft
        report.add(self.CAT_ROOFING, 'Synthetic roof underlayment (400 sqft roll)',
                   max(1, math.ceil(roof_area / 400)), 'rolls',
                   f'{roof_area:.0f} sqft roof area')
        report.add(self.CAT_ROOFING, 'Drip edge (10 ft section)',
                   math.ceil(perimeter_lf / 10), 'each',
                   f'{perimeter_lf:.0f} lf eaves + rakes')

        if rtype == 'shingles':
            report.add(self.CAT_ROOFING,
                       'Architectural shingles (bundle, 33 sqft)',
                       squares * 3, 'bundles',
                       f'{roof_area:.0f} sqft roof area + {waste:.0f}% waste')
            # Starter strip: 1 bundle per 100 lf eave
            eave_lf = bldg_l_ft * 2 + bldg_w_ft * 2 + 4 * ov_ft
            report.add(self.CAT_ROOFING, 'Starter strip shingle (bundle ≈ 100 lf)',
                       max(1, math.ceil(eave_lf / 100)), 'bundles')
            # Ridge cap: 1 bundle per 35 lf of ridge
            ridge_lf = bldg_l_ft + 2 * ov_ft
            report.add(self.CAT_ROOFING, 'Ridge cap shingles (bundle ≈ 35 lf)',
                       max(1, math.ceil(ridge_lf / 35)), 'bundles')
            # Roofing nails: 2 lbs per square
            report.add(self.CAT_ROOFING, 'Roofing nails 1-3/4" (5 lb box)',
                       math.ceil(squares * 2 / 5), 'boxes',
                       '2 lbs per square')
        else:  # metal
            report.add(self.CAT_ROOFING, 'Metal roofing panel (sqft)',
                       math.ceil(adj_roof), 'sqft',
                       f'{roof_area:.0f} sqft + {waste:.0f}% waste')
            report.add(self.CAT_ROOFING, 'Metal roofing screws (1 lb box)',
                       math.ceil(squares * 3 / 100), 'lbs')

        # Ice & water shield: first 3 ft from each eave
        ice_sqft = eave_lf * 3 if rtype == 'shingles' else (bldg_l_ft * 2 + bldg_w_ft * 2) * 3
        report.add(self.CAT_ROOFING, 'Ice & water shield (225 sqft roll)',
                   max(1, math.ceil(ice_sqft / 225)), 'rolls',
                   'First 3 ft from all eaves')

        # Roof vents: 1 per 150 sqft attic floor
        attic_sqft = bldg_w_ft * bldg_l_ft
        report.add(self.CAT_ROOFING, 'Roof vent (static or ridge vent)',
                   max(1, math.ceil(attic_sqft / 150)), 'each',
                   f'{attic_sqft:.0f} sqft attic, 1 per 150 sqft')

    # ── Phase 1.19 — Interior Trim ────────────────────────────────────────────

    def _calc_interior_trim(self, report: MaterialReport,
                            rooms: list[dict],
                            doors: list[dict],
                            windows: list[dict],
                            settings: EstimatorSettings):
        # Baseboard: room perimeter minus door widths
        total_perim_lf = sum(
            2 * (self._ft(r['w']) + self._ft(r['h'])) for r in rooms
        )
        door_openings_lf = sum(d.get('width', 36) / 12 for d in doors)
        base_lf = max(0, total_perim_lf - door_openings_lf)

        report.add(self.CAT_TRIM, 'Baseboard (3.5", 16 ft length)',
                   math.ceil(base_lf / 16), 'each',
                   f'{base_lf:.0f} lf (perimeter minus doors)')
        report.add(self.CAT_TRIM, 'Base shoe molding (16 ft length)',
                   math.ceil(base_lf / 16), 'each',
                   f'{base_lf:.0f} lf')

        # Door casing: ~17 lf per door (2 jamb sides + header, each side)
        if doors:
            door_casing_lf = len(doors) * 17
            report.add(self.CAT_TRIM, 'Door casing (16 ft length)',
                       math.ceil(door_casing_lf / 16), 'each',
                       f'{len(doors)} doors × 17 lf each (both sides)')
            report.add(self.CAT_TRIM, 'Door threshold / sill',
                       len(doors), 'each')

        # Window casing: ~10 lf per window (4 sides)
        if windows:
            win_casing_lf = len(windows) * 10
            report.add(self.CAT_TRIM, 'Window casing (16 ft length)',
                       math.ceil(win_casing_lf / 16), 'each',
                       f'{len(windows)} windows × 10 lf each')
            report.add(self.CAT_TRIM, 'Window stool & apron (8 ft length)',
                       len(windows), 'each')

        # Trim nails / finish nails
        total_trim_lf = base_lf + (len(doors) * 17 if doors else 0) + (len(windows) * 10 if windows else 0)
        report.add(self.CAT_TRIM, 'Finish nails 2" (1 lb box)',
                   max(1, math.ceil(total_trim_lf / 200)), 'lbs',
                   '~1 lb per 200 lf of trim')
        report.add(self.CAT_TRIM, 'Interior caulk (10 oz tube)',
                   max(1, math.ceil(total_trim_lf / 50)), 'each',
                   '1 tube per 50 lf of trim joints')
        report.add(self.CAT_TRIM, 'Trim paint / wood filler',
                   1, 'allowance')

    # ── Phase 1.20 — Plumbing Rough-In ───────────────────────────────────────

    def _calc_plumbing_stub(self, report: MaterialReport,
                            rooms: list[dict],
                            settings: EstimatorSettings):
        total_sqft = sum(self._ft(r['w']) * self._ft(r['h']) for r in rooms)
        if total_sqft <= 0:
            return
        # Rough estimate: 1 bathroom per 200 sqft (minimum 1)
        bath_count = max(1, math.ceil(total_sqft / 200))

        report.add(self.CAT_PLUMB, 'ABS/PVC drain pipe 3" (10 ft length)',
                   math.ceil(bath_count * 30 / 10), 'each',
                   f'~30 lf per bathroom ({bath_count} bath est.)')
        report.add(self.CAT_PLUMB, 'PEX supply line 1/2" (100 ft roll)',
                   math.ceil(bath_count * 50 / 100), 'rolls',
                   f'~50 lf per bathroom')
        report.add(self.CAT_PLUMB, 'PVC drain fittings kit',
                   bath_count, 'each', 'Elbows, tees, couplings per bathroom')
        report.add(self.CAT_PLUMB, 'PEX crimp fitting kit',
                   bath_count, 'each')
        report.add(self.CAT_PLUMB, 'P-trap 1-1/2" (per sink)',
                   bath_count, 'each')
        report.add(self.CAT_PLUMB, 'Toilet flange 3" PVC',
                   bath_count, 'each')
        report.add(self.CAT_PLUMB, 'Water heater stub-out kit',
                   1, 'each')
        report.add(self.CAT_PLUMB, 'Shutoff valve 1/2" (angle stop)',
                   bath_count * 2, 'each', '2 per bathroom (hot + cold)')
        report.add(self.CAT_PLUMB, 'Main shutoff valve 3/4"',
                   1, 'each')

    # ── Phase 1.21 — HVAC Rough-In ───────────────────────────────────────────

    def _calc_hvac_stub(self, report: MaterialReport,
                        rooms: list[dict],
                        settings: EstimatorSettings):
        total_sqft = sum(self._ft(r['w']) * self._ft(r['h']) for r in rooms)
        if total_sqft <= 0:
            return

        room_count = max(1, len(rooms))
        ht         = settings.ceiling_ht_ft
        # Rough duct LF: ceiling height × room count × 2 (supply + return)
        duct_lf    = math.ceil(ht * room_count * 2)
        # HVAC tonnage: 1 ton per 600 sqft (approx. Manual J simplified)
        tons       = max(1, math.ceil(total_sqft / 600))

        report.add(self.CAT_HVAC, 'Flexible duct 6" (25 ft section)',
                   math.ceil(duct_lf / 25), 'each',
                   f'~{duct_lf} lf supply + return estimate')
        report.add(self.CAT_HVAC, 'Supply register 4"×10" (floor/wall)',
                   room_count, 'each', '1 per room')
        report.add(self.CAT_HVAC, 'Return air grille 14"×14"',
                   max(1, math.ceil(room_count / 2)), 'each', '1 per 2 rooms')
        report.add(self.CAT_HVAC, 'Duct takeoff collar 6"',
                   room_count, 'each', '1 per supply run')
        report.add(self.CAT_HVAC, f'HVAC unit ({tons} ton heat pump / split)',
                   1, 'each',
                   f'{total_sqft:.0f} sqft ÷ 600 sqft/ton = {tons} ton')
        report.add(self.CAT_HVAC, 'Thermostat (programmable)',
                   1, 'each')
        report.add(self.CAT_HVAC, 'Plenum / air handler box',
                   1, 'each')
        report.add(self.CAT_HVAC, 'Duct insulation wrap (1" fiberglass, 25 ft roll)',
                   math.ceil(duct_lf / 25), 'each')
        report.add(self.CAT_HVAC, 'HVAC disconnect box',
                   1, 'each')

    # ── Pole Barn ─────────────────────────────────────────────────────────────

    def _calc_pole_barn(self, report: MaterialReport,
                        sched: LumberSchedule,
                        sections: list[dict],
                        settings: EstimatorSettings):
        """
        Kentucky pole barn (post-frame) material estimate.
        References: KBC 2013/2018, IRC 2021 §R602, KY Ag Extension AEN-110.
        Minimum column: 6×6  |  Max col spacing: 12 ft  |  Frost depth: 24"
        Embed rule-of-thumb: building_ht / 5 + 2 ft  (min embed 4 ft for KY).
        """
        CAT_COL   = 'Pole Barn – Columns'
        CAT_GIRT  = 'Pole Barn – Girts & Framing'
        CAT_ROOF  = 'Pole Barn – Roof Structure'
        CAT_CLAD  = 'Pole Barn – Cladding'
        CAT_BASE  = 'Pole Barn – Foundation & Floor'
        CAT_HW    = 'Pole Barn – Hardware'

        col_sp    = settings.pb_col_spacing_ft
        embed     = settings.pb_col_embed_ft
        col_ht    = settings.pb_col_height_ft
        girt_sp   = settings.pb_girt_spacing_in / 12.0   # convert to ft
        truss_sp  = settings.pb_truss_spacing_ft
        purlin_sp = settings.pb_purlin_spacing_in / 12.0
        pitch     = settings.roof_pitch
        waste     = settings.waste_pct
        col_size  = settings.pb_col_size
        girt_size = '2x6' if col_size in ('8x8', '8x10') else '2x4'

        slope_factor   = math.sqrt(1 + (pitch / 12) ** 2)
        overhang_ft    = settings.rafter_overhang_ft

        total_cols        = 0
        total_truss_count = 0
        total_truss_width = 0.0
        total_purlin_lf   = 0.0
        total_girt_lf     = 0.0
        total_wall_sf     = 0.0
        total_floor_sf    = 0.0
        total_roof_sf     = 0.0
        total_perim_ft    = 0.0

        for sec in sections:
            W = sec.get('width_ft', settings.building_width_ft)
            L = sec.get('length_ft', settings.building_length_ft)

            # Perimeter columns: one at each corner + intermediate on each wall
            cols_long  = math.floor(L / col_sp) + 1   # per long wall
            cols_short = math.floor(W / col_sp) + 1   # per short wall
            sec_cols   = 2 * cols_long + 2 * cols_short - 4  # corners shared
            total_cols += sec_cols

            # Girts (horizontal wall nailers between columns)
            girt_rows  = math.ceil(col_ht / girt_sp)
            perim_ft   = 2 * (W + L)
            total_perim_ft += perim_ft
            # Each girt span = col_sp; total pieces ≈ spans × rows
            girt_spans = 2 * (cols_long - 1) + 2 * (cols_short - 1)
            total_girt_lf += girt_spans * girt_rows * col_sp * (1 + waste / 100)

            # Trusses: one at each truss spacing along the length
            sec_trusses = math.floor(L / truss_sp) + 1
            total_truss_count += sec_trusses
            total_truss_width = max(total_truss_width, W)  # span of widest section

            # Purlins: rows per slope × 2 slopes × length + overhang
            rafter_run_ft     = (W / 2) * slope_factor + overhang_ft
            purlin_rows_slope = math.ceil(rafter_run_ft / purlin_sp) + 1
            purlin_run_ft     = L + 2 * overhang_ft
            total_purlin_lf  += purlin_rows_slope * 2 * purlin_run_ft * (1 + waste / 100)

            # Areas
            total_wall_sf  += perim_ft * col_ht
            total_floor_sf += W * L
            total_roof_sf  += W * slope_factor * L * (1 + waste / 100)

        # ── Columns ──────────────────────────────────────────────────────────
        col_total_ft = embed + col_ht + 0.5   # +6" for ridge-notch allowance
        col_stock_ft = int(math.ceil(col_total_ft / 2) * 2)   # next even ft
        col_stock_ft = max(col_stock_ft, 8)
        report.add(CAT_COL, f'{col_size} column × {col_stock_ft}\'',
                   total_cols, 'pcs',
                   f'{total_cols} columns: {embed:.1f} ft embed + {col_ht:.0f} ft above grade  '
                   f'(KY min embed 4 ft, frost 24")')
        report.add(CAT_COL, f'Column total length each',
                   1, 'note',
                   f'{col_total_ft:.1f} ft = {embed:.1f} ft embed + {col_ht:.0f} ft wall + 0.5 ft trim')

        # ── Girts ────────────────────────────────────────────────────────────
        girt_pieces = [col_sp] * int(total_girt_lf / col_sp + 0.5)
        self._add_lumber_summary(report, sched, CAT_GIRT, girt_size,
                                 girt_pieces,
                                 f'{settings.pb_girt_spacing_in:.0f}" o.c. horizontal wall nailers  '
                                 f'({total_girt_lf:.0f} lf + {waste:.0f}% waste)')

        # Skirt / bottom girt (PT at grade) — only added here if skirt_type is 'none'
        # (pt_skirt and grade_beam are handled under CAT_BASE below)
        if settings.pb_skirt_type == 'none':
            report.add(CAT_GIRT, f'2x8 PT nailer (bottom girt) × {int(col_sp)}\'',
                       2 * int(math.ceil(total_perim_ft / col_sp)),
                       'pcs', f'Bottom nailer at grade, {total_perim_ft:.0f} lf perimeter')

        # Ridge board / ridge beam
        ridge_lf = sum(s.get('length_ft', settings.building_length_ft) + 2 * overhang_ft
                       for s in sections)
        report.add(CAT_GIRT, f'2x10 ridge board × 16\'',
                   int(math.ceil(ridge_lf / 16 * (1 + waste / 100))), 'pcs',
                   f'{ridge_lf:.0f} lf ridge + overhangs (+{waste:.0f}% waste)')

        # ── Roof trusses ──────────────────────────────────────────────────────
        report.add(CAT_ROOF, f'Prefab roof truss (span {total_truss_width:.0f}\' / {pitch}/12 pitch)',
                   total_truss_count, 'each',
                   f'Trusses @ {truss_sp:.0f} ft o.c. — order from local truss plant  '
                   f'(verify bearing, snow 20 psf KY central)')

        # ── Purlins ───────────────────────────────────────────────────────────
        purlin_pieces = [purlin_sp * 12 / 12] * int(total_purlin_lf / (purlin_sp) + 0.5)
        # Use standard 8/10/12 ft stock for purlins
        purlin_stock_pieces = [settings.rafter_overhang_ft * 2 + s.get('length_ft', 30)
                                for s in sections] * int(total_purlin_lf / 20 + 1)
        report.add(CAT_ROOF, '2x4 purlin (roof nailer)',
                   int(math.ceil(total_purlin_lf / 8 * (1 + waste / 100))), 'pcs @ 8\'',
                   f'{total_purlin_lf:.0f} lf @ {settings.pb_purlin_spacing_in:.0f}" o.c. '
                   f'(+{waste:.0f}% waste)')

        # ── Roof cladding ─────────────────────────────────────────────────────
        if not settings.include_roofing:
            pass
        elif settings.pb_roof_cladding == 'metal':
            # 3-ft wide ribbed metal panels — order in running ft of panel
            panel_width_ft = 3.0
            rafter_run_ft  = (total_truss_width / 2) * slope_factor + overhang_ft
            panels_per_row = int(math.ceil(
                sum(s.get('length_ft', 30) + 2 * overhang_ft for s in sections) / panel_width_ft
                * (1 + waste / 100)))
            report.add(CAT_CLAD, f'Metal roofing panel (3\' wide × {rafter_run_ft:.1f}\' long)',
                       panels_per_row * 2, 'pcs',
                       f'Both slopes: {total_roof_sf:.0f} sqft roof area (+{waste:.0f}% waste)')
            report.add(CAT_CLAD, 'Metal roofing screws w/ neoprene washer (250-ct box)',
                       int(math.ceil(total_roof_sf / 150)), 'boxes',
                       '~1 screw per sqft at purlins')
            report.add(CAT_CLAD, 'Ridge cap (metal, 10 ft length)',
                       int(math.ceil(ridge_lf / 10 * (1 + waste / 100))), 'pcs',
                       f'{ridge_lf:.0f} lf ridge')
        else:
            # Shingles
            roof_squares = math.ceil(total_roof_sf / 100 * (1 + waste / 100))
            report.add(CAT_CLAD, 'Architectural shingles (1 square / bundle = 33 sqft)',
                       int(math.ceil(roof_squares * 3)), 'bundles',
                       f'{total_roof_sf:.0f} sqft roof area')
            report.add(CAT_CLAD, 'Roofing felt / underlayment (4-square roll)',
                       int(math.ceil(roof_squares / 4)), 'rolls', '')

        # ── Wall cladding ─────────────────────────────────────────────────────
        net_wall_sf = total_wall_sf * (1 + waste / 100)
        if not settings.include_siding:
            pass
        elif settings.pb_wall_cladding == 'metal':
            panel_width_ft = 3.0
            panel_ht_ft    = col_ht + 1.0    # +1 ft for overlap / trim
            panel_cols_per_wall = int(math.ceil(total_perim_ft / panel_width_ft
                                                * (1 + waste / 100)))
            report.add(CAT_CLAD, f'Metal wall panel (3\' wide × {panel_ht_ft:.0f}\' tall)',
                       panel_cols_per_wall, 'pcs',
                       f'{total_wall_sf:.0f} sqft wall area (+{waste:.0f}% waste)')
            report.add(CAT_CLAD, 'Metal wall screws w/ neoprene washer (250-ct box)',
                       int(math.ceil(net_wall_sf / 200)), 'boxes', '~1 screw per sqft at girts')
            report.add(CAT_CLAD, 'Corner trim (metal, 10 ft)',
                       int(math.ceil(total_cols / (math.ceil(total_perim_ft / col_sp)) * 4
                                     * col_ht / 10 + 0.5)),
                       'pcs', '4 corners × wall height')
        elif settings.pb_wall_cladding == 'board_batten':
            report.add(CAT_CLAD, '1×6 board (board & batten siding)',
                       int(math.ceil(net_wall_sf / 4)), 'pcs @ 8\'',
                       f'{net_wall_sf:.0f} sqft wall area (rough estimate)')
            report.add(CAT_CLAD, '1×3 batten strip',
                       int(math.ceil(net_wall_sf / 12)), 'pcs @ 8\'', '1 batten per 12" o.c.')
        else:  # LP SmartSide
            sheets = int(math.ceil(net_wall_sf / 32))   # 4×8 panel
            report.add(CAT_CLAD, 'LP SmartSide panel (4×8 sheet)',
                       sheets, 'sheets', f'{net_wall_sf:.0f} sqft wall area')

        # ── Perimeter treatment ───────────────────────────────────────────────
        if not settings.include_concrete:
            pass
        elif settings.pb_skirt_type == 'pt_skirt':
            # 2×8 PT skirt board at grade around perimeter
            skirt_pcs = int(math.ceil(total_perim_ft / 8 * (1 + waste / 100)))
            report.add(CAT_BASE, '2x8 PT skirt board × 8\'',
                       skirt_pcs, 'pcs',
                       f'{total_perim_ft:.0f} lf perimeter (+{waste:.0f}% waste)')
        elif settings.pb_skirt_type == 'grade_beam':
            beam_lf  = total_perim_ft
            conc_cyd = beam_lf * (1 / 3) * (2 / 3) / 27   # 4"×8" grade beam (ft units)
            report.add(CAT_BASE, 'Concrete grade beam (4" wide × 8" deep)',
                       int(math.ceil(beam_lf)), 'lf', 'Perimeter grade beam')
            report.add(CAT_BASE, 'Concrete (grade beam)',
                       math.ceil(conc_cyd * 1.1), 'cu yd', '+10% waste')
            report.add(CAT_BASE, '#4 rebar (10 ft)',
                       int(math.ceil(beam_lf * 2 / 10 * 1.1)), 'pcs',
                       '2 continuous bars in grade beam')

        # ── Floor ─────────────────────────────────────────────────────────────
        if not settings.include_concrete:
            pass
        elif settings.pb_floor_type == 'concrete':
            conc_cyd = total_floor_sf * (4 / 12) / 27   # 4" slab
            report.add(CAT_BASE, 'Concrete slab (4" thick)',
                       math.ceil(conc_cyd * 1.05), 'cu yd',
                       f'{total_floor_sf:.0f} sqft floor area (+5% waste)')
            report.add(CAT_BASE, '6-mil poly vapor barrier (1000 sqft roll)',
                       int(math.ceil(total_floor_sf / 900)), 'rolls',
                       'Under slab moisture barrier')
            report.add(CAT_BASE, 'Wire mesh (6×6 W1.4/W1.4, 5×10 sheet)',
                       int(math.ceil(total_floor_sf / 50 * 1.1)), 'sheets',
                       'Slab reinforcement (+10% waste)')
            report.add(CAT_BASE, 'Compactable gravel base (4", tons)',
                       math.ceil(total_floor_sf * (4 / 12) / 27 * 1.4), 'tons',
                       '4" compacted base under slab (1.4 t/cu yd)')
        elif settings.pb_floor_type == 'gravel':
            report.add(CAT_BASE, 'Crushed stone / gravel (4" depth, tons)',
                       math.ceil(total_floor_sf * (4 / 12) / 27 * 1.4), 'tons',
                       f'{total_floor_sf:.0f} sqft floor @ 4" depth')

        # ── Hardware ──────────────────────────────────────────────────────────
        if settings.include_hardware:
            report.add(CAT_HW, 'Column base bracket (Simpson AC-series)',
                       total_cols, 'each',
                       'One per column — verify size for column type')
            report.add(CAT_HW, 'Truss-to-column bracket (Simpson H10 or equal)',
                       total_truss_count * 2, 'each',
                       'Two per truss (both bearing walls)')
            report.add(CAT_HW, 'Lag bolt 1/2"×4" (girt-to-column)',
                       int(math.ceil(total_cols * 3)), 'each',
                       '~3 per column for girt attachment')
            report.add(CAT_HW, '16d galvanized spike nails (5 lb box)',
                       int(math.ceil(total_cols * 3 / 50)), 'boxes',
                       '~50 per box, column & girt framing')


# ══════════════════════════════════════════════════════════════════════════════
# Kentucky / IRC 2021 Code Compliance Engine
# ══════════════════════════════════════════════════════════════════════════════

from code_tables import (
    KY_DEFAULTS,
    min_deck_joist, min_floor_joist, min_deck_beam,
    min_rafter, min_footing_dia, max_cantilever,
    blocking_rows_required, header_size as _header_size_code,
    footing_depth_required, rafter_length, POST_MAX_HEIGHTS,
    NOMINAL_TO_ACTUAL,
)


@dataclass
class CodeIssue:
    """One structural code compliance finding."""
    element:     str        # e.g. 'Joist Fill', 'Footing', 'Rafter'
    location:    str        # e.g. 'bay 1' or 'wall at x=120"'
    check:       str        # short description of the rule checked
    required:    str        # what the code requires
    provided:    str        # what was found in the drawing ('' if missing)
    severity:    str        # 'OK' | 'WARN' | 'ERROR'
    auto_fixable: bool = False   # True = AutoDrawEngine can resolve it


@dataclass
class CodeReport:
    """Collection of all code compliance findings for the current scene."""
    issues: list[CodeIssue] = field(default_factory=list)

    def add(self, element: str, location: str, check: str,
            required: str, provided: str, severity: str,
            auto_fixable: bool = False):
        self.issues.append(CodeIssue(
            element, location, check, required, provided, severity, auto_fixable
        ))

    def errors(self)   -> list[CodeIssue]:
        return [i for i in self.issues if i.severity == 'ERROR']

    def warnings(self) -> list[CodeIssue]:
        return [i for i in self.issues if i.severity == 'WARN']

    def ok_items(self) -> list[CodeIssue]:
        return [i for i in self.issues if i.severity == 'OK']

    def to_csv(self) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(['Element', 'Location', 'Check', 'Required', 'Provided', 'Severity', 'Auto-fixable'])
        for i in self.issues:
            w.writerow([i.element, i.location, i.check,
                        i.required, i.provided, i.severity,
                        'Yes' if i.auto_fixable else 'No'])
        return buf.getvalue()

    def to_plain_text(self) -> str:
        lines = ['ArchCAD — Code Compliance Report (Kentucky / IRC 2021)',
                 '=' * 60]
        for sev, label in (('ERROR', 'ERRORS'), ('WARN', 'WARNINGS'), ('OK', 'PASSING')):
            group = [i for i in self.issues if i.severity == sev]
            if not group:
                continue
            lines.append(f'\n{label} ({len(group)})')
            lines.append('-' * 40)
            for i in group:
                lines.append(f'  {i.element} — {i.location}')
                lines.append(f'    {i.check}: required {i.required}, provided {i.provided}')
        return '\n'.join(lines)


class CodeChecker:
    """
    Validates scene items against Kentucky / IRC 2021 structural requirements.

    Usage:
        ky  = KY_DEFAULTS.copy()
        ky['ground_snow_psf'] = 20          # optionally override
        report = CodeChecker().run(scene_items, settings, ky)
    """

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, scene_items: list[dict],
            settings: EstimatorSettings,
            ky: dict | None = None) -> CodeReport:
        """Run all checks and return a CodeReport."""
        if ky is None:
            ky = KY_DEFAULTS.copy()

        report = CodeReport()

        joistfills = [d for d in scene_items if d.get('type') == 'joist_fill']
        posts      = [d for d in scene_items if d.get('type') == 'post']
        walls      = [d for d in scene_items if d.get('type') == 'wall']
        doors      = [d for d in scene_items if d.get('type') == 'door']
        windows    = [d for d in scene_items if d.get('type') == 'window']
        rooms      = [d for d in scene_items if d.get('type') == 'room']

        self._check_joists(report, joistfills, settings)
        self._check_blocking(report, joistfills, settings)
        self._check_cantilevers(report, joistfills, settings)
        self._check_footings(report, joistfills, posts, settings, ky)
        self._check_posts(report, joistfills, posts, settings)
        self._check_beams(report, joistfills, settings)
        self._check_rafters(report, rooms, walls, settings, ky)
        self._check_headers(report, walls, doors, windows, settings)

        return report

    # ── Individual checks ─────────────────────────────────────────────────────

    def _check_joists(self, report: CodeReport,
                      joistfills: list[dict],
                      settings: EstimatorSettings):
        """Check each JoistFillItem span against IRC joist span tables."""
        for idx, jf in enumerate(joistfills):
            loc = f'bay {idx + 1}'
            span_in, _bay, spacing = MaterialEstimator._joist_span_bay(jf)
            span_ft = span_in / 12.0
            joist_size = jf.get('joist_size', settings.joist_size)

            required = min_deck_joist(span_ft, spacing)
            provided = joist_size

            def _nom(s):
                return int(s.split('x')[1]) if 'x' in s else 0

            if required == '2x12+' or _nom(required) > _nom(provided):
                sev = 'ERROR'
            elif _nom(required) == _nom(provided):
                sev = 'OK'
            else:
                sev = 'OK'   # provided > required → fine

            report.add(
                'Joist Fill', loc,
                f'Joist size for {span_ft:.1f} ft span @ {spacing}" o.c.',
                required, provided, sev,
                auto_fixable=False,  # size upgrade requires user decision
            )

    def _check_blocking(self, report: CodeReport,
                        joistfills: list[dict],
                        settings: EstimatorSettings):
        """Check that required mid-span blocking rows are present in each bay."""
        for idx, jf in enumerate(joistfills):
            loc = f'bay {idx + 1}'
            span_in, _bay, _sp = MaterialEstimator._joist_span_bay(jf)
            rows_required = blocking_rows_required(span_in)
            rows_present  = jf.get('blocking_rows', 0)

            if rows_required == 0:
                report.add('Blocking', loc,
                           'Mid-span blocking', f'{rows_required} rows',
                           f'{rows_present} rows', 'OK')
            elif rows_present >= rows_required:
                report.add('Blocking', loc,
                           'Mid-span blocking', f'{rows_required} rows',
                           f'{rows_present} rows', 'OK')
            else:
                report.add('Blocking', loc,
                           'Mid-span blocking (IRC R502.7)',
                           f'{rows_required} rows',
                           f'{rows_present} rows present',
                           'ERROR', auto_fixable=True)

    def _check_cantilevers(self, report: CodeReport,
                           joistfills: list[dict],
                           settings: EstimatorSettings):
        """Check cantilever extension against IRC R502.3.3."""
        for idx, jf in enumerate(joistfills):
            loc = f'bay {idx + 1}'
            cantilever_in = jf.get('cantilever_in', 0)
            if cantilever_in <= 0:
                continue
            joist_size  = jf.get('joist_size', settings.joist_size)
            max_cant_in = max_cantilever(joist_size)

            if cantilever_in <= max_cant_in:
                report.add('Cantilever', loc,
                           f'Max cantilever for {joist_size} (IRC R502.3.3)',
                           f'{max_cant_in:.2f}"', f'{cantilever_in:.2f}"', 'OK')
            else:
                report.add('Cantilever', loc,
                           f'Max cantilever for {joist_size} (IRC R502.3.3)',
                           f'{max_cant_in:.2f}"', f'{cantilever_in:.2f}"',
                           'ERROR')

    def _check_footings(self, report: CodeReport,
                        joistfills: list[dict],
                        posts: list[dict],
                        settings: EstimatorSettings,
                        ky: dict):
        """Check footing diameter and depth against IRC R507.3 / KY frost depth."""
        frost_in    = ky.get('frost_depth_in', 24)
        soil_psf    = ky.get('soil_bearing_psf', 1500)
        snow_psf    = ky.get('ground_snow_psf', 20)
        min_depth   = footing_depth_required(frost_in)

        # Build list of posts from explicit post items + grid-implied posts
        if posts:
            all_posts = posts
        else:
            # Estimate implied posts from joist fill grids
            all_posts = self._implied_posts(joistfills, settings)

        for idx, post in enumerate(all_posts):
            loc = f'post {idx + 1}'
            trib_ft2 = post.get('trib_area_ft2', 0)
            if trib_ft2 <= 0:
                # Compute from settings if not stored
                trib_ft2 = (settings.post_spacing_x_ft *
                            settings.post_spacing_y_ft)

            req_dia_in = min_footing_dia(trib_ft2)
            act_dia_in = post.get('footing_dia_in',
                                   settings.footing_dia_in)
            act_depth_in = post.get('footing_depth_in',
                                     settings.footing_depth_in)

            if act_dia_in < req_dia_in:
                report.add('Footing', loc,
                           f'Min dia for {trib_ft2:.0f} ft² trib. area (IRC R507.3.1)',
                           f'{req_dia_in}"', f'{act_dia_in}"',
                           'ERROR', auto_fixable=False)
            else:
                report.add('Footing', loc,
                           f'Footing diameter (IRC R507.3.1)',
                           f'{req_dia_in}"', f'{act_dia_in}"', 'OK')

            if act_depth_in < min_depth:
                report.add('Footing', loc,
                           f'Depth below frost line (IRC R507.3.2, KY={frost_in}")',
                           f'{min_depth}"', f'{act_depth_in}"',
                           'ERROR')
            else:
                report.add('Footing', loc,
                           'Footing depth (frost line)',
                           f'{min_depth}"', f'{act_depth_in}"', 'OK')

    def _check_posts(self, report: CodeReport,
                     joistfills: list[dict],
                     posts: list[dict],
                     settings: EstimatorSettings):
        """Check post sizes against IRC R507.4 height limits."""
        all_posts = posts if posts else self._implied_posts(joistfills, settings)

        for idx, post in enumerate(all_posts):
            loc  = f'post {idx + 1}'
            ht   = post.get('post_height_ft', settings.post_height_ft)
            size = post.get('post_size', '4x4')
            max_ht = POST_MAX_HEIGHTS.get(size, 8.0)

            if ht > max_ht:
                report.add('Post', loc,
                           f'{size} post max height (IRC R507.4)',
                           f'{max_ht:.0f} ft', f'{ht:.1f} ft',
                           'ERROR')
            else:
                report.add('Post', loc,
                           f'{size} post height check',
                           f'≤ {max_ht:.0f} ft', f'{ht:.1f} ft', 'OK')

    def _check_beams(self, report: CodeReport,
                     joistfills: list[dict],
                     settings: EstimatorSettings):
        """Check mid-span beam requirements where joist span exceeds single-piece max."""
        for idx, jf in enumerate(joistfills):
            loc = f'bay {idx + 1}'
            span_in, bay_in, spacing = MaterialEstimator._joist_span_bay(jf)
            span_ft    = span_in / 12.0
            joist_size = jf.get('joist_size', settings.joist_size)

            # Max span from table for this size and spacing
            from code_tables import DECK_JOIST_SPANS
            from code_tables import _nearest_spacing as _ns
            sz_table = DECK_JOIST_SPANS.get(joist_size, {})
            if sz_table:
                key      = _ns(sz_table, spacing)
                max_span = sz_table[key]
            else:
                max_span = 16.0   # fallback

            if span_ft > max_span:
                # Need an intermediate beam; compute minimum spec
                half_span_ft  = span_ft / 2.0
                beam_span_ft  = bay_in / 12.0
                required_beam = min_deck_beam(half_span_ft, beam_span_ft)
                provided_beam = jf.get('beam_size', settings.beam_size)
                report.add('Beam', loc,
                           f'Intermediate beam needed: joist span {span_ft:.1f} ft > table max {max_span:.1f} ft',
                           required_beam, provided_beam,
                           'ERROR', auto_fixable=True)
            else:
                report.add('Beam', loc,
                           'Intermediate beam check',
                           'not required', '—', 'OK')

    def _check_rafters(self, report: CodeReport,
                       rooms: list[dict],
                       walls: list[dict],
                       settings: EstimatorSettings,
                       ky: dict):
        """Check rafter spans and overhang for each room."""
        if not settings.include_roof:
            return   # skip if roof framing not selected

        snow_psf       = ky.get('ground_snow_psf', 20)
        overhang_in    = settings.rafter_overhang_ft * 12
        rafter_spacing = settings.rafter_spacing

        for idx, room in enumerate(rooms):
            loc    = f'room {idx + 1}'
            width  = room.get('w', 0)
            if width <= 0:
                continue

            half_span_ft = (width / 12.0) / 2.0
            size_req     = min_rafter(half_span_ft, rafter_spacing)
            size_prov    = settings.joist_size   # reuse as rafter size for now

            def _nom(s): return int(s.split('x')[1]) if 'x' in s else 0

            if size_req == '2x12+' or _nom(size_req) > _nom(size_prov):
                sev = 'ERROR'
            else:
                sev = 'OK'

            report.add('Rafter', loc,
                       f'Rafter size for {half_span_ft:.1f} ft run @ {rafter_spacing}" o.c.',
                       size_req, size_prov, sev)

            # Overhang > 24" → engineer advisory
            if overhang_in > 24:
                report.add('Rafter', loc,
                           'Eave overhang > 24" (IRC R802.7.1.1)',
                           '≤ 24" or engineered',
                           f'{overhang_in:.0f}"',
                           'WARN')
            else:
                report.add('Rafter', loc,
                           'Eave overhang check',
                           '≤ 24"', f'{overhang_in:.0f}"', 'OK')

    def _check_headers(self, report: CodeReport,
                       walls: list[dict],
                       doors: list[dict],
                       windows: list[dict],
                       settings: EstimatorSettings):
        """Check door and window header sizes against IRC R602.7."""
        for idx, door in enumerate(doors):
            loc     = f'door {idx + 1}'
            width   = door.get('door_width', door.get('w', 36))
            req     = _header_size_code(width)
            prov    = door.get('header_size', '')

            if not prov:
                report.add('Header', loc,
                           f'Header size for {width:.0f}" opening (IRC R602.7)',
                           req, 'not specified',
                           'WARN', auto_fixable=False)
            else:
                def _nom(s): return int(s.split('x')[1]) if 'x' in s else 0
                sev = 'OK' if _nom(prov) >= _nom(req) else 'ERROR'
                report.add('Header', loc,
                           f'Header size for {width:.0f}" opening',
                           req, prov, sev)

        for idx, win in enumerate(windows):
            loc   = f'window {idx + 1}'
            width = win.get('window_width', win.get('w', 36))
            req   = _header_size_code(width)
            prov  = win.get('header_size', '')
            if not prov:
                report.add('Header', loc,
                           f'Header size for {width:.0f}" window (IRC R602.7)',
                           req, 'not specified',
                           'WARN')

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _implied_posts(joistfills: list[dict],
                       settings: EstimatorSettings) -> list[dict]:
        """Generate implied post list from joist fill grids when no explicit posts drawn."""
        posts = []
        sx = settings.post_spacing_x_ft * 12
        sy = settings.post_spacing_y_ft * 12

        for jf in joistfills:
            x0 = jf.get('x', 0)
            y0 = jf.get('y', 0)
            w  = jf.get('w', 0)
            h  = jf.get('h', 0)
            cols = max(2, math.ceil(w / sx) + 1)
            rows = max(2, math.ceil(h / sy) + 1)

            for c in range(cols):
                for r in range(rows):
                    posts.append({
                        'x': x0 + c * sx,
                        'y': y0 + r * sy,
                        'post_height_ft': settings.post_height_ft,
                        'post_size': '4x4',
                        'footing_dia_in': settings.footing_dia_in,
                        'footing_depth_in': settings.footing_depth_in,
                        'trib_area_ft2': (settings.post_spacing_x_ft *
                                          settings.post_spacing_y_ft),
                    })
        return posts
